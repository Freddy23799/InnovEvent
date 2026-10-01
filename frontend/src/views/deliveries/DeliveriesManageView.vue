<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const auth = useAuthStore();
// Un transporteur ne crée pas de nouvelles livraisons — il exécute celles qui
// lui sont affectées par l'administration (cf. plan « Compte transporteur »).
const isAdmin = auth.role === "admin";

const STATUSES = [
  { value: "created", label: "Créée" }, { value: "pending", label: "En attente" }, { value: "confirmed", label: "Confirmée" },
  { value: "to_prepare", label: "À préparer" }, { value: "ready", label: "Prête à récupérer" },
  { value: "carrier_assigned", label: "Transporteur affecté" }, { value: "collected", label: "Collectée" },
  { value: "in_transit", label: "En transit" }, { value: "arrived", label: "Arrivée à destination" },
  { value: "delivering", label: "En cours de livraison" }, { value: "delivered", label: "Livrée" },
  { value: "failed", label: "Échec" }, { value: "postponed", label: "Reportée" }, { value: "cancelled", label: "Annulée" },
  { value: "returning", label: "Retour en cours" }, { value: "returned", label: "Retournée" },
];
const STATUS_BADGE = {
  created: "ie-badge-neutral", pending: "ie-badge-warning", confirmed: "ie-badge-success", to_prepare: "ie-badge-warning",
  ready: "ie-badge-warning", carrier_assigned: "ie-badge-success", collected: "ie-badge-success", in_transit: "ie-badge-success",
  arrived: "ie-badge-success", delivering: "ie-badge-success", delivered: "ie-badge-success", failed: "ie-badge-danger",
  postponed: "ie-badge-warning", cancelled: "ie-badge-danger", returning: "ie-badge-warning", returned: "ie-badge-danger",
};
const TYPES = [
  { value: "local", label: "Locale" }, { value: "intercity", label: "Interurbaine" }, { value: "goods", label: "Marchandises" },
  { value: "parcel", label: "Colis" }, { value: "linked_order", label: "Liée à une commande" }, { value: "independent", label: "Indépendante" },
];

const deliveries = ref([]);
const zones = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");

const search = ref("");
const statusFilter = ref("");

const emptyForm = {
  pickup_address: "", destination_address: "", recipient_name: "", recipient_phone: "",
  delivery_type: "parcel", priority: "normal", zone: "", distance_km: null, amount: 0,
  payment_mode: "on_delivery", description: "",
  parcels: [{ description: "", quantity: 1, weight_kg: null }],
};
const form = reactive(JSON.parse(JSON.stringify(emptyForm)));

const filteredDeliveries = computed(() => {
  return deliveries.value.filter((d) => {
    if (statusFilter.value && d.status !== statusFilter.value) return false;
    if (search.value) {
      const q = search.value.toLowerCase();
      return [d.reference, d.tracking_code, d.client_phone, d.destination_address].some((f) => (f || "").toLowerCase().includes(q));
    }
    return true;
  });
});

const stats = computed(() => ({
  total: deliveries.value.length,
  pending: deliveries.value.filter((d) => d.status === "pending").length,
  inProgress: deliveries.value.filter((d) => ["carrier_assigned", "collected", "in_transit", "arrived", "delivering"].includes(d.status)).length,
  delivered: deliveries.value.filter((d) => d.status === "delivered").length,
}));

async function loadData() {
  loading.value = true;
  try {
    const [deliveriesRes, zonesRes] = await Promise.all([api.get("/deliveries/"), api.get("/deliveries/zones/")]);
    deliveries.value = deliveriesRes.data.results || deliveriesRes.data;
    zones.value = zonesRes.data.results || zonesRes.data;
  } finally {
    loading.value = false;
  }
}

function addParcelRow() {
  form.parcels.push({ description: "", quantity: 1, weight_kg: null });
}
function removeParcelRow(index) {
  form.parcels.splice(index, 1);
}

