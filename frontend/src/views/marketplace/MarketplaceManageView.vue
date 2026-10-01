<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const MARKETPLACE_TYPES = [
  { value: "sale", label: "Marketplace vente" },
  { value: "interior_design", label: "Décoration & design intérieur" },
  { value: "actors", label: "Marketplace des acteurs" },
];

const listings = ref([]);
const providers = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = {
  marketplace_type: "sale", provider: "", title: "", description: "",
  price: 0, currency: "XAF", is_active: true, requires_subscription: false, order: 0,
};
const form = reactive({ ...emptyForm });

// Par défaut, la Marketplace vente est en accès libre (mode client simple) ; les
// deux autres nécessitent un abonnement — l'administrateur peut toujours changer
// ce réglage pour chaque annonce individuellement.
function onTypeChange() {
  form.requires_subscription = form.marketplace_type !== "sale";
}

async function loadData() {
  loading.value = true;
  try {
    const [listingsRes, providersRes] = await Promise.all([
      api.get("/marketplace/listings/"),
      api.get("/providers/"),
    ]);
    listings.value = listingsRes.data.results || listingsRes.data;
    providers.value = providersRes.data.results || providersRes.data;
  } finally {
    loading.value = false;
  }
}

function typeLabel(value) {
  return MARKETPLACE_TYPES.find((t) => t.value === value)?.label || value;
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(listing) {
  Object.assign(form, { ...listing, provider: listing.provider || "" });
  editingId.value = listing.id;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  const base = { ...form, provider: form.provider || null };
  if (!photoFile.value) return base;
  const payload = new FormData();
  Object.entries(base).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    payload.append(key, value);
  });
  payload.append("photo", photoFile.value);
  return payload;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/marketplace/listings/${editingId.value}/`, payload);
    } else {
      await api.post("/marketplace/listings/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Annonce enregistrée.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette annonce.";
  } finally {
    submitting.value = false;
  }
}

async function toggleActive(listing) {
  await api.patch(`/marketplace/listings/${listing.id}/`, { is_active: !listing.is_active });
  await loadData();
}

async function deleteListing(listing) {
  if (!confirm(`Supprimer définitivement « ${listing.title} » ? Préférez « Masquer » si vous pensez la republier un jour.`)) return;
  await api.delete(`/marketplace/listings/${listing.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-store" style="color: var(--ie-red); margin-right: 8px;"></i>Marketplaces Premium</h1>
        <p class="ie-page-subtitle">Annonces des 3 marketplaces réservés aux clients abonnés. Masquez une annonce plutôt que de la supprimer si vous comptez la republier.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle annonce" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Marketplace</label>
            <select v-model="form.marketplace_type" class="ie-select" @change="onTypeChange">
              <option v-for="t in MARKETPLACE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Prestataire associé (optionnel)</label>
            <select v-model="form.provider" class="ie-select">
              <option value="">— Aucun —</option>
              <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Titre</label>
        <input v-model="form.title" class="ie-input" required placeholder="Ex : Chaises Chiavari dorées (lot de 50)" />
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix</label>
            <input v-model.number="form.price" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Devise</label>
            <select v-model="form.currency" class="ie-select">
              <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Annonce visible (décocher pour masquer sans supprimer)
        </label>
        <div class="ie-discount-fieldset">
          <label style="display:flex; align-items:center; gap:8px; font-size:14px;">
            <input v-model="form.requires_subscription" type="checkbox" />
            Réservée aux comptes abonnés à ce marketplace
          </label>
          <p class="ie-field-hint" style="margin-top: 8px;">
            Décoché = accès libre : visible par tout client connecté, sans abonnement (« mode client simple »).
            Coché = visible uniquement par les clients ayant souscrit un abonnement à « {{ MARKETPLACE_TYPES.find((t) => t.value === form.marketplace_type)?.label }} ».
          </p>
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="listings.length">
        <table class="ie-table">
          <thead>
            <tr>
              <th>Marketplace</th><th>Titre</th><th>Prestataire</th><th class="ie-num">Prix</th><th>Accès</th><th>Statut</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="listing in listings" :key="listing.id">
              <td>{{ typeLabel(listing.marketplace_type) }}</td>
              <td><strong>{{ listing.title }}</strong></td>
              <td>{{ listing.provider_name || listing.created_by_name || "—" }}</td>
              <td class="ie-num">{{ Number(listing.price).toLocaleString('fr-FR') }} {{ listing.currency }}</td>
              <td>
                <span class="ie-badge" :class="listing.requires_subscription ? 'ie-badge-neutral' : 'ie-badge-success'">
                  {{ listing.requires_subscription ? "Abonnement requis" : "Libre" }}
                </span>
              </td>
              <td>
                <span class="ie-badge" :class="listing.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">
                  {{ listing.is_active ? "Visible" : "Masquée" }}
                </span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(listing)">Modifier</button>
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="toggleActive(listing)">
                  {{ listing.is_active ? "Masquer" : "Afficher" }}
                </button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteListing(listing)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-crown" text="Aucune annonce créée pour le moment." />
    </div>
  </div>
</template>
