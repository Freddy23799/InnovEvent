<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const props = defineProps({ packId: { type: [String, Number], required: true } });

const router = useRouter();
const toast = useToastStore();

const TIERS = [
  { value: "", label: "—" },
  { value: "haut", label: "Haut de gamme" },
  { value: "moyen", label: "Moyenne gamme" },
  { value: "petit", label: "Petite gamme" },
];
const RESOURCE_TYPES = [
  { value: "venue", label: "Salle" },
  { value: "provider", label: "Prestataire" },
  { value: "equipment", label: "Matériel" },
];

const loading = ref(true);
const notFound = ref(false);
const pack = ref(null);
const photoFile = ref(null);
const submitting = ref(false);
const errorMessage = ref("");

const form = reactive({ label: "", caption: "", tier: "", budget_label: "", order: 0, is_active: true });

const venues = ref([]);
const providers = ref([]);
const equipmentList = ref([]);
const packItems = ref([]);
const packItemForm = reactive({ resource_type: "venue", resource_id: "", default_quantity: 1, is_optional: false });
const packItemSubmitting = ref(false);

const RESOURCE_OPTIONS = computed(() => {
  if (packItemForm.resource_type === "venue") return venues.value;
  if (packItemForm.resource_type === "provider") return providers.value;
  return equipmentList.value;
});

// Créer directement un nouveau composant (matériel ou salle) avec sa photo,
// plutôt que d'obliger l'administrateur à aller le créer ailleurs puis
// revenir ici pour le sélectionner. Les prestataires restent créés depuis
// « Prestataires » (compte + profil), trop complexe pour un formulaire inline.
const componentMode = ref("existing"); // "existing" | "new"
const CREATABLE_TYPES = new Set(["venue", "equipment"]);
const emptyNewComponentForm = { name: "", price: 0, description: "", city: "" };
const newComponentForm = reactive({ ...emptyNewComponentForm });
const newComponentPhoto = ref(null);

function onNewComponentPhotoChange(e) {
  newComponentPhoto.value = e.target.files[0] || null;
}

function resetNewComponentForm() {
  Object.assign(newComponentForm, emptyNewComponentForm);
  newComponentPhoto.value = null;
}

async function loadPack() {
  loading.value = true;
  notFound.value = false;
  try {
    const { data } = await api.get(`/public/landing-media/${props.packId}/`);
    pack.value = data;
    Object.assign(form, {
      label: data.label, caption: data.caption || "", tier: data.tier || "",
      budget_label: data.budget_label || "", order: data.order, is_active: data.is_active,
    });
  } catch (e) {
    notFound.value = true;
  } finally {
    loading.value = false;
  }
}

async function loadPackItems() {
  const { data } = await api.get("/public/pack-items/", { params: { pack: props.packId } });
  packItems.value = data;
}

async function loadResourceCatalogs() {
  const [venuesRes, providersRes, equipmentRes] = await Promise.all([
    api.get("/venues/"),
    api.get("/providers/"),
    api.get("/equipment/"),
  ]);
  venues.value = venuesRes.data.results || venuesRes.data;
  providers.value = providersRes.data.results || providersRes.data;
  equipmentList.value = equipmentRes.data.results || equipmentRes.data;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = new FormData();
    payload.append("category", "pack");
    Object.entries(form).forEach(([key, value]) => payload.append(key, value));
    if (photoFile.value) payload.append("photo", photoFile.value);
    const { data } = await api.patch(`/public/landing-media/${props.packId}/`, payload);
    pack.value = data;
    photoFile.value = null;
    toast.success("Modifications enregistrées.");
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce pack.";
  } finally {
    submitting.value = false;
  }
}

