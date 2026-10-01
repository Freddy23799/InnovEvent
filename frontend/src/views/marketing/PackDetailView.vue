<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";

const props = defineProps({ packId: { type: [String, Number], required: true } });

const lightbox = useLightboxStore();
const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

// Reprend une sélection laissée avant un passage par l'inscription (voir
// requestQuote ci-dessous) — sans ça, le client perdrait ses choix en
// revenant sur cette page après avoir créé son compte.
const SELECTION_STORAGE_KEY = "ie_pending_pack_selection";

const loading = ref(true);
const notFound = ref(false);
const pack = ref(null);
const items = ref([]);
const quantities = reactive({});
const selected = reactive({});

const TYPE_ICONS = { venue: "fa-solid fa-building-columns", provider: "fa-solid fa-handshake", equipment: "fa-solid fa-sliders" };
const TYPE_LABELS = { venue: "Salle", provider: "Prestataire", equipment: "Matériel" };

function packFeatures(caption) {
  if (!caption) return [];
  return caption
    .split(",")
    .map((f) => f.trim().replace(/\.$/, ""))
    .filter(Boolean)
    .map((f) => f.charAt(0).toUpperCase() + f.slice(1));
}

const includedItems = computed(() => items.value.filter((i) => !i.is_optional));
const optionalItems = computed(() => items.value.filter((i) => i.is_optional));

async function loadPack() {
  loading.value = true;
  notFound.value = false;
  try {
    const [packRes, itemsRes] = await Promise.all([
      api.get(`/public/landing-media/${props.packId}/`),
      api.get("/public/pack-items/", { params: { pack: props.packId } }),
    ]);
    pack.value = packRes.data;
    items.value = itemsRes.data;
    items.value.forEach((item) => {
      quantities[item.id] = item.resource_type === "equipment" ? item.default_quantity || 1 : 1;
      // Inclus par défaut dans le devis ; les options restent décochées jusqu'à ce
      // que le client les ajoute lui-même.
      selected[item.id] = !item.is_optional;
    });
    restorePendingSelection();
  } catch (e) {
    notFound.value = true;
  } finally {
    loading.value = false;
  }
}

// Un client non connecté qui clique « Demander un devis » est envoyé créer
// son compte ; sans cette sauvegarde, ses cases cochées/quantités seraient
// perdues au retour sur cette page.
function restorePendingSelection() {
  let raw = null;
  try {
    raw = sessionStorage.getItem(SELECTION_STORAGE_KEY);
  } catch (e) {
    return;
  }
  if (!raw) return;
  sessionStorage.removeItem(SELECTION_STORAGE_KEY);
  try {
    const saved = JSON.parse(raw);
    if (String(saved.packId) !== String(props.packId)) return;
    Object.assign(selected, saved.selected);
    Object.assign(quantities, saved.quantities);
    if (auth.isAuthenticated) {
      showQuoteForm.value = true;
    }
  } catch (e) {
    // sélection illisible : on ignore simplement, pas bloquant
  }
}

// Devis estimatif : somme des éléments cochés (prix unitaire × quantité). Les
// prestataires sans prix unique (fourchette texte) sont signalés « sur devis »
// plutôt que d'être inclus dans un total qui serait faux.
const quoteLines = computed(() =>
  items.value
    .filter((item) => selected[item.id])
    .map((item) => ({
      id: item.id,
      name: item.resource_name,
      quantity: item.resource_type === "equipment" ? quantities[item.id] || 1 : 1,
      unitPrice: item.resource_price,
      subtotal: item.resource_price != null ? item.resource_price * (item.resource_type === "equipment" ? quantities[item.id] || 1 : 1) : null,
    }))
);
const quoteTotal = computed(() => quoteLines.value.reduce((sum, line) => sum + (line.subtotal || 0), 0));
const hasUnpricedSelection = computed(() => quoteLines.value.some((l) => l.subtotal == null));
const selectedCount = computed(() => quoteLines.value.length);

