<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const auth = useAuthStore();
const isAdmin = auth.role === "admin";

const TYPES = [
  { value: "moto", label: "Moto" },
  { value: "tricycle", label: "Tricycle" },
  { value: "car", label: "Voiture" },
  { value: "pickup", label: "Pickup" },
  { value: "van", label: "Camionnette" },
  { value: "truck", label: "Camion" },
  { value: "other", label: "Autre" },
];
const STATUSES = [
  { value: "available", label: "Disponible" },
  { value: "in_use", label: "En mission" },
  { value: "maintenance", label: "En maintenance" },
  { value: "unavailable", label: "Indisponible" },
];
const STATUS_BADGE = { available: "ie-badge-success", in_use: "ie-badge-warning", maintenance: "ie-badge-danger", unavailable: "ie-badge-neutral" };

const vehicles = ref([]);
const carriers = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = {
  plate_number: "", brand: "", model: "", year: null, vehicle_type: "car", capacity_kg: null,
  max_volume_m3: null, carrier: "", insurance_expiry: "", technical_inspection_expiry: "", status: "available", is_active: true,
};
const form = reactive({ ...emptyForm });

async function loadData() {
  loading.value = true;
  try {
    const [vehiclesRes, carriersRes] = await Promise.all([api.get("/deliveries/vehicles/"), api.get("/deliveries/carriers/")]);
    vehicles.value = vehiclesRes.data.results || vehiclesRes.data;
    carriers.value = carriersRes.data.results || carriersRes.data;
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

function startEdit(vehicle) {
  Object.assign(form, {
    ...emptyForm, ...vehicle, carrier: vehicle.carrier || "",
    insurance_expiry: vehicle.insurance_expiry || "", technical_inspection_expiry: vehicle.technical_inspection_expiry || "",
  });
  editingId.value = vehicle.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = {
      ...form, carrier: form.carrier || null,
      insurance_expiry: form.insurance_expiry || null, technical_inspection_expiry: form.technical_inspection_expiry || null,
    };
    if (editingId.value) {
      await api.patch(`/deliveries/vehicles/${editingId.value}/`, payload);
    } else {
      await api.post("/deliveries/vehicles/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Véhicule enregistré.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.plate_number?.[0] || e?.response?.data?.detail || "Impossible d'enregistrer ce véhicule.";
  } finally {
    submitting.value = false;
  }
}

async function deleteVehicle(vehicle) {
  if (!confirm(`Supprimer le véhicule « ${vehicle.plate_number} » ?`)) return;
  await api.delete(`/deliveries/vehicles/${vehicle.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-truck" style="color: var(--ie-red); margin-right: 8px;"></i>Véhicules</h1>
        <p class="ie-page-subtitle">Flotte de véhicules disponibles pour les livraisons.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau véhicule" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Immatriculation</label>
            <input v-model="form.plate_number" class="ie-input" required :disabled="!!editingId" />
          </div>
          <div>
            <label class="ie-label">Type</label>
            <select v-model="form.vehicle_type" class="ie-select">
              <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Marque</label>
            <input v-model="form.brand" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Modèle</label>
            <input v-model="form.model" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Capacité (kg)</label>
            <input v-model.number="form.capacity_kg" type="number" min="0" class="ie-input" />
          </div>
          <div v-if="isAdmin">
            <label class="ie-label">Transporteur</label>
            <select v-model="form.carrier" class="ie-select">
              <option value="">—</option>
              <option v-for="c in carriers" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Expiration assurance</label>
            <input v-model="form.insurance_expiry" type="date" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Expiration contrôle technique</label>
            <input v-model="form.technical_inspection_expiry" type="date" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Statut</label>
        <select v-model="form.status" class="ie-select" style="max-width: 240px;">
          <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Véhicule actif
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="vehicles.length">
        <table class="ie-table">
          <thead>
            <tr><th>Immatriculation</th><th>Type</th><th>Transporteur</th><th>Capacité</th><th>Statut</th><th>Alertes</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="v in vehicles" :key="v.id">
              <td><strong>{{ v.plate_number }}</strong></td>
              <td>{{ TYPES.find((t) => t.value === v.vehicle_type)?.label }}</td>
              <td>{{ v.carrier_name || "—" }}</td>
              <td class="ie-num">{{ v.capacity_kg ? `${v.capacity_kg} kg` : "—" }}</td>
              <td><span class="ie-badge" :class="STATUS_BADGE[v.status]">{{ STATUSES.find((s) => s.value === v.status)?.label }}</span></td>
              <td>
                <span v-if="v.is_insurance_expiring_soon" class="ie-badge ie-badge-danger">Assurance</span>
                <span v-if="v.is_inspection_expiring_soon" class="ie-badge ie-badge-danger">Contrôle</span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(v)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteVehicle(v)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-truck" text="Aucun véhicule enregistré pour le moment." />
    </div>
  </div>
</template>