async function createNewComponent() {
  const type = packItemForm.resource_type;
  if (type === "equipment") {
    const payload = new FormData();
    payload.append("name", newComponentForm.name);
    payload.append("price_per_unit", newComponentForm.price);
    payload.append("description", newComponentForm.description);
    payload.append("category", "other");
    if (newComponentPhoto.value) payload.append("photo", newComponentPhoto.value);
    const { data } = await api.post("/equipment/", payload);
    equipmentList.value.unshift(data);
    return data.id;
  }
  // venue
  const payload = new FormData();
  payload.append("name", newComponentForm.name);
  payload.append("price_per_day", newComponentForm.price);
  payload.append("description", newComponentForm.description);
  payload.append("city", newComponentForm.city);
  if (newComponentPhoto.value) payload.append("photo", newComponentPhoto.value);
  const { data } = await api.post("/venues/", payload);
  venues.value.unshift(data);
  return data.id;
}

async function addPackItem() {
  if (componentMode.value === "existing" && !packItemForm.resource_id) return;
  if (componentMode.value === "new" && !newComponentForm.name.trim()) return;
  packItemSubmitting.value = true;
  try {
    const resourceId = componentMode.value === "new" ? await createNewComponent() : packItemForm.resource_id;
    await api.post("/public/pack-items/", {
      pack: props.packId,
      resource_type: packItemForm.resource_type,
      [packItemForm.resource_type]: resourceId,
      default_quantity: packItemForm.default_quantity,
      is_optional: packItemForm.is_optional,
      order: packItems.value.length + 1,
    });
    await loadPackItems();
    Object.assign(packItemForm, { resource_id: "", default_quantity: 1, is_optional: false });
    resetNewComponentForm();
    toast.success(componentMode.value === "new" ? "Composant créé et ajouté au pack." : "Composant ajouté au pack.");
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d'ajouter ce composant.");
  } finally {
    packItemSubmitting.value = false;
  }
}

async function deletePackItem(item) {
  if (!confirm(`Retirer « ${item.resource_name} » de ce pack ?`)) return;
  await api.delete(`/public/pack-items/${item.id}/`);
  packItems.value = packItems.value.filter((i) => i.id !== item.id);
}

onMounted(() => {
  loadPack();
  loadPackItems();
  loadResourceCatalogs();
});
</script>

