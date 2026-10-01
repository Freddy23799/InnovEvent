<script setup>
import { onMounted, ref } from "vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const dateFrom = ref("");
const dateTo = ref("");
const statusFilter = ref("");
const exporting = ref(false);
const stats = ref(null);
const loading = ref(true);

const STATUSES = [
  { value: "", label: "Tous les statuts" },
  { value: "delivered", label: "Livrée" }, { value: "cancelled", label: "Annulée" }, { value: "failed", label: "Échec" },
  { value: "returned", label: "Retournée" }, { value: "pending", label: "En attente" },
];

async function loadStats() {
  loading.value = true;
  try {
    const { data } = await api.get("/deliveries/stats/");
    stats.value = data;
  } finally {
    loading.value = false;
  }
}

function buildParams(type) {
  const params = { type };
  if (dateFrom.value) params.date_from = dateFrom.value;
  if (dateTo.value) params.date_to = dateTo.value;
  if (statusFilter.value) params.status = statusFilter.value;
  return params;
}

async function exportFile(type) {
  exporting.value = true;
  try {
    const res = await api.get("/deliveries/export/", { params: buildParams(type), responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    if (type === "csv") {
      a.download = "rapport-transport.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } else {
      window.open(url, "_blank");
    }
    toast.success(type === "csv" ? "Export CSV téléchargé." : "Rapport PDF généré.");
  } catch (e) {
    toast.error("Impossible de générer l'export.");
  } finally {
    exporting.value = false;
  }
}

onMounted(loadStats);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-chart-column" style="color: var(--ie-red); margin-right: 8px;"></i>Rapports transport</h1>
    <p class="ie-page-subtitle">Filtrez par période et statut, puis exportez au format CSV ou PDF.</p>

    <div class="ie-card ie-card-body" style="margin-top: 16px;">
      <div class="ie-form-row">
        <div>
          <label class="ie-label">Du</label>
          <input v-model="dateFrom" type="date" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Au</label>
          <input v-model="dateTo" type="date" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Statut</label>
          <select v-model="statusFilter" class="ie-select">
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
      </div>
      <div style="display: flex; gap: 10px; margin-top: 18px;">
        <button class="ie-btn ie-btn-secondary" :disabled="exporting" @click="exportFile('csv')">
          <i class="fa-solid fa-file-csv"></i> Exporter en CSV
        </button>
        <button class="ie-btn ie-btn-primary" :disabled="exporting" @click="exportFile('pdf')">
          <i class="fa-solid fa-file-pdf"></i> Générer le rapport PDF
        </button>
      </div>
    </div>

    <div v-if="!loading && stats" class="ie-card ie-section" style="padding: 20px; margin-top: 20px;">
      <h2 style="margin-bottom: 14px;">Aperçu global</h2>
      <div class="ie-kpi-grid">
        <div class="ie-card ie-kpi"><b>{{ stats.total }}</b><span>Total livraisons</span></div>
        <div class="ie-card ie-kpi"><b>{{ stats.completed }}</b><span>Livrées</span></div>
        <div class="ie-card ie-kpi"><b>{{ stats.cancelled + stats.failed }}</b><span>Annulées / échouées</span></div>
        <div class="ie-card ie-kpi"><b>{{ Number(stats.revenue).toLocaleString('fr-FR') }} XAF</b><span>Chiffre d'affaires livré</span></div>
        <div class="ie-card ie-kpi"><b>{{ Number(stats.outstanding).toLocaleString('fr-FR') }} XAF</b><span>En attente de paiement</span></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.ie-kpi b { font-size: 20px; color: var(--ie-navy); }
.ie-kpi span { font-size: 12px; color: var(--ie-muted); }
</style>