function startCreate() {
  Object.assign(form, JSON.parse(JSON.stringify(emptyForm)));
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = { ...form, zone: form.zone || null, parcels: form.parcels.filter((p) => p.description.trim()) };
    await api.post("/deliveries/", payload);
    showForm.value = false;
    toast.success("Livraison créée.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible de créer cette livraison.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-box-open" style="color: var(--ie-red); margin-right: 8px;"></i>Livraisons</h1>
        <p class="ie-page-subtitle">
          {{ isAdmin ? "Créer, affecter et suivre toutes les livraisons de la plateforme." : "Livraisons qui vous sont affectées en tant que transporteur." }}
        </p>
      </div>
      <div v-if="isAdmin" class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle livraison" }}
        </button>
      </div>
    </div>

    <div class="ie-kpi-grid" style="margin-bottom: 20px;">
      <div class="ie-card ie-kpi"><b>{{ stats.total }}</b><span>Total livraisons</span></div>
      <div class="ie-card ie-kpi"><b>{{ stats.pending }}</b><span>En attente</span></div>
      <div class="ie-card ie-kpi"><b>{{ stats.inProgress }}</b><span>En cours</span></div>
      <div class="ie-card ie-kpi"><b>{{ stats.delivered }}</b><span>Livrées</span></div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Adresse de départ</label>
            <input v-model="form.pickup_address" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Adresse de destination</label>
            <input v-model="form.destination_address" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Nom du destinataire</label>
            <input v-model="form.recipient_name" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Téléphone du destinataire</label>
            <input v-model="form.recipient_phone" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Type de livraison</label>
            <select v-model="form.delivery_type" class="ie-select">
              <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Priorité</label>
            <select v-model="form.priority" class="ie-select">
              <option value="normal">Normale</option>
              <option value="urgent">Urgente</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Zone tarifaire</label>
            <select v-model="form.zone" class="ie-select">
              <option value="">—</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Distance (km)</label>
            <input v-model.number="form.distance_km" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Montant (XAF)</label>
            <input v-model.number="form.amount" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Mode de paiement</label>
            <select v-model="form.payment_mode" class="ie-select">
              <option value="on_delivery">À la livraison</option>
              <option value="before">Avant livraison</option>
            </select>
          </div>
        </div>

        <label class="ie-label" style="margin-top: 14px;">Colis</label>
        <div v-for="(p, i) in form.parcels" :key="i" class="ie-form-row" style="margin-top: 6px; align-items: end;">
          <div>
            <input v-model="p.description" class="ie-input" placeholder="Description du colis" />
          </div>
          <div style="display: flex; gap: 8px;">
            <input v-model.number="p.quantity" type="number" min="1" class="ie-input" placeholder="Qté" style="width: 80px;" />
            <input v-model.number="p.weight_kg" type="number" min="0" class="ie-input" placeholder="Poids (kg)" style="width: 110px;" />
            <button type="button" class="ie-btn ie-btn-danger ie-btn-sm" @click="removeParcelRow(i)"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>
        <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 8px;" @click="addParcelRow">
          <i class="fa-solid fa-plus"></i> Ajouter un colis
        </button>

        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Création…" : "Créer la livraison" }}
        </button>
      </form>
    </div>

    <div class="ie-search-bar" style="margin-bottom: 14px;">
      <div class="ie-search-input">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="search" placeholder="Référence, code de suivi, téléphone, destination..." />
      </div>
      <select v-model="statusFilter" class="ie-select ie-search-filter">
        <option value="">Tous les statuts</option>
        <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="filteredDeliveries.length">
        <table class="ie-table">
          <thead>
            <tr><th>Référence</th><th>Destination</th><th>Type</th><th>Transporteur</th><th>Montant</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="d in filteredDeliveries" :key="d.id">
              <td><strong>{{ d.reference }}</strong><br /><span style="font-size: 11px; color: var(--ie-muted);">{{ d.tracking_code }}</span></td>
              <td>{{ d.destination_address }}</td>
              <td>{{ TYPES.find((t) => t.value === d.delivery_type)?.label }}</td>
              <td>{{ d.carrier_name || "—" }}</td>
              <td class="ie-num">{{ Number(d.amount).toLocaleString('fr-FR') }} XAF</td>
              <td><span class="ie-badge" :class="STATUS_BADGE[d.status]">{{ d.status_display }}</span></td>
              <td class="ie-table-actions">
                <router-link :to="{ name: 'delivery-detail', params: { id: d.id } }" class="ie-btn ie-btn-ghost ie-btn-sm">
                  <i class="fa-solid fa-eye"></i> Détail
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-box-open" text="Aucune livraison pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.ie-kpi b { font-size: 24px; color: var(--ie-navy); }
.ie-kpi span { font-size: 12px; color: var(--ie-muted); }
</style>
