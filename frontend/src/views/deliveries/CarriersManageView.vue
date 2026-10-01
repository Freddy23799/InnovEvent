<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const TYPES = [
  { value: "company", label: "Entreprise" },
  { value: "partner", label: "Partenaire" },
  { value: "independent", label: "Indépendant" },
  { value: "internal", label: "Interne" },
];
const STATUSES = [
  { value: "available", label: "Disponible" },
  { value: "busy", label: "Occupé" },
  { value: "off_duty", label: "Hors service" },
  { value: "suspended", label: "Suspendu" },
  { value: "inactive", label: "Inactif" },
];
const STATUS_BADGE = { available: "ie-badge-success", busy: "ie-badge-warning", off_duty: "ie-badge-neutral", suspended: "ie-badge-danger", inactive: "ie-badge-neutral" };

const carriers = ref([]);
const zones = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = {
  name: "", company_name: "", carrier_type: "independent", phone: "", whatsapp: "", email: "",
  address: "", service_zone: "", transport_type: "", id_number: "", status: "available", is_active: true,
};
const form = reactive({ ...emptyForm });

// --- Création d'un compte transporteur (mirror AdminProfessionalProfilesView) ---
const showAccountForm = ref(false);
const ownerMode = ref("new"); // "new" | "existing"
const partnerUsers = ref([]);
const emptyAccountForm = {
  name: "", carrier_type: "company", phone: "", whatsapp: "", email: "", address: "", service_zone: "", transport_type: "",
  owner_user: "", new_owner_username: "", new_owner_email: "", new_owner_first_name: "", new_owner_last_name: "",
};
const accountForm = reactive({ ...emptyAccountForm });
const accountSubmitting = ref(false);
const accountErrorMessage = ref("");
const lastCreatedAccount = ref(null);

async function loadPartnerUsers() {
  try {
    const { data } = await api.get("/auth/users/", { params: { role: "partner" } });
    partnerUsers.value = data.results || data;
  } catch {
    partnerUsers.value = [];
  }
}

function toggleAccountForm() {
  showAccountForm.value = !showAccountForm.value;
  if (showAccountForm.value) {
    showForm.value = false;
    Object.assign(accountForm, emptyAccountForm);
    accountErrorMessage.value = "";
    lastCreatedAccount.value = null;
    loadPartnerUsers();
  }
}

async function submitAccountForm() {
  accountErrorMessage.value = "";
  accountSubmitting.value = true;
  try {
    const payload = {
      name: accountForm.name, carrier_type: accountForm.carrier_type, phone: accountForm.phone,
      whatsapp: accountForm.whatsapp, email: accountForm.email, address: accountForm.address,
      service_zone: accountForm.service_zone || null, transport_type: accountForm.transport_type,
    };
    if (ownerMode.value === "existing") {
      payload.owner_user = accountForm.owner_user;
    } else {
      payload.new_owner_username = accountForm.new_owner_username;
      payload.new_owner_email = accountForm.new_owner_email;
      payload.new_owner_first_name = accountForm.new_owner_first_name;
      payload.new_owner_last_name = accountForm.new_owner_last_name;
    }
    const { data } = await api.post("/deliveries/carriers/admin-create/", payload);
    lastCreatedAccount.value = data;
    toast.success("Compte transporteur créé.");
    await loadData();
  } catch (e) {
    const detail = e?.response?.data?.detail;
    accountErrorMessage.value = typeof detail === "object" ? Object.values(detail).flat().join(" ") : (detail || "Impossible de créer ce compte.");
  } finally {
    accountSubmitting.value = false;
  }
}

