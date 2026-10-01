<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const CATEGORIES = [
  { value: "dj", label: "DJ" },
  { value: "caterer", label: "Traiteur" },
  { value: "decoration", label: "Décoration" },
  { value: "security", label: "Sécurité" },
  { value: "photography", label: "Photographie" },
  { value: "video", label: "Vidéo" },
  { value: "pastry", label: "Pâtisserie" },
  { value: "animation", label: "Animation (MC, artistes, danseurs...)" },
  { value: "impresario", label: "Impresario" },
  { value: "graphic_design", label: "Graphisme & infographie" },
  { value: "printing", label: "Impression" },
  { value: "other", label: "Autre" },
];

const providers = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = { name: "", category: "dj", contact_email: "", contact_phone: "", address: "", city: "", price_range: "", identity_number: "", description: "", is_active: true };
const form = reactive({ ...emptyForm });

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  if (!photoFile.value) return form;
  const payload = new FormData();
  Object.entries(form).forEach(([key, value]) => payload.append(key, value));
  payload.append("photo", photoFile.value);
  return payload;
}

function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label || value;
}

async function loadProviders() {
  loading.value = true;
  try {
    const { data } = await api.get("/providers/");
    providers.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  photoFile.value = null;
  showForm.value = true;
}

function startEdit(provider) {
  Object.assign(form, provider);
  editingId.value = provider.id;
  photoFile.value = null;
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/providers/${editingId.value}/`, payload);
    } else {
      await api.post("/providers/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Prestataire enregistré.");
    await loadProviders();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce prestataire.";
  } finally {
    submitting.value = false;
  }
}

async function deleteProvider(provider) {
  if (!confirm(`Supprimer « ${provider.name} » ?`)) return;
  await api.delete(`/providers/${provider.id}/`);
  await loadProviders();
}

async function downloadBadge(provider) {
  const response = await api.get(`/providers/${provider.id}/badge/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `badge-${provider.name}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

onMounted(loadProviders);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-handshake" style="color: var(--ie-red); margin-right: 8px;"></i>Fournisseurs</h1>
        <p class="ie-page-subtitle">Gestion complète des prestataires, toutes catégories confondues.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau fournisseur" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select">
              <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Email de contact</label>
            <input v-model="form.contact_email" type="email" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Téléphone</label>
            <input v-model="form.contact_phone" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Adresse</label>
            <input v-model="form.address" class="ie-input" placeholder="Quartier, rue…" />
          </div>
          <div>
            <label class="ie-label">Ville</label>
            <input v-model="form.city" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Fourchette de prix</label>
            <input v-model="form.price_range" class="ie-input" placeholder="Ex: 50 000 - 150 000 XAF" />
          </div>
          <div>
            <label class="ie-label">Numéro de pièce d'identité</label>
            <input v-model="form.identity_number" class="ie-input" placeholder="CNI, passeport, RCCM…" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Fournisseur actif
        </label>
        <p v-if="errorMessage" style="color: var(--ie-red); font-size: 13px; margin-top: 10px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="providers.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Catégorie</th><th>Ville</th><th>Contact</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="provider in providers" :key="provider.id">
              <td><strong>{{ provider.name }}</strong></td>
              <td>{{ categoryLabel(provider.category) }}</td>
              <td>{{ provider.city || "—" }}</td>
              <td>
                <div>{{ provider.contact_phone || "—" }}</div>
                <div style="color: var(--ie-muted); font-size: 12px;">{{ provider.contact_email }}</div>
              </td>
              <td><span class="ie-badge" :class="provider.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ provider.is_active ? "Actif" : "Inactif" }}</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="downloadBadge(provider)">
                  <i class="fa-solid fa-id-card"></i> Badge
                </button>
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(provider)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteProvider(provider)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-handshake" text="Aucun fournisseur enregistré." />
    </div>
  </div>
</template>
