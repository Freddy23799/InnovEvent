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

const STATUSES = [
  { value: "available", label: "Disponible" },
  { value: "on_mission", label: "En mission" },
  { value: "off_duty", label: "Hors service" },
  { value: "suspended", label: "Suspendu" },
];
const STATUS_BADGE = { available: "ie-badge-success", on_mission: "ie-badge-warning", off_duty: "ie-badge-neutral", suspended: "ie-badge-danger" };

const drivers = ref([]);
const carriers = ref([]);
const vehicles = ref([]);
const eligibleUsers = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = {
  full_name: "", phone: "", whatsapp: "", email: "", license_number: "", license_category: "",
  license_expiry: "", address: "", carrier: "", current_vehicle: "", status: "available", is_active: true, user: "",
};
const form = reactive({ ...emptyForm });
const photoFile = ref(null);
const idCardFile = ref(null);
const licenseFile = ref(null);

async function loadData() {
  loading.value = true;
  try {
    const requests = [
      api.get("/deliveries/drivers/"), api.get("/deliveries/carriers/"), api.get("/deliveries/vehicles/"),
    ];
    if (isAdmin) requests.push(api.get("/auth/users/"));
    const [driversRes, carriersRes, vehiclesRes, usersRes] = await Promise.all(requests);
    drivers.value = driversRes.data.results || driversRes.data;
    carriers.value = carriersRes.data.results || carriersRes.data;
    vehicles.value = vehiclesRes.data.results || vehiclesRes.data;
    if (usersRes) {
      const allUsers = usersRes.data.results || usersRes.data;
      const linkedIds = new Set(drivers.value.filter((d) => d.user).map((d) => d.user));
      eligibleUsers.value = allUsers.filter((u) => u.role !== "admin" && (!linkedIds.has(u.id) || u.id === form.user));
    }
  } finally {
    loading.value = false;
  }
}

function clearFiles() {
  photoFile.value = null;
  idCardFile.value = null;
  licenseFile.value = null;
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  clearFiles();
  showForm.value = true;
}

function startEdit(driver) {
  Object.assign(form, {
    ...emptyForm, ...driver, carrier: driver.carrier || "", current_vehicle: driver.current_vehicle || "",
    license_expiry: driver.license_expiry || "", user: driver.user || "",
  });
  editingId.value = driver.id;
  errorMessage.value = "";
  clearFiles();
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const fields = {
      ...form, carrier: form.carrier || null, current_vehicle: form.current_vehicle || null,
      license_expiry: form.license_expiry || null,
    };
    if (isAdmin) fields.user = form.user || null;
    else delete fields.user;

    let payload = fields;
    if (photoFile.value || idCardFile.value || licenseFile.value) {
      payload = new FormData();
      Object.entries(fields).forEach(([key, value]) => { if (value != null) payload.append(key, value); });
      if (photoFile.value) payload.append("photo", photoFile.value);
      if (idCardFile.value) payload.append("id_card_photo", idCardFile.value);
      if (licenseFile.value) payload.append("license_photo", licenseFile.value);
    }

    if (editingId.value) {
      await api.patch(`/deliveries/drivers/${editingId.value}/`, payload);
    } else {
      await api.post("/deliveries/drivers/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Chauffeur enregistré.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce chauffeur.";
  } finally {
    submitting.value = false;
  }
}

async function deleteDriver(driver) {
  if (!confirm(`Supprimer le chauffeur « ${driver.full_name} » ?`)) return;
  await api.delete(`/deliveries/drivers/${driver.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-id-card" style="color: var(--ie-red); margin-right: 8px;"></i>Chauffeurs</h1>
        <p class="ie-page-subtitle">Chauffeurs internes ou externes, rattachés à un transporteur.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau chauffeur" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom complet</label>
            <input v-model="form.full_name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Téléphone</label>
            <input v-model="form.phone" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Numéro de permis</label>
            <input v-model="form.license_number" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Expiration du permis</label>
            <input v-model="form.license_expiry" type="date" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div v-if="isAdmin">
            <label class="ie-label">Transporteur</label>
            <select v-model="form.carrier" class="ie-select">
              <option value="">—</option>
              <option v-for="c in carriers" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Véhicule actuel</label>
            <select v-model="form.current_vehicle" class="ie-select">
              <option value="">—</option>
              <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}</option>
            </select>
          </div>
        </div>
        <template v-if="isAdmin">
          <label class="ie-label" style="margin-top: 14px;">Compte utilisateur lié (optionnel)</label>
          <select v-model="form.user" class="ie-select">
            <option value="">Aucun</option>
            <option v-for="u in eligibleUsers" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
          </select>
          <p class="ie-field-hint" style="margin-top: 4px;">Donne accès à l'espace « Mes livraisons » sur le compte choisi.</p>
        </template>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Photo du chauffeur</label>
            <input type="file" accept="image/*" class="ie-input" @change="photoFile = $event.target.files[0] || null" />
            <img v-if="editingId && form.photo && !photoFile" :src="form.photo" alt="Photo actuelle" class="ie-doc-thumb" />
          </div>
          <div>
            <label class="ie-label">Photo de la CNI</label>
            <input type="file" accept="image/*" class="ie-input" @change="idCardFile = $event.target.files[0] || null" />
            <img v-if="editingId && form.id_card_photo && !idCardFile" :src="form.id_card_photo" alt="CNI actuelle" class="ie-doc-thumb" />
          </div>
          <div>
            <label class="ie-label">Photo du permis de conduire</label>
            <input type="file" accept="image/*" class="ie-input" @change="licenseFile = $event.target.files[0] || null" />
            <img v-if="editingId && form.license_photo && !licenseFile" :src="form.license_photo" alt="Permis actuel" class="ie-doc-thumb" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Statut</label>
        <select v-model="form.status" class="ie-select" style="max-width: 240px;">
          <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Chauffeur actif
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="drivers.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Téléphone</th><th>Transporteur</th><th>Véhicule</th><th>Compte</th><th>Documents</th><th>Statut</th><th>Livraisons</th><th>Alertes</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="d in drivers" :key="d.id">
              <td><strong>{{ d.full_name }}</strong></td>
              <td>{{ d.phone }}</td>
              <td>{{ d.carrier_name || "—" }}</td>
              <td>{{ d.current_vehicle_plate || "—" }}</td>
              <td>
                <span v-if="d.username" class="ie-badge ie-badge-success">{{ d.username }}</span>
                <span v-else style="color: var(--ie-muted); font-size: 12px;">Aucun</span>
              </td>
              <td>
                <span v-if="d.photo && d.id_card_photo && d.license_photo" class="ie-badge ie-badge-success" title="CNI, permis et photo fournis">
                  <i class="fa-solid fa-check"></i> Complet
                </span>
                <span v-else class="ie-badge ie-badge-warning" title="Photo, CNI ou permis manquant">
                  <i class="fa-solid fa-triangle-exclamation"></i> Incomplet
                </span>
              </td>
              <td><span class="ie-badge" :class="STATUS_BADGE[d.status]">{{ STATUSES.find((s) => s.value === d.status)?.label }}</span></td>
              <td class="ie-num">{{ d.deliveries_count }}</td>
              <td><span v-if="d.is_license_expiring_soon" class="ie-badge ie-badge-danger">Permis</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(d)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteDriver(d)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-id-card" text="Aucun chauffeur enregistré pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
.ie-doc-thumb { width: 90px; height: 60px; object-fit: cover; border-radius: 6px; border: 1px solid var(--ie-border); margin-top: 6px; }
</style>
