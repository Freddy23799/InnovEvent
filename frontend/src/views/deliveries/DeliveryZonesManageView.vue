<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const zones = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = { name: "", base_fee: 0, price_per_km: 0, price_per_kg: 0, urgent_surcharge_percent: 0, order: 0, is_active: true };
const form = reactive({ ...emptyForm });

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/deliveries/zones/");
    zones.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(zone) {
  Object.assign(form, zone);
  editingId.value = zone.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    if (editingId.value) {
      await api.patch(`/deliveries/zones/${editingId.value}/`, form);
    } else {
      await api.post("/deliveries/zones/", form);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Zone enregistrée.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette zone.";
  } finally {
    submitting.value = false;
  }
}

async function deleteZone(zone) {
  if (!confirm(`Supprimer la zone « ${zone.name} » ?`)) return;
  await api.delete(`/deliveries/zones/${zone.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-map-location-dot" style="color: var(--ie-red); margin-right: 8px;"></i>Zones & tarifs de livraison</h1>
        <p class="ie-page-subtitle">Tarification transparente par zone : tarif de base, prix au km, prix au kg, majoration urgence.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle zone" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <label class="ie-label">Nom de la zone</label>
        <input v-model="form.name" class="ie-input" required placeholder="Ex : Zone A - Douala centre" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Tarif de base (XAF)</label>
            <input v-model.number="form.base_fee" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Prix / km (XAF)</label>
            <input v-model.number="form.price_per_km" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix / kg (XAF)</label>
            <input v-model.number="form.price_per_kg" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Majoration urgence (%)</label>
            <input v-model.number="form.urgent_surcharge_percent" type="number" min="0" max="100" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Ordre d'affichage</label>
        <input v-model.number="form.order" type="number" min="0" class="ie-input" style="max-width: 160px;" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Zone active
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="zones.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Base</th><th>Prix/km</th><th>Prix/kg</th><th>Urgence</th><th>Active</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="z in zones" :key="z.id">
              <td><strong>{{ z.name }}</strong></td>
              <td class="ie-num">{{ Number(z.base_fee).toLocaleString('fr-FR') }} XAF</td>
              <td class="ie-num">{{ Number(z.price_per_km).toLocaleString('fr-FR') }} XAF</td>
              <td class="ie-num">{{ Number(z.price_per_kg).toLocaleString('fr-FR') }} XAF</td>
              <td>+{{ z.urgent_surcharge_percent }}%</td>
              <td><span class="ie-badge" :class="z.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ z.is_active ? "Oui" : "Non" }}</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(z)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteZone(z)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-map-location-dot" text="Aucune zone tarifaire créée pour le moment." />
    </div>
  </div>
</template>