// Aperçu PDF non contractuel, accessible sans compte — le devis structuré,
// définitif et téléchargeable reste réservé aux comptes connectés (voir
// « Demander un devis pour ce pack » ci-dessus).
const previewLoading = ref(false);
const previewError = ref("");

async function previewQuotePdf() {
  previewError.value = "";
  previewLoading.value = true;
  try {
    const selections = quoteLines.value.map((l) => ({ pack_item_id: l.id, quantity: l.quantity }));
    const { data } = await api.post(
      `/public/landing-media/${props.packId}/quote-preview/`,
      { selections },
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
    window.open(url, "_blank", "noopener");
  } catch (e) {
    previewError.value = "Impossible de générer l'aperçu pour le moment.";
  } finally {
    previewLoading.value = false;
  }
}

// Demande de devis groupée pour tout le pack : un seul formulaire (date +
// libellé de l'événement), une seule soumission qui crée l'événement et une
// réservation par élément sélectionné — au lieu de laisser le client réserver
// chaque élément séparément après coup.
const showQuoteForm = ref(false);
const quoteForm = reactive({ event_title: "", event_date: "", notes: "" });
const quoteSubmitting = ref(false);
const quoteError = ref("");
const quoteSuccess = ref(null);

const heroError = ref("");

function requestQuote() {
  heroError.value = "";
  if (!quoteLines.value.length) {
    heroError.value = "Sélectionnez au moins un élément ci-dessous avant de demander un devis.";
    return;
  }
  if (!auth.isAuthenticated) {
    try {
      sessionStorage.setItem(SELECTION_STORAGE_KEY, JSON.stringify({ packId: props.packId, selected, quantities }));
    } catch (e) {
      // stockage indisponible (navigation privée...) : le client refera sa sélection au retour
    }
    router.push({ name: "register", query: { role: "client", next: route.fullPath } });
    return;
  }
  quoteError.value = "";
  quoteSuccess.value = null;
  showQuoteForm.value = true;
}

async function submitQuoteRequest() {
  quoteError.value = "";
  if (!quoteForm.event_date) {
    quoteError.value = "La date de votre événement est requise.";
    return;
  }
  quoteSubmitting.value = true;
  try {
    const selections = quoteLines.value.map((l) => ({ pack_item_id: l.id, quantity: l.quantity }));
    const { data } = await api.post(`/public/landing-media/${props.packId}/quote-request/`, {
      event_title: quoteForm.event_title,
      event_date: quoteForm.event_date,
      notes: quoteForm.notes,
      selections,
    });
    quoteSuccess.value = data;
    showQuoteForm.value = false;
  } catch (e) {
    quoteError.value = e?.response?.data?.detail || "Impossible d'envoyer votre demande pour le moment.";
  } finally {
    quoteSubmitting.value = false;
  }
}

function bookingLink(item) {
  return {
    name: "bookings",
    query: {
      resource_type: item.resource_type,
      resource_id: item[item.resource_type],
      quantity: item.resource_type === "equipment" ? quantities[item.id] : 1,
    },
  };
}

onMounted(loadPack);
</script>

<template>
  <div class="ie-pack-detail">
    <div v-if="loading" class="ie-skeleton" style="height: 420px; border-radius: 16px;"></div>

    <EmptyState v-else-if="notFound" icon="fa-solid fa-box-open" text="Ce pack n'est plus disponible." />

    <template v-else>
      <nav class="ie-pack-breadcrumb" aria-label="Fil d'Ariane">
        <router-link :to="{ name: 'landing', hash: '#packs' }">Nos packs</router-link>
        <i class="fa-solid fa-chevron-right"></i>
        <span>{{ pack.label }}</span>
      </nav>

      <div class="ie-pack-hero">
        <div class="ie-pack-hero-photo" :class="{ 'is-empty': !pack.photo }">
          <img v-if="pack.photo" :src="pack.photo" :alt="pack.label" class="ie-zoomable" @click="lightbox.open(pack.photo, pack.label)" />
          <i v-else class="fa-solid fa-box-open"></i>
        </div>
        <div class="ie-pack-hero-body">
          <span class="ie-pack-eyebrow"><i class="fa-solid fa-gift"></i> Pack InnovEvent</span>
          <h1>{{ pack.label }}</h1>
          <p v-if="pack.caption">{{ pack.caption }}</p>
          <ul v-if="packFeatures(pack.caption).length" class="ie-pack-hero-features">
            <li v-for="(feature, i) in packFeatures(pack.caption)" :key="i"><i class="fa-solid fa-check"></i>{{ feature }}</li>
          </ul>
          <div class="ie-pack-hero-foot">
            <strong v-if="pack.budget_label" class="ie-pack-price">{{ pack.budget_label }}</strong>
            <span v-if="items.length" class="ie-badge ie-badge-neutral">{{ items.length }} élément{{ items.length > 1 ? 's' : '' }} inclus dans le pack</span>
          </div>
          <button type="button" class="ie-btn ie-btn-primary ie-pack-hero-cta" @click="requestQuote">
            <i class="fa-solid fa-file-invoice"></i> Demander un devis pour ce pack
          </button>
          <p v-if="heroError" class="ie-field-hint" style="color: var(--ie-red); margin-top: 8px;">{{ heroError }}</p>
        </div>
      </div>

      <div v-if="quoteSuccess" class="ie-quote-success">
        <i class="fa-solid fa-circle-check"></i>
        <div>
          <strong>Votre demande a bien été envoyée.</strong>
          <p>{{ quoteSuccess.bookings.length }} élément{{ quoteSuccess.bookings.length > 1 ? 's' : '' }} du pack en attente de confirmation. Vous serez notifié dès la réponse.</p>
          <router-link :to="{ name: 'bookings' }" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 8px;">
            <i class="fa-solid fa-list-check"></i> Voir mes réservations
          </router-link>
        </div>
      </div>

      <div v-if="showQuoteForm" class="ie-quote-form-panel">
        <h2><i class="fa-solid fa-calendar-check"></i> Finaliser ma demande de devis</h2>
        <p class="ie-field-hint">{{ selectedCount }} élément{{ selectedCount > 1 ? 's' : '' }} sélectionné{{ selectedCount > 1 ? 's' : '' }} — une réservation « en attente » sera créée pour chacun.</p>
        <form @submit.prevent="submitQuoteRequest">
          <label class="ie-label">Nom de l'événement (optionnel)</label>
          <input v-model="quoteForm.event_title" class="ie-input" :placeholder="`Ex : ${pack.label}`" />
          <label class="ie-label" style="margin-top: 12px;">Date de l'événement</label>
          <input v-model="quoteForm.event_date" type="date" class="ie-input" required />
          <label class="ie-label" style="margin-top: 12px;">Message (optionnel)</label>
          <textarea v-model="quoteForm.notes" class="ie-input" rows="2" placeholder="Précisions utiles pour les prestataires…"></textarea>
          <p v-if="quoteError" class="ie-alert ie-alert-danger" style="margin-top: 10px;">{{ quoteError }}</p>
          <div style="display: flex; gap: 10px; margin-top: 14px;">
            <button type="submit" class="ie-btn ie-btn-primary" :disabled="quoteSubmitting">
              {{ quoteSubmitting ? "Envoi…" : "Envoyer ma demande" }}
            </button>
            <button type="button" class="ie-btn ie-btn-ghost" @click="showQuoteForm = false">Annuler</button>
          </div>
        </form>
      </div>

      <section class="ie-pack-section">
        <h2>Ce que comprend ce pack</h2>
        <p class="ie-pack-section-hint">Cochez les éléments qui vous intéressent — vous pourrez aussi les réserver séparément si besoin.</p>

        <div v-if="includedItems.length" class="ie-pack-items-grid">
          <div v-for="item in includedItems" :key="item.id" class="ie-pack-item-card" :class="{ 'is-unavailable': !item.resource_is_active }">
            <div class="ie-pack-item-photo">
              <img v-if="item.resource_photo" :src="item.resource_photo" :alt="item.resource_name" />
              <i v-else :class="TYPE_ICONS[item.resource_type]"></i>
              <span class="ie-pack-item-type"><i :class="TYPE_ICONS[item.resource_type]"></i> {{ TYPE_LABELS[item.resource_type] }}</span>
            </div>
            <div class="ie-pack-item-body">
              <label class="ie-pack-item-select">
                <input v-model="selected[item.id]" type="checkbox" />
                Inclure dans mon devis
              </label>
              <h3>{{ item.resource_name }}</h3>
              <p v-if="item.resource_price_label">{{ item.resource_price_label }}</p>
              <div v-if="item.resource_type === 'equipment'" class="ie-pack-qty">
                <label>Quantité</label>
                <input v-model.number="quantities[item.id]" type="number" min="1" class="ie-input" />
              </div>
              <router-link v-if="item.resource_is_active" :to="bookingLink(item)" class="ie-btn ie-btn-primary ie-btn-sm" style="width: 100%; margin-top: 10px;">
                <i class="fa-solid fa-calendar-plus"></i> Réserver cet élément
              </router-link>
              <span v-else class="ie-pack-item-unavailable">Actuellement indisponible</span>
            </div>
          </div>
        </div>
        <EmptyState v-else icon="fa-solid fa-box-open" text="Le détail de ce pack n'a pas encore été renseigné." />
      </section>

      <section v-if="optionalItems.length" class="ie-pack-section">
        <h2>Options complémentaires</h2>
        <p class="ie-pack-section-hint">Ajoutez ces éléments à la carte pour compléter votre événement.</p>
        <div class="ie-pack-items-grid">
          <div v-for="item in optionalItems" :key="item.id" class="ie-pack-item-card" :class="{ 'is-unavailable': !item.resource_is_active }">
            <div class="ie-pack-item-photo">
              <img v-if="item.resource_photo" :src="item.resource_photo" :alt="item.resource_name" />
              <i v-else :class="TYPE_ICONS[item.resource_type]"></i>
              <span class="ie-pack-item-type"><i :class="TYPE_ICONS[item.resource_type]"></i> {{ TYPE_LABELS[item.resource_type] }}</span>
            </div>
            <div class="ie-pack-item-body">
              <label class="ie-pack-item-select">
                <input v-model="selected[item.id]" type="checkbox" />
                Inclure dans mon devis
              </label>
              <h3>{{ item.resource_name }}</h3>
              <p v-if="item.resource_price_label">{{ item.resource_price_label }}</p>
              <div v-if="item.resource_type === 'equipment'" class="ie-pack-qty">
                <label>Quantité</label>
                <input v-model.number="quantities[item.id]" type="number" min="1" class="ie-input" />
              </div>
              <router-link v-if="item.resource_is_active" :to="bookingLink(item)" class="ie-btn ie-btn-secondary ie-btn-sm" style="width: 100%; margin-top: 10px;">
                <i class="fa-solid fa-plus"></i> Ajouter en option
              </router-link>
              <span v-else class="ie-pack-item-unavailable">Actuellement indisponible</span>
            </div>
          </div>
        </div>
      </section>

      <section v-if="items.length" class="ie-quote-panel">
        <div class="ie-quote-header">
          <h2><i class="fa-solid fa-file-invoice-dollar"></i> Mon devis estimatif</h2>
          <span class="ie-quote-count">{{ selectedCount }} élément{{ selectedCount > 1 ? 's' : '' }} sélectionné{{ selectedCount > 1 ? 's' : '' }}</span>
        </div>
        <div v-if="quoteLines.length" class="ie-quote-lines">
          <div v-for="line in quoteLines" :key="line.id" class="ie-quote-line">
            <span class="ie-quote-line-name">{{ line.name }}<template v-if="line.quantity > 1"> × {{ line.quantity }}</template></span>
            <span class="ie-quote-line-amount">{{ line.subtotal != null ? `${line.subtotal.toLocaleString('fr-FR')} XAF` : 'Sur devis' }}</span>
          </div>
        </div>
        <p v-else class="ie-quote-empty">Cochez « Inclure dans mon devis » sur les éléments qui vous intéressent pour voir une estimation.</p>
        <div v-if="quoteLines.length" class="ie-quote-total">
          <span>Total estimatif</span>
          <strong>{{ quoteTotal.toLocaleString('fr-FR') }} XAF</strong>
        </div>
        <p v-if="hasUnpricedSelection" class="ie-quote-hint">
          <i class="fa-solid fa-circle-info"></i> Certains prestataires n'ont pas de tarif fixe (fourchette de prix) : contactez-les directement lors de la réservation pour un devis précis.
        </p>
        <div v-if="quoteLines.length" style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px;">
          <button type="button" class="ie-btn ie-btn-primary ie-btn-sm" @click="requestQuote">
            <i class="fa-solid fa-paper-plane"></i> Demander ce devis
          </button>
          <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" :disabled="previewLoading" @click="previewQuotePdf">
            <i class="fa-solid fa-file-pdf"></i> {{ previewLoading ? "Génération…" : "Aperçu PDF (non contractuel)" }}
          </button>
        </div>
        <p v-if="previewError" class="ie-quote-hint" style="color: var(--ie-red);">{{ previewError }}</p>
        <p class="ie-field-hint" style="margin-top: 6px;">Aperçu PDF consultable sans connexion. « Demander ce devis » exige un compte — vos éléments sélectionnés sont conservés.</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.ie-pack-detail { max-width: 960px; margin: 0 auto; }

.ie-pack-breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--ie-muted); margin-bottom: 18px; }
.ie-pack-breadcrumb a { color: var(--ie-navy); font-weight: 600; }
.ie-pack-breadcrumb a:hover { text-decoration: underline; }
.ie-pack-breadcrumb i { font-size: 9px; }
.ie-pack-breadcrumb span { color: var(--ie-ink); font-weight: 600; }

