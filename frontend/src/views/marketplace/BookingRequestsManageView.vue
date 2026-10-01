<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import KpiCard from "../../components/KpiCard.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";

const STATUS_META = {
  pending: { label: "En attente de réponse", badge: "ie-badge-neutral" },
  quoted: { label: "Devis envoyé", badge: "ie-badge-neutral" },
  modification_requested: { label: "Modification demandée", badge: "ie-badge-warning" },
  accepted: { label: "Devis accepté", badge: "ie-badge-warning" },
  confirmed: { label: "Confirmée (payée)", badge: "ie-badge-success" },
  completed: { label: "Prestation réalisée", badge: "ie-badge-success" },
  declined: { label: "Refusée", badge: "ie-badge-danger" },
  cancelled: { label: "Annulée", badge: "ie-badge-danger" },
  contacted: { label: "Mise en relation effectuée (suivi manuel)", badge: "ie-badge-neutral" },
};
const STATUS_OPTIONS = [
  { value: "pending", label: "En attente de réponse" },
  { value: "quoted", label: "Devis envoyé" },
  { value: "modification_requested", label: "Modification demandée" },
  { value: "accepted", label: "Devis accepté" },
  { value: "confirmed", label: "Confirmée (payée)" },
  { value: "completed", label: "Prestation réalisée" },
  { value: "declined", label: "Refusée" },
  { value: "cancelled", label: "Annulée" },
  { value: "contacted", label: "Mise en relation effectuée (suivi manuel)" },
];
const OPEN_STATUSES = new Set(["pending", "quoted", "modification_requested", "accepted"]);

const requests = ref([]);
const loading = ref(true);
const statusFilter = ref("");
const search = ref("");
const savingId = ref(null);
const notesDraft = reactive({});

const filteredRequests = computed(() => {
  let result = requests.value;
  if (statusFilter.value) result = result.filter((r) => r.status === statusFilter.value);
  const query = search.value.trim().toLowerCase();
  if (query) {
    result = result.filter((r) =>
      (r.business_name || "").toLowerCase().includes(query) || (r.client_name || "").toLowerCase().includes(query)
    );
  }
  return result;
});

const stats = computed(() => {
  const openCount = requests.value.filter((r) => OPEN_STATUSES.has(r.status)).length;
  const confirmedCount = requests.value.filter((r) => r.status === "confirmed" || r.status === "completed").length;
  const confirmedRevenue = requests.value
    .filter((r) => (r.status === "confirmed" || r.status === "completed") && r.latest_quote)
    .reduce((sum, r) => sum + Number(r.latest_quote.total_amount || 0), 0);
  return { total: requests.value.length, open: openCount, confirmed: confirmedCount, revenue: confirmedRevenue };
});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/booking-requests/");
    requests.value = data.results || data;
    requests.value.forEach((r) => { notesDraft[r.id] = r.admin_notes || ""; });
  } finally {
    loading.value = false;
  }
}

async function updateStatus(request, status) {
  savingId.value = request.id;
  try {
    const { data } = await api.patch(`/marketplace/booking-requests/${request.id}/`, { status });
    Object.assign(request, data);
  } finally {
    savingId.value = null;
  }
}

async function saveNotes(request) {
  savingId.value = request.id;
  try {
    const { data } = await api.patch(`/marketplace/booking-requests/${request.id}/`, { admin_notes: notesDraft[request.id] });
    Object.assign(request, data);
  } finally {
    savingId.value = null;
  }
}

