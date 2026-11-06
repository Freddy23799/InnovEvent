<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import { ACTOR_CATEGORY_GROUPS, OTHER_CATEGORY_GROUP } from "../../data/actorCategories";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const lightbox = useLightboxStore();
const MARKETPLACE_LABELS = { actors: "Marketplace des acteurs", interior_design: "Décoration & design intérieur" };
const CATEGORY_GROUPS = [...ACTOR_CATEGORY_GROUPS, OTHER_CATEGORY_GROUP];

const VERIFICATION_STATUSES = [
  { value: "not_verified", label: "Non vérifié" },
  { value: "profile_verified", label: "Profil vérifié" },
  { value: "identity_verified", label: "Identité vérifiée" },
  { value: "company_verified", label: "Entreprise vérifiée" },
  { value: "portfolio_verified", label: "Portfolio vérifié" },
  { value: "professional_partner", label: "Partenaire professionnel" },
];

const profiles = ref([]);
const loading = ref(true);
const saving = reactive({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/profiles/");
    profiles.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function toggleBadge(profile, field) {
  saving[profile.id] = true;
  try {
    const { data } = await api.patch(`/marketplace/profiles/${profile.id}/badges/`, { [field]: !profile[field] });
    Object.assign(profile, data);
  } finally {
    saving[profile.id] = false;
  }
}

async function updateVerificationStatus(profile, status) {
  saving[profile.id] = true;
  try {
    const { data } = await api.patch(`/marketplace/profiles/${profile.id}/badges/`, { verification_status: status });
    Object.assign(profile, data, { verification_requested_at: null });
    toast.success("Statut de vérification mis à jour.");
  } finally {
    saving[profile.id] = false;
  }
}

// --- Demandes de vérification (CNI envoyée par le prestataire) -------------
const pendingVerifications = computed(() =>
  profiles.value
    .filter((p) => p.verification_requested_at)
    .sort((a, b) => new Date(a.verification_requested_at) - new Date(b.verification_requested_at))
);

const review = ref(null);
const reviewLoading = ref(false);

async function openReview(profile) {
  review.value = { summary: profile, detail: null };
  reviewLoading.value = true;
  try {
    const { data } = await api.get(`/marketplace/profiles/${profile.id}/`);
    review.value = { summary: profile, detail: data };
  } catch (e) {
    toast.error("Impossible de charger ce profil.");
    review.value = null;
  } finally {
    reviewLoading.value = false;
  }
}

async function decide(status) {
  const profile = review.value.summary;
  await updateVerificationStatus(profile, status);
  review.value = null;
}

function zoom(url, caption) {
  lightbox.open(url, caption);
}

function openPortfolio(index) {
  lightbox.openGallery(review.value.detail.portfolio_items.map((p) => ({ url: p.image, caption: p.caption })), index);
}

function reviewChecks(d) {
  return [
    { label: "Photo de profil", done: Boolean(d.logo) },
    { label: "Photo de couverture", done: Boolean(d.cover_photo) },
    { label: "Description", done: Boolean(d.description?.trim()) },
    { label: "Ville", done: Boolean(d.city) },
    { label: "Téléphone", done: Boolean(d.contact_phone) },
    { label: "CNI", done: Boolean(d.id_card_photo) },
    { label: `${d.services.length} service(s)`, done: d.services.length > 0 },
    { label: `${d.portfolio_items.length} réalisation(s)`, done: d.portfolio_items.length > 0 },
  ];
}

function sinceLabel(value) {
  const days = Math.floor((Date.now() - new Date(value)) / 86400000);
  return days <= 0 ? "aujourd'hui" : days === 1 ? "hier" : `il y a ${days} jours`;
}

// --- Ajout direct d'une prestation par l'administration ---------------------
const showForm = ref(false);
const ownerMode = ref("new"); // "new" | "existing"
const partnerUsers = ref([]);
const emptyForm = {
  marketplace_type: "actors", category: "", business_name: "", city: "", description: "",
  owner_user: "", new_owner_username: "", new_owner_email: "", new_owner_first_name: "", new_owner_last_name: "",
};
const form = reactive({ ...emptyForm });
const submitting = ref(false);
const errorMessage = ref("");
const lastCreated = ref(null);

async function loadPartnerUsers() {
  try {
    const { data } = await api.get("/auth/users/", { params: { role: "partner" } });
    partnerUsers.value = data.results || data;
  } catch {
    partnerUsers.value = [];
  }
}

function toggleForm() {
  showForm.value = !showForm.value;
  if (showForm.value) {
    Object.assign(form, emptyForm);
    errorMessage.value = "";
    lastCreated.value = null;
    loadPartnerUsers();
  }
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = {
      marketplace_type: form.marketplace_type, category: form.category,
      business_name: form.business_name, city: form.city, description: form.description,
    };
    if (ownerMode.value === "existing") {
      payload.owner_user = form.owner_user;
    } else {
      payload.new_owner_username = form.new_owner_username;
      payload.new_owner_email = form.new_owner_email;
      payload.new_owner_first_name = form.new_owner_first_name;
      payload.new_owner_last_name = form.new_owner_last_name;
    }
    const { data } = await api.post("/marketplace/profiles/admin-create/", payload);
    lastCreated.value = data;
    profiles.value.unshift(data);
    Object.assign(form, emptyForm);
    toast.success("Prestataire enregistré.");
  } catch (e) {
    const detail = e?.response?.data?.detail;
    errorMessage.value = typeof detail === "object" ? Object.values(detail).flat().join(" ") : (detail || "Impossible de créer cette prestation.");
  } finally {
    submitting.value = false;
  }
}

const categoryLabel = computed(() => {
  for (const group of CATEGORY_GROUPS) {
    const found = group.items.find((i) => i.value === form.category);
    if (found) return found.label;
  }
  return "";
});

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-people-group" style="color: var(--ie-red); margin-right: 8px;"></i>Prestataires</h1>
        <p class="ie-page-subtitle">Ajoutez directement une prestation dans une catégorie, et accordez les badges de reconnaissance.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="toggleForm">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Ajouter un prestataire" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <div v-if="lastCreated" class="ie-alert ie-alert-success" style="margin-bottom: 14px;">
        <i class="fa-solid fa-circle-check"></i> « {{ lastCreated.business_name }} » créé et déjà abonné, visible immédiatement dans le Marketplace.
        <template v-if="lastCreated.generated_password">
          <br />Compte <strong>{{ lastCreated.owner_username }}</strong> — mot de passe généré : <code>{{ lastCreated.generated_password }}</code>
          <span class="ie-field-hint"> (à transmettre au prestataire — ne sera plus affiché ensuite)</span>
        </template>
      </div>

      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Marketplace</label>
            <select v-model="form.marketplace_type" class="ie-select">
              <option value="actors">Marketplace des acteurs</option>
              <option value="interior_design">Décoration & design intérieur</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select" required>
              <option value="" disabled>Choisir une catégorie…</option>
              <optgroup v-for="g in CATEGORY_GROUPS" :key="g.title" :label="g.title">
                <option v-for="c in g.items" :key="c.value" :value="c.value">{{ c.label }}</option>
              </optgroup>
            </select>
          </div>
        </div>
        <p v-if="categoryLabel" class="ie-field-hint" style="margin-top: 4px;">{{ categoryLabel }}</p>

        <label class="ie-label" style="margin-top: 14px;">Nom de l'entreprise / activité</label>
        <input v-model="form.business_name" class="ie-input" required placeholder="Ex : SnapBooth Cameroun" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Ville</label>
            <input v-model="form.city" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="2"></textarea>

        <label class="ie-label" style="margin-top: 18px;">Compte prestataire</label>
        <div class="ie-owner-mode-toggle">
          <button type="button" class="ie-btn ie-btn-sm" :class="ownerMode === 'new' ? 'ie-btn-primary' : 'ie-btn-ghost'" @click="ownerMode = 'new'">
            Créer un nouveau compte
          </button>
          <button type="button" class="ie-btn ie-btn-sm" :class="ownerMode === 'existing' ? 'ie-btn-primary' : 'ie-btn-ghost'" @click="ownerMode = 'existing'">
            Utiliser un compte existant
          </button>
        </div>

        <template v-if="ownerMode === 'new'">
          <div class="ie-form-row" style="margin-top: 10px;">
            <div>
              <label class="ie-label">Identifiant</label>
              <input v-model="form.new_owner_username" class="ie-input" required placeholder="Ex : presta_snapbooth" />
            </div>
            <div>
              <label class="ie-label">Email</label>
              <input v-model="form.new_owner_email" type="email" class="ie-input" />
            </div>
          </div>
          <div class="ie-form-row" style="margin-top: 10px;">
            <div>
              <label class="ie-label">Prénom</label>
              <input v-model="form.new_owner_first_name" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Nom</label>
              <input v-model="form.new_owner_last_name" class="ie-input" />
            </div>
          </div>
          <p class="ie-field-hint" style="margin-top: 6px;">Un mot de passe sera généré automatiquement et affiché une seule fois après création.</p>
        </template>
        <template v-else>
          <select v-model="form.owner_user" class="ie-select" style="margin-top: 10px;" required>
            <option value="" disabled>Choisir un compte prestataire…</option>
            <option v-for="u in partnerUsers" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
          </select>
          <p v-if="!partnerUsers.length" class="ie-field-hint" style="margin-top: 6px;">Aucun compte prestataire disponible — créez-en un nouveau plutôt.</p>
        </template>

        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 14px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Création…" : "Créer cette prestation" }}
        </button>
      </form>
    </div>

    <section v-if="pendingVerifications.length" class="ie-card ie-card-body ie-verif-queue">
      <h2><i class="fa-solid fa-id-card"></i> Demandes de vérification <span>{{ pendingVerifications.length }}</span></h2>
      <p class="ie-field-hint" style="margin: 0 0 12px;">Ces prestataires ont envoyé leur CNI. Examinez leur profil puis attribuez le statut de vérification.</p>
      <div class="ie-verif-list">
        <div v-for="p in pendingVerifications" :key="p.id" class="ie-verif-item">
          <span class="ie-verif-avatar">
            <img v-if="p.logo" v-img="p.logo" :alt="p.business_name" />
            <i v-else class="fa-solid fa-handshake"></i>
          </span>
          <div class="ie-verif-info">
            <strong>{{ p.business_name }}</strong>
            <span>{{ p.category_display }} · {{ p.city || "Ville non renseignée" }} · CNI reçue {{ sinceLabel(p.verification_requested_at) }}</span>
          </div>
          <button type="button" class="ie-btn ie-btn-primary ie-btn-sm" @click="openReview(p)"><i class="fa-solid fa-magnifying-glass"></i> Examiner</button>
        </div>
      </div>
    </section>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div v-else-if="profiles.length" class="ie-table-wrap">
        <table class="ie-table">
          <thead>
            <tr>
              <th>Prestataire</th><th>Marketplace</th><th>Note</th>
              <th>Statut de vérification</th><th>★ Recommandé</th><th>🏆 Top</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in profiles" :key="p.id">
              <td>
                <button type="button" class="ie-profile-link" @click="openReview(p)">{{ p.business_name }}</button>
                <p class="ie-field-hint" style="margin: 2px 0 0;">
                  {{ p.category_display }} · {{ p.city }}
                  <span v-if="p.verification_requested_at" class="ie-badge ie-badge-warning ie-cni-badge">CNI à examiner</span>
                  <span v-else-if="p.has_id_card" class="ie-cni-ok"><i class="fa-solid fa-id-card"></i> CNI</span>
                </p>
              </td>
              <td>{{ MARKETPLACE_LABELS[p.marketplace_type] || p.marketplace_type }}</td>
              <td>{{ p.average_rating ? `${p.average_rating} ★ (${p.review_count})` : "—" }}</td>
              <td>
                <select
                  class="ie-select" style="font-size: 12.5px; padding: 4px 8px;" :value="p.verification_status" :disabled="saving[p.id]"
                  @change="updateVerificationStatus(p, $event.target.value)"
                >
                  <option v-for="s in VERIFICATION_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
              </td>
              <td>
                <label class="ie-badge-toggle">
                  <input type="checkbox" :checked="p.is_recommended" :disabled="saving[p.id]" @change="toggleBadge(p, 'is_recommended')" />
                </label>
              </td>
              <td>
                <label class="ie-badge-toggle">
                  <input type="checkbox" :checked="p.is_top" :disabled="saving[p.id]" @change="toggleBadge(p, 'is_top')" />
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-award" text="Aucun profil professionnel pour le moment." />
    </div>
    <Teleport to="body">
      <div v-if="review" class="ie-review-overlay" @click.self="review = null">
        <div class="ie-review" role="dialog" aria-modal="true" aria-label="Examen du profil">
          <header class="ie-review-head">
            <div>
              <span class="ie-field-hint">Examen du profil</span>
              <h2>{{ review.summary.business_name }}</h2>
            </div>
            <button type="button" class="ie-review-close" aria-label="Fermer" @click="review = null"><i class="fa-solid fa-xmark"></i></button>
          </header>

          <div v-if="reviewLoading || !review.detail" class="ie-review-body"><div class="ie-skeleton" style="height: 320px;"></div></div>
          <div v-else class="ie-review-body">
            <div class="ie-review-cover" :class="{ empty: !review.detail.cover_photo }">
              <img v-if="review.detail.cover_photo" v-img="review.detail.cover_photo" alt="" @click="zoom(review.detail.cover_photo, 'Couverture')" />
              <span class="ie-review-logo">
                <img v-if="review.detail.logo" v-img="review.detail.logo" alt="" />
                <i v-else class="fa-solid fa-handshake"></i>
              </span>
            </div>

            <div class="ie-review-checks">
              <span v-for="c in reviewChecks(review.detail)" :key="c.label" :class="{ done: c.done }">
                <i class="fa-solid" :class="c.done ? 'fa-circle-check' : 'fa-circle-xmark'"></i> {{ c.label }}
              </span>
            </div>

            <div class="ie-review-grid">
              <section>
                <h3>Pièce d'identité (CNI)</h3>
                <button v-if="review.detail.id_card_photo" type="button" class="ie-review-cni" @click="zoom(review.detail.id_card_photo, 'CNI')">
                  <img :src="review.detail.id_card_photo" alt="CNI du prestataire" />
                  <span><i class="fa-solid fa-magnifying-glass-plus"></i> Agrandir</span>
                </button>
                <p v-else class="ie-field-hint">Aucune CNI envoyée.</p>
              </section>
              <section>
                <h3>Informations</h3>
                <dl class="ie-review-dl">
                  <div><dt>Activité</dt><dd>{{ review.detail.category_display }}</dd></div>
                  <div><dt>Marketplace</dt><dd>{{ MARKETPLACE_LABELS[review.detail.marketplace_type] || review.detail.marketplace_type }}</dd></div>
                  <div><dt>Ville</dt><dd>{{ [review.detail.neighborhood, review.detail.city].filter(Boolean).join(", ") || "—" }}</dd></div>
                  <div><dt>Téléphone</dt><dd>{{ review.detail.contact_phone || "—" }}</dd></div>
                  <div><dt>Email</dt><dd>{{ review.detail.contact_email || "—" }}</dd></div>
                  <div><dt>Zone</dt><dd>{{ review.detail.service_area || "—" }}</dd></div>
                  <div><dt>Statut actuel</dt><dd>{{ review.detail.verification_status_display }}</dd></div>
                </dl>
              </section>
            </div>

            <section>
              <h3>Description</h3>
              <p class="ie-review-text">{{ review.detail.description || "Aucune description." }}</p>
              <p v-if="review.detail.specialties" class="ie-review-text"><strong>Spécialités :</strong> {{ review.detail.specialties }}</p>
            </section>

            <section v-if="review.detail.services.length">
              <h3>Services ({{ review.detail.services.length }})</h3>
              <ul class="ie-review-services">
                <li v-for="sv in review.detail.services" :key="sv.id">
                  <strong>{{ sv.name }}</strong>
                  <span>{{ sv.pricing_type === "fixed" ? `À partir de ${Number(sv.price_from).toLocaleString("fr-FR")} ${sv.currency}` : "Sur devis" }}</span>
                </li>
              </ul>
            </section>

            <section>
              <h3>Réalisations ({{ review.detail.portfolio_items.length }})</h3>
              <div v-if="review.detail.portfolio_items.length" class="ie-review-portfolio">
                <button v-for="(item, index) in review.detail.portfolio_items" :key="item.id" type="button" @click="openPortfolio(index)">
                  <img v-img="item.image" :alt="item.caption" />
                </button>
              </div>
              <p v-else class="ie-field-hint">Aucune réalisation publiée.</p>
            </section>
          </div>

          <footer v-if="review.detail" class="ie-review-foot">
            <span class="ie-field-hint">Attribuer le statut :</span>
            <div class="ie-review-actions">
              <button
                v-for="st in VERIFICATION_STATUSES.filter((x) => x.value !== 'not_verified')" :key="st.value" type="button"
                class="ie-btn ie-btn-sm" :class="review.detail.verification_status === st.value ? 'ie-btn-primary' : 'ie-btn-ghost'"
                :disabled="saving[review.summary.id]" @click="decide(st.value)"
              >
                <i class="fa-solid fa-circle-check"></i> {{ st.label }}
              </button>
              <button type="button" class="ie-btn ie-btn-sm ie-btn-danger" :disabled="saving[review.summary.id]" @click="decide('not_verified')">
                <i class="fa-solid fa-ban"></i> Non vérifié
              </button>
            </div>
          </footer>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.ie-badge-toggle input { width: 18px; height: 18px; cursor: pointer; }
.ie-owner-mode-toggle { display: flex; gap: 8px; margin-top: 6px; }
.ie-profile-link { padding: 0; border: 0; background: none; color: var(--ie-navy); font: inherit; font-weight: 700; cursor: pointer; text-align: left; }
.ie-profile-link:hover { color: var(--ie-red); text-decoration: underline; }
.ie-cni-badge { margin-left: 6px; font-size: 10px; }
.ie-cni-ok { margin-left: 6px; color: var(--ie-success); font-weight: 600; }

.ie-verif-queue { margin-bottom: 20px; border-left: 4px solid var(--ie-warning); }
.ie-verif-queue h2 { display: flex; align-items: center; gap: 10px; margin: 0 0 6px; font-size: 17px; color: var(--ie-navy); }
.ie-verif-queue h2 i { color: var(--ie-warning); }
.ie-verif-queue h2 span { padding: 1px 9px; border-radius: 999px; background: var(--ie-warning); color: #fff; font-size: 12px; }
.ie-verif-list { display: grid; gap: 8px; }
.ie-verif-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid var(--ie-line); border-radius: 10px; }
.ie-verif-avatar { display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; overflow: hidden; border-radius: 10px; background: var(--ie-navy-soft); color: var(--ie-navy); }
.ie-verif-avatar img { width: 100%; height: 100%; object-fit: cover; }
.ie-verif-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.ie-verif-info strong { color: var(--ie-navy); font-size: 14px; }
.ie-verif-info span { color: var(--ie-muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.ie-review-overlay { position: fixed; inset: 0; z-index: 950; display: flex; align-items: center; justify-content: center; padding: 20px; background: rgba(20, 30, 40, 0.55); }
.ie-review { display: flex; flex-direction: column; width: min(860px, 100%); max-height: calc(100dvh - 40px); overflow: hidden; border-radius: 18px; background: #fff; box-shadow: 0 30px 80px #0005; }
.ie-review-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 22px; border-bottom: 1px solid var(--ie-line); }
.ie-review-head h2 { margin: 2px 0 0; font-size: 19px; color: var(--ie-navy); }
.ie-review-close { width: 36px; height: 36px; border: 0; border-radius: 50%; background: #f2f4f6; color: var(--ie-navy); cursor: pointer; }
.ie-review-body { flex: 1; overflow-y: auto; padding: 18px 22px; display: flex; flex-direction: column; gap: 18px; }
.ie-review-body h3 { margin: 0 0 10px; font-size: 13px; color: var(--ie-navy); text-transform: uppercase; letter-spacing: 0.05em; }
.ie-review-cover { position: relative; height: 150px; border-radius: 14px; background: linear-gradient(120deg, var(--ie-navy), #1f2a3d); margin-bottom: 26px; }
.ie-review-cover.empty { height: 80px; }
.ie-review-cover > img { width: 100%; height: 100%; object-fit: cover; border-radius: 14px; cursor: zoom-in; }
.ie-review-logo { position: absolute; left: 18px; bottom: -26px; display: grid; place-items: center; width: 72px; height: 72px; overflow: hidden; border: 4px solid #fff; border-radius: 16px; background: #fff; color: var(--ie-navy); box-shadow: 0 4px 14px #0002; }
.ie-review-logo img { width: 100%; height: 100%; object-fit: cover; }
.ie-review-checks { display: flex; flex-wrap: wrap; gap: 6px; }
.ie-review-checks span { padding: 5px 10px; border-radius: 999px; background: #f6e2e3; color: var(--ie-red); font-size: 12px; font-weight: 600; }
.ie-review-checks span.done { background: var(--ie-success-soft); color: var(--ie-success); }
.ie-review-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.ie-review-cni { position: relative; display: block; width: 100%; padding: 0; overflow: hidden; border: 1px solid var(--ie-line); border-radius: 12px; background: #f4f6f8; cursor: zoom-in; }
.ie-review-cni img { display: block; width: 100%; max-height: 240px; object-fit: contain; }
.ie-review-cni span { position: absolute; right: 8px; bottom: 8px; padding: 4px 9px; border-radius: 999px; background: #000000a0; color: #fff; font-size: 11px; font-weight: 700; }
.ie-review-dl { margin: 0; }
.ie-review-dl div { display: flex; justify-content: space-between; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--ie-line); font-size: 13px; }
.ie-review-dl dt { color: var(--ie-muted); }
.ie-review-dl dd { margin: 0; color: var(--ie-navy); font-weight: 600; text-align: right; overflow-wrap: anywhere; }
.ie-review-text { margin: 0 0 6px; color: #3c4b5b; font-size: 13.5px; line-height: 1.6; white-space: pre-line; }
.ie-review-services { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.ie-review-services li { display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px; border: 1px solid var(--ie-line); border-radius: 8px; font-size: 13px; }
.ie-review-services span { color: var(--ie-muted); }
.ie-review-portfolio { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; }
.ie-review-portfolio button { aspect-ratio: 1; padding: 0; overflow: hidden; border: 0; border-radius: 8px; cursor: zoom-in; }
.ie-review-portfolio img { width: 100%; height: 100%; object-fit: cover; }
.ie-review-foot { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 14px 22px; border-top: 1px solid var(--ie-line); background: #fafbfc; }
.ie-review-actions { display: flex; flex-wrap: wrap; gap: 6px; }
@media (max-width: 700px) {
  .ie-review-overlay { padding: 0; align-items: flex-end; }
  .ie-review { max-height: 92dvh; border-radius: 18px 18px 0 0; }
  .ie-review-grid { grid-template-columns: 1fr; }
}
</style>