<template>
  <div>
    <div v-if="loading" class="ie-skeleton" style="height: 300px;"></div>

    <div v-else-if="notFound" class="ie-card ie-card-body">
      <p>Ce pack n'existe plus.</p>
      <router-link :to="{ name: 'landing-media' }" class="ie-btn ie-btn-ghost" style="margin-top: 12px;">
        <i class="fa-solid fa-arrow-left"></i> Retour au site vitrine
      </router-link>
    </div>

    <template v-else>
      <div class="ie-page-header">
        <div>
          <router-link :to="{ name: 'landing-media' }" class="pm-breadcrumb">
            <i class="fa-solid fa-arrow-left"></i> Site vitrine
          </router-link>
          <h1 style="margin-top: 6px;"><i class="fa-solid fa-gift" style="color: var(--ie-red); margin-right: 8px;"></i>{{ pack.label }}</h1>
          <p class="ie-page-subtitle">Description du pack et composants inclus — tel qu'affiché sur la page d'accueil et la fiche publique.</p>
        </div>
      </div>

      <div class="pm-layout">
        <section class="ie-card ie-card-body">
          <h2 class="pm-section-title"><i class="fa-solid fa-pen"></i> Description du pack</h2>
          <form @submit.prevent="submitForm">
            <label class="ie-label">Libellé</label>
            <input v-model="form.label" class="ie-input" required placeholder="Ex : Pack Prestige" />

            <label class="ie-label" style="margin-top: 14px;">Description</label>
            <textarea v-model="form.caption" class="ie-input" rows="3" placeholder="Ex : Décoration haut de gamme, mobilier premium, service traiteur complet."></textarea>
            <p class="ie-field-hint">Chaque phrase séparée par une virgule s'affiche comme un point de la liste « ce pack inclut » sur la fiche publique.</p>

            <div class="ie-form-row" style="margin-top: 14px;">
              <div>
                <label class="ie-label">Gamme</label>
                <select v-model="form.tier" class="ie-select">
                  <option v-for="t in TIERS" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
              </div>
              <div>
                <label class="ie-label">Prix affiché</label>
                <input v-model="form.budget_label" class="ie-input" placeholder="Ex : 1 200 000 FCFA" />
              </div>
            </div>

            <div class="ie-form-row" style="margin-top: 14px;">
              <div>
                <label class="ie-label">Ordre d'affichage</label>
                <input v-model.number="form.order" type="number" min="0" class="ie-input" />
              </div>
              <div>
                <label class="ie-label">Photo</label>
                <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
              </div>
            </div>

            <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
              <input v-model="form.is_active" type="checkbox" /> Visible sur la page d'accueil
            </label>

            <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
            <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
              {{ submitting ? "Enregistrement…" : "Enregistrer" }}
            </button>
          </form>
        </section>

        <section class="ie-card ie-card-body">
          <h2 class="pm-section-title"><i class="fa-solid fa-boxes-stacked"></i> Composants du pack</h2>
          <p class="ie-field-hint" style="margin-bottom: 14px;">Salles, prestataires ou matériel inclus dans ce pack — affichés sur la fiche publique, réservables séparément.</p>

          <div v-if="packItems.length" class="pm-items-list">
            <div v-for="pi in packItems" :key="pi.id" class="pm-item-row">
              <div class="pm-item-thumb">
                <img v-if="pi.resource_photo" :src="pi.resource_photo" :alt="pi.resource_name" />
                <i v-else class="fa-solid fa-image"></i>
              </div>
              <span class="ie-badge ie-badge-neutral">{{ RESOURCE_TYPES.find((r) => r.value === pi.resource_type)?.label }}</span>
              <span class="pm-item-name">{{ pi.resource_name }}</span>
              <span v-if="pi.resource_price_label" class="pm-item-price">{{ pi.resource_price_label }}</span>
              <span v-if="pi.resource_type === 'equipment'" class="pm-item-qty">× {{ pi.default_quantity }}</span>
              <span v-if="pi.is_optional" class="ie-badge ie-badge-warning">Option</span>
              <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deletePackItem(pi)"><i class="fa-solid fa-trash"></i></button>
            </div>
          </div>
          <p v-else class="ie-field-hint">Aucun composant pour ce pack pour le moment.</p>

          <form class="pm-item-form" @submit.prevent="addPackItem">
            <label class="ie-label" style="margin-top: 16px;">Ajouter un composant</label>
            <div class="pm-item-form-row">
              <select
                v-model="packItemForm.resource_type" class="ie-select"
                @change="packItemForm.resource_id = ''; componentMode = 'existing'"
              >
                <option v-for="rt in RESOURCE_TYPES" :key="rt.value" :value="rt.value">{{ rt.label }}</option>
              </select>
            </div>

            <div v-if="CREATABLE_TYPES.has(packItemForm.resource_type)" class="pm-mode-toggle">
              <button type="button" class="pm-mode-btn" :class="{ 'is-active': componentMode === 'existing' }" @click="componentMode = 'existing'">
                Choisir un existant
              </button>
              <button type="button" class="pm-mode-btn" :class="{ 'is-active': componentMode === 'new' }" @click="componentMode = 'new'">
                <i class="fa-solid fa-plus"></i> Créer un nouveau composant
              </button>
            </div>

            <div v-if="componentMode === 'existing'" class="pm-item-form-row" style="margin-top: 10px;">
              <select v-model="packItemForm.resource_id" class="ie-select" :required="componentMode === 'existing'">
                <option value="" disabled>Choisir…</option>
                <option v-for="opt in RESOURCE_OPTIONS" :key="opt.id" :value="opt.id">{{ opt.name }}</option>
              </select>
            </div>

            <div v-else class="pm-new-component">
              <label class="ie-label">Nom</label>
              <input v-model="newComponentForm.name" class="ie-input" :required="componentMode === 'new'" placeholder="Ex : Chaises Chiavari dorées" />
              <div class="pm-item-form-row" style="margin-top: 10px;">
                <div style="flex: 1;">
                  <label class="ie-label">{{ packItemForm.resource_type === 'venue' ? 'Prix / jour' : 'Prix / unité' }}</label>
                  <input v-model.number="newComponentForm.price" type="number" min="0" class="ie-input" placeholder="XAF" />
                </div>
                <div v-if="packItemForm.resource_type === 'venue'" style="flex: 1;">
                  <label class="ie-label">Ville</label>
                  <input v-model="newComponentForm.city" class="ie-input" placeholder="Ex : Douala" />
                </div>
              </div>
              <label class="ie-label" style="margin-top: 10px;">Description</label>
              <input v-model="newComponentForm.description" class="ie-input" placeholder="Description courte" />
              <label class="ie-label" style="margin-top: 10px;">Photo</label>
              <input type="file" accept="image/*" class="ie-input" @change="onNewComponentPhotoChange" />
            </div>

            <div class="pm-item-form-row" style="margin-top: 10px;">
              <input
                v-if="packItemForm.resource_type === 'equipment'"
                v-model.number="packItemForm.default_quantity" type="number" min="1" class="ie-input"
                placeholder="Quantité"
              />
              <label class="pm-item-optional">
                <input v-model="packItemForm.is_optional" type="checkbox" /> Composant optionnel
              </label>
            </div>
            <button class="ie-btn ie-btn-primary ie-btn-sm" type="submit" style="margin-top: 12px;" :disabled="packItemSubmitting">
              <i class="fa-solid fa-plus"></i> {{ packItemSubmitting ? "Ajout…" : (componentMode === 'new' ? "Créer et ajouter au pack" : "Ajouter au pack") }}
            </button>
          </form>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.pm-breadcrumb { display: inline-flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--ie-navy); font-weight: 600; }