async function loadData() {
  loading.value = true;
  try {
    const [carriersRes, zonesRes] = await Promise.all([api.get("/deliveries/carriers/"), api.get("/deliveries/zones/")]);
    carriers.value = carriersRes.data.results || carriersRes.data;
    zones.value = zonesRes.data.results || zonesRes.data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  showForm.value = true;
  showAccountForm.value = false;
}

function startEdit(carrier) {
  Object.assign(form, { ...emptyForm, ...carrier, service_zone: carrier.service_zone || "" });
  editingId.value = carrier.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = { ...form, service_zone: form.service_zone || null };
    if (editingId.value) {
      await api.patch(`/deliveries/carriers/${editingId.value}/`, payload);
    } else {
      await api.post("/deliveries/carriers/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Transporteur enregistré.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce transporteur.";
  } finally {
    submitting.value = false;
  }
}

async function deleteCarrier(carrier) {
  if (!confirm(`Supprimer le transporteur « ${carrier.name} » ?`)) return;
  await api.delete(`/deliveries/carriers/${carrier.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-truck-fast" style="color: var(--ie-red); margin-right: 8px;"></i>Transporteurs</h1>
        <p class="ie-page-subtitle">Entreprises, partenaires, indépendants ou transporteurs internes.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-secondary" @click="toggleAccountForm">
          <i class="fa-solid" :class="showAccountForm ? 'fa-xmark' : 'fa-user-plus'"></i>
          {{ showAccountForm ? "Annuler" : "Créer un compte transporteur" }}
        </button>
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau transporteur" }}
        </button>
      </div>
    </div>

    <div v-if="showAccountForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <p class="ie-page-subtitle" style="margin-top: 0;">
        Crée un transporteur ET un compte de connexion associé (rôle prestataire), pour qu'il gère lui-même sa flotte et ses livraisons.
      </p>
      <div v-if="lastCreatedAccount" class="ie-alert ie-alert-success" style="margin-bottom: 14px;">
        <i class="fa-solid fa-circle-check"></i> Transporteur « {{ lastCreatedAccount.name }} » créé.
        <template v-if="lastCreatedAccount.generated_password">
          <br />Compte <strong>{{ lastCreatedAccount.owner_username }}</strong> — mot de passe généré : <code>{{ lastCreatedAccount.generated_password }}</code>
          <span class="ie-field-hint"> (à transmettre au transporteur — ne sera plus affiché ensuite)</span>
        </template>
      </div>

      <form @submit.prevent="submitAccountForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom du transporteur</label>
            <input v-model="accountForm.name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Type</label>
            <select v-model="accountForm.carrier_type" class="ie-select">
              <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Téléphone</label>
            <input v-model="accountForm.phone" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Zone de service</label>
            <select v-model="accountForm.service_zone" class="ie-select">
              <option value="">—</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
        </div>

        <label class="ie-label" style="margin-top: 18px;">Compte transporteur</label>
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
              <input v-model="accountForm.new_owner_username" class="ie-input" required placeholder="Ex : transporteur_kamga" />
            </div>
            <div>
              <label class="ie-label">Email</label>
              <input v-model="accountForm.new_owner_email" type="email" class="ie-input" />
            </div>
          </div>
          <div class="ie-form-row" style="margin-top: 10px;">
            <div>
              <label class="ie-label">Prénom</label>
              <input v-model="accountForm.new_owner_first_name" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Nom</label>
              <input v-model="accountForm.new_owner_last_name" class="ie-input" />
            </div>
          </div>
          <p class="ie-field-hint" style="margin-top: 6px;">Un mot de passe sera généré automatiquement et affiché une seule fois après création.</p>
        </template>
        <template v-else>
          <select v-model="accountForm.owner_user" class="ie-select" style="margin-top: 10px;" required>
            <option value="" disabled>Choisir un compte prestataire…</option>
            <option v-for="u in partnerUsers" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
          </select>
          <p v-if="!partnerUsers.length" class="ie-field-hint" style="margin-top: 6px;">Aucun compte prestataire disponible sans transporteur — créez-en un nouveau plutôt.</p>
        </template>

        <p v-if="accountErrorMessage" class="ie-alert ie-alert-danger" style="margin-top: 14px;">{{ accountErrorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="accountSubmitting">
          {{ accountSubmitting ? "Création…" : "Créer ce compte transporteur" }}
        </button>
      </form>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Type</label>
            <select v-model="form.carrier_type" class="ie-select">
              <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Téléphone</label>
            <input v-model="form.phone" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">WhatsApp</label>
            <input v-model="form.whatsapp" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Email</label>
            <input v-model="form.email" type="email" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Zone de service</label>
            <select v-model="form.service_zone" class="ie-select">
              <option value="">—</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Adresse</label>
        <input v-model="form.address" class="ie-input" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Type de transport</label>
            <input v-model="form.transport_type" class="ie-input" placeholder="Ex : moto, camion, mixte..." />
          </div>
          <div>
            <label class="ie-label">Statut</label>
            <select v-model="form.status" class="ie-select">
              <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
        </div>
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Transporteur actif
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="carriers.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Type</th><th>Téléphone</th><th>Zone</th><th>Compte</th><th>Statut</th><th>Livraisons</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="c in carriers" :key="c.id">
              <td><strong>{{ c.name }}</strong></td>
              <td>{{ TYPES.find((t) => t.value === c.carrier_type)?.label }}</td>
              <td>{{ c.phone }}</td>
              <td>{{ c.service_zone_name || "—" }}</td>
              <td>
                <span v-if="c.username" class="ie-badge ie-badge-success">{{ c.username }}</span>
                <span v-else style="color: var(--ie-muted); font-size: 12px;">Aucun</span>
              </td>
              <td><span class="ie-badge" :class="STATUS_BADGE[c.status]">{{ STATUSES.find((s) => s.value === c.status)?.label }}</span></td>
              <td class="ie-num">{{ c.deliveries_count }}</td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(c)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteCarrier(c)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-truck-fast" text="Aucun transporteur enregistré pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-owner-mode-toggle { display: flex; gap: 8px; margin-top: 6px; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
</style>