.ie-pack-hero { display: grid; grid-template-columns: 260px 1fr; gap: 26px; margin-bottom: 36px; }
.ie-pack-hero-photo { aspect-ratio: 4/3; border-radius: 14px; overflow: hidden; background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center; }
.ie-pack-hero-photo img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.ie-pack-hero-photo.is-empty i { font-size: 40px; color: var(--ie-navy); opacity: 0.3; }
.ie-pack-eyebrow { font-size: 11px; font-weight: 800; letter-spacing: 0.06em; color: var(--ie-red); text-transform: uppercase; display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.ie-pack-hero-body h1 { font-size: 24px; color: var(--ie-navy); margin: 0 0 10px; }
.ie-pack-hero-body p { font-size: 13.5px; color: var(--ie-ink); line-height: 1.6; margin: 0 0 14px; }
.ie-pack-hero-features { list-style: none; margin: 0 0 16px; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.ie-pack-hero-features li { font-size: 12.5px; color: var(--ie-ink); display: flex; align-items: center; gap: 8px; }
.ie-pack-hero-features i { color: var(--ie-red); font-size: 11px; }
.ie-pack-hero-foot { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.ie-pack-price { font-size: 22px; color: var(--ie-red); }
.ie-pack-hero-cta { display: inline-flex; }

.ie-pack-section { margin-bottom: 36px; }
.ie-pack-section h2 { font-size: 17px; color: var(--ie-navy); margin: 0 0 4px; }
.ie-pack-section-hint { font-size: 12.5px; color: var(--ie-muted); margin: 0 0 16px; }

.ie-pack-items-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 16px; }
.ie-pack-item-card { background: #fff; border: 1px solid var(--ie-line); border-radius: 12px; overflow: hidden; }
.ie-pack-item-card.is-unavailable { opacity: 0.6; }
.ie-pack-item-photo { height: 130px; background: var(--ie-navy-soft); position: relative; display: flex; align-items: center; justify-content: center; }
.ie-pack-item-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-pack-item-photo i { font-size: 30px; color: var(--ie-navy); opacity: 0.35; }
.ie-pack-item-type {
  position: absolute; top: 8px; left: 8px; background: rgba(23, 27, 38, 0.75); color: #fff;
  font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 999px; display: flex; align-items: center; gap: 4px;
}
.ie-pack-item-body { padding: 14px; }
.ie-pack-item-body h3 { font-size: 13.5px; color: var(--ie-navy); margin: 0 0 4px; }
.ie-pack-item-body p { font-size: 12px; color: var(--ie-muted); margin: 0; }
.ie-pack-qty { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 10px; }
.ie-pack-qty label { font-size: 11.5px; color: var(--ie-muted); font-weight: 600; }
.ie-pack-qty input { width: 70px; padding: 6px 8px; }
.ie-pack-item-unavailable { display: block; margin-top: 10px; font-size: 11.5px; color: var(--ie-muted); text-align: center; }
.ie-pack-item-select { display: flex; align-items: center; gap: 7px; font-size: 11.5px; color: var(--ie-muted); font-weight: 600; margin-bottom: 8px; cursor: pointer; }

.ie-quote-panel {
  background: #fff; border: 1px solid var(--ie-line); border-radius: 14px;
  padding: 20px 24px; box-shadow: 0 4px 16px rgba(30, 42, 51, 0.08); margin-top: 28px;
}
.ie-quote-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.ie-quote-header h2 { font-size: 16px; color: var(--ie-navy); margin: 0; display: flex; align-items: center; gap: 8px; }
.ie-quote-header h2 i { color: var(--ie-red); }
.ie-quote-count { font-size: 12px; color: var(--ie-muted); }
.ie-quote-lines { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; max-height: 180px; overflow-y: auto; }
.ie-quote-line { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; color: var(--ie-ink); padding-bottom: 8px; border-bottom: 1px dashed var(--ie-line); }
.ie-quote-line-name { flex: 1; }
.ie-quote-line-amount { font-weight: 600; color: var(--ie-navy); white-space: nowrap; }
.ie-quote-empty { font-size: 12.5px; color: var(--ie-muted); margin: 0 0 8px; }
.ie-quote-total { display: flex; justify-content: space-between; align-items: center; padding-top: 12px; border-top: 2px solid var(--ie-navy); }
.ie-quote-total span { font-size: 13.5px; color: var(--ie-ink); font-weight: 600; }
.ie-quote-total strong { font-size: 20px; color: var(--ie-red); }
.ie-quote-hint { font-size: 11.5px; color: var(--ie-muted); margin: 10px 0 0; display: flex; align-items: flex-start; gap: 6px; }

.ie-quote-success {
  display: flex; align-items: flex-start; gap: 14px; background: var(--ie-success-soft, #e3f3ea);
  border: 1px solid var(--ie-success, #1e7b4d); border-radius: 12px; padding: 18px 20px; margin-bottom: 28px;
}
.ie-quote-success i { font-size: 22px; color: var(--ie-success, #1e7b4d); margin-top: 2px; }
.ie-quote-success strong { display: block; color: var(--ie-navy); font-size: 14px; margin-bottom: 4px; }
.ie-quote-success p { margin: 0; font-size: 12.5px; color: var(--ie-ink); }

.ie-quote-form-panel {
  background: #fff; border: 1px solid var(--ie-line); border-radius: 14px; padding: 22px 24px; margin-bottom: 28px;
  box-shadow: 0 4px 16px rgba(30, 42, 51, 0.08);
}
.ie-quote-form-panel h2 { font-size: 16px; color: var(--ie-navy); margin: 0 0 4px; display: flex; align-items: center; gap: 8px; }
.ie-quote-form-panel h2 i { color: var(--ie-red); }

@media (max-width: 640px) {
  .ie-pack-hero { grid-template-columns: 1fr; }
}
</style>