async function downloadPdf(quote) {
  const { data } = await api.get(`/marketplace/quotes/${quote.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `devis-${String(quote.id).padStart(6, "0")}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-clipboard-list" style="color: var(--ie-red); margin-right: 8px;"></i>Demandes de réservation</h1>
        <p class="ie-page-subtitle">
          Un client réserve toujours via la plateforme, jamais directement auprès du prestataire : à vous de suivre la négociation et de faire évoluer le statut ci-dessous si nécessaire.
        </p>
      </div>
    </div>

    <div class="ie-kpi-grid">
      <KpiCard label="Demandes au total" :value="stats.total" :loading="loading" icon="fa-solid fa-clipboard-list" tone="navy" />
      <KpiCard label="En cours de négociation" :value="stats.open" :loading="loading" icon="fa-solid fa-hourglass-half" tone="warning" />
      <KpiCard label="Confirmées" :value="stats.confirmed" :loading="loading" icon="fa-solid fa-circle-check" tone="success" />
      <KpiCard label="CA confirmé (XAF)" :value="stats.revenue.toLocaleString('fr-FR')" :loading="loading" icon="fa-solid fa-sack-dollar" tone="red" />
    </div>

    <div class="ie-brm-toolbar">
      <div class="ie-search-input">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="search" placeholder="Rechercher un prestataire ou un client..." />
      </div>
      <select v-model="statusFilter" class="ie-select">
        <option value="">Tous les statuts</option>
        <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div v-else-if="filteredRequests.length" class="ie-brm-list">
        <article v-for="r in filteredRequests" :key="r.id" class="ie-brm-row">
          <header class="ie-brm-row-head">
            <div>
              <strong class="ie-brm-provider">{{ r.business_name }}</strong>
              <span v-if="r.service_name" class="ie-brm-service"> — {{ r.service_name }}</span>
              <p v-if="r.event_type" class="ie-brm-event-type">{{ r.event_type }}</p>
            </div>
            <div class="ie-brm-head-right">
              <span class="ie-badge" :class="STATUS_META[r.status]?.badge">{{ STATUS_META[r.status]?.label || r.status }}</span>
              <span class="ie-brm-date">Reçue le {{ new Date(r.created_at).toLocaleDateString('fr-FR') }}</span>
            </div>
          </header>

          <div class="ie-brm-meta">
            <span><i class="fa-solid fa-user"></i> {{ r.client_name }}</span>
            <span v-if="r.client_phone"><i class="fa-solid fa-phone"></i> {{ r.client_phone }}</span>
            <span v-if="r.contact_phone && r.contact_phone !== r.client_phone"><i class="fa-solid fa-mobile-screen"></i> {{ r.contact_phone }}</span>
            <span v-if="r.client_email"><i class="fa-solid fa-envelope"></i> {{ r.client_email }}</span>
            <span v-if="r.event_date"><i class="fa-solid fa-calendar-day"></i> {{ new Date(r.event_date).toLocaleDateString('fr-FR') }}</span>
            <span v-if="r.city"><i class="fa-solid fa-location-dot"></i> {{ r.city }}</span>
            <span v-if="r.guest_count"><i class="fa-solid fa-people-group"></i> {{ r.guest_count }} invités</span>
          </div>

          <p v-if="r.message" class="ie-brm-message">{{ r.message }}</p>

          <div v-if="r.requested_equipment?.length" class="ie-brm-equipment">
            <strong><i class="fa-solid fa-boxes-stacked"></i> Matériel souhaité</strong>
            <span v-for="item in r.requested_equipment" :key="item.id">{{ item.equipment_name }} × {{ item.quantity }}</span>
          </div>

          <div v-if="r.latest_quote" class="ie-brm-quote">
            <div>
              <i class="fa-solid fa-file-invoice"></i>
              <strong>{{ Number(r.latest_quote.total_amount).toLocaleString('fr-FR') }} {{ r.latest_quote.currency }}</strong>
              <span class="ie-field-hint">{{ r.latest_quote.status_label }}</span>
            </div>
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="downloadPdf(r.latest_quote)">
              <i class="fa-solid fa-download"></i> Télécharger le PDF
            </button>
          </div>

          <div class="ie-brm-admin">
            <span class="ie-brm-admin-label"><i class="fa-solid fa-user-shield"></i> Gestion interne</span>
            <div class="ie-brm-admin-row">
              <select
                class="ie-select" :value="r.status" :disabled="savingId === r.id"
                @change="updateStatus(r, $event.target.value)"
              >
                <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
              <input v-model="notesDraft[r.id]" class="ie-input" placeholder="Note interne — jamais visible du client ni du prestataire" />
              <button class="ie-btn ie-btn-ghost ie-btn-sm" :disabled="savingId === r.id" @click="saveNotes(r)">
                <i class="fa-solid fa-floppy-disk"></i> Enregistrer
              </button>
            </div>
          </div>
        </article>
      </div>
      <EmptyState v-else icon="fa-solid fa-clipboard-list" text="Aucune demande de réservation pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }
@media (max-width: 900px) { .ie-kpi-grid { grid-template-columns: repeat(2, 1fr); } }

.ie-brm-toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.ie-search-input {
  display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid var(--ie-line);
  border-radius: 10px; padding: 0 12px; flex: 1; min-width: 240px;
}
.ie-search-input i { color: var(--ie-muted); }
.ie-search-input input { border: 0; outline: none; flex: 1; font-size: 13px; padding: 10px 0; background: transparent; }

.ie-brm-list { display: flex; flex-direction: column; gap: 14px; padding: 16px; }
.ie-brm-row { background: #fff; border: 1px solid var(--ie-line); border-radius: 12px; padding: 16px 18px; }

.ie-brm-row-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; flex-wrap: wrap; }
.ie-brm-provider { font-size: 15px; color: var(--ie-navy); }
.ie-brm-service { color: var(--ie-muted); font-size: 12.5px; }
.ie-brm-event-type { margin: 2px 0 0; font-size: 12px; color: var(--ie-red); font-weight: 700; }
.ie-brm-head-right { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.ie-brm-date { font-size: 11px; color: var(--ie-muted); }

.ie-brm-meta {
  display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 10px; padding: 10px 0; border-top: 1px solid var(--ie-line);
  font-size: 12.5px; color: var(--ie-ink);
}
.ie-brm-meta i { color: var(--ie-muted); margin-right: 5px; width: 13px; }

.ie-brm-message { margin: 10px 0 0; font-size: 12.5px; color: var(--ie-muted); line-height: 1.55; max-width: 640px; }

.ie-brm-equipment {
  margin-top: 10px; padding: 8px 12px; background: #FAFBFC; border: 1px solid var(--ie-line); border-radius: 8px;
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap; font-size: 12px;
}
.ie-brm-equipment strong { color: var(--ie-navy); font-size: 11.5px; }
.ie-brm-equipment strong i { color: var(--ie-red); margin-right: 5px; }
.ie-brm-equipment span { color: var(--ie-ink); }

.ie-brm-quote {
  margin-top: 12px; padding: 10px 14px; background: var(--ie-navy-soft); border-radius: 8px;
  display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;
}
.ie-brm-quote i.fa-file-invoice { color: var(--ie-red); margin-right: 6px; }
.ie-brm-quote strong { color: var(--ie-navy); margin-right: 8px; }
.ie-brm-quote .ie-field-hint { font-size: 11.5px; }

.ie-brm-admin { margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--ie-line); }
.ie-brm-admin-label { display: block; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ie-muted); margin-bottom: 8px; }
.ie-brm-admin-label i { margin-right: 5px; }
.ie-brm-admin-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.ie-brm-admin-row .ie-select { max-width: 220px; }
.ie-brm-admin-row .ie-input { flex: 1; min-width: 220px; }
</style>
