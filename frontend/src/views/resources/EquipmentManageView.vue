<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const CATEGORIES = [
  { value: "sound", label: "Sonorisation" },
  { value: "lighting", label: "Éclairage" },
  { value: "furniture", label: "Mobilier" },
  { value: "video", label: "Vidéo" },
  { value: "other", label: "Autre" },
];

const equipment = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = { name: "", category: "sound", quantity_total: 1, price_per_unit: 0, description: "", is_active: true };
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

async function loadEquipment() {
  loading.value = true;
  try {
    const { data } = await api.get("/equipment/");
    equipment.value = data.results || data;
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

function startEdit(item) {
  Object.assign(form, item);
  editingId.value = item.id;
  photoFile.value = null;
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/equipment/${editingId.value}/`, payload);
    } else {
      await api.post("/equipment/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Équipement enregistré.");
    await loadEquipment();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce matériel.";
  } finally {
    submitting.value = false;
  }
}

async function deleteEquipment(item) {
  if (!confirm(`Supprimer « ${item.name} » ?`)) return;
  await api.delete(`/equipment/${item.id}/`);
  await loadEquipment();
}

onMounted(loadEquipment);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-toolbox" style="color: var(--ie-red); margin-right: 8px;"></i>Gestion matériel</h1>
        <p class="ie-page-subtitle">Inventaire du matériel événementiel.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau matériel" }}
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
            <label class="ie-label">Quantité initiale</label>
            <input v-model.number="form.quantity_total" type="number" min="1" class="ie-input" required :disabled="!!editingId" />
            <p v-if="editingId" class="ie-field-hint">
              Le stock se modifie désormais via <router-link :to="{ name: 'stock-movements' }">Mouvements de stock</router-link>.
            </p>
          </div>
          <div>
            <label class="ie-label">Prix / unité (XAF)</label>
            <input v-model.number="form.price_per_unit" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Matériel actif
        </label>
        <p v-if="errorMessage" style="color: var(--ie-red); font-size: 13px; margin-top: 10px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="equipment.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Catégorie</th><th class="ie-num">Quantité</th><th class="ie-num">Prix / unité</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="item in equipment" :key="item.id">
              <td><strong>{{ item.name }}</strong></td>
              <td>{{ categoryLabel(item.category) }}</td>
              <td class="ie-num">{{ item.quantity_total }}</td>
              <td class="ie-num">{{ Number(item.price_per_unit).toLocaleString('fr-FR') }} XAF</td>
              <td><span class="ie-badge" :class="item.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ item.is_active ? "Actif" : "Inactif" }}</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(item)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteEquipment(item)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-toolbox" text="Aucun matériel enregistré." />
    </div>
  </div>
</template>

<style scoped>
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
.ie-field-hint a { color: var(--ie-red); font-weight: 600; }
</style>