.pm-breadcrumb:hover { text-decoration: underline; }
.pm-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start; }
.pm-section-title { font-size: 15px; color: var(--ie-navy); margin: 0 0 16px; display: flex; align-items: center; gap: 8px; }
.pm-section-title i { color: var(--ie-red); }

.pm-items-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }
.pm-item-row { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 9px 10px; background: #fafbfc; border: 1px solid var(--ie-line); border-radius: 8px; }
.pm-item-thumb {
  width: 38px; height: 38px; border-radius: 6px; overflow: hidden; background: var(--ie-navy-soft);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.pm-item-thumb img { width: 100%; height: 100%; object-fit: cover; }
.pm-item-thumb i { font-size: 13px; color: var(--ie-navy); opacity: 0.35; }
.pm-item-name { flex: 1; font-weight: 600; color: var(--ie-navy); }
.pm-item-price { color: var(--ie-red); font-weight: 600; font-size: 12px; white-space: nowrap; }
.pm-item-qty { color: var(--ie-muted); }
.pm-item-form-row { display: flex; gap: 10px; flex-wrap: wrap; }
.pm-item-form-row .ie-select, .pm-item-form-row .ie-input { flex: 1; min-width: 140px; }
.pm-item-optional { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ie-muted); white-space: nowrap; }

.pm-mode-toggle { display: flex; gap: 8px; margin-top: 10px; }
.pm-mode-btn {
  flex: 1; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--ie-line); background: #fff;
  font-size: 12.5px; font-weight: 600; color: var(--ie-muted); cursor: pointer; transition: all 0.15s ease;
}
.pm-mode-btn.is-active { border-color: var(--ie-red); background: var(--ie-red-soft); color: var(--ie-red); }
.pm-new-component { margin-top: 10px; padding: 12px; border: 1px dashed var(--ie-line); border-radius: 8px; background: #fafbfc; }

@media (max-width: 860px) { .pm-layout { grid-template-columns: 1fr; } }
</style>
