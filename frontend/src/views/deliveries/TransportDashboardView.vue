<script setup>
import { computed, onMounted, ref } from "vue";
import ChartCanvas from "../../components/ChartCanvas.vue";
import KpiCard from "../../components/KpiCard.vue";
import api from "../../services/api";

const STATUS_LABELS = {
  created: "Créée", pending: "En attente", confirmed: "Confirmée", to_prepare: "À préparer", ready: "Prête",
  carrier_assigned: "Affectée", collected: "Collectée", in_transit: "En transit", arrived: "Arrivée",
  delivering: "En livraison", delivered: "Livrée", failed: "Échec", postponed: "Reportée",
  cancelled: "Annulée", returning: "Retour", returned: "Retournée",
};

const loading = ref(true);
const stats = ref(null);

async function loadStats() {
  loading.value = true;
  try {
    const { data } = await api.get("/deliveries/stats/");
    stats.value = data;
  } finally {
    loading.value = false;
  }
}

const byDayChart = computed(() => {
  if (!stats.value) return { labels: [], datasets: [] };
  return {
    labels: stats.value.by_day.map((d) => new Date(d.date).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" })),
    datasets: [{ label: "Livraisons créées", data: stats.value.by_day.map((d) => d.count), backgroundColor: "#C0272D", borderRadius: 6, maxBarThickness: 34 }],
  };
});

const byStatusChart = computed(() => {
  if (!stats.value) return { labels: [], datasets: [] };
  const entries = stats.value.by_status;
  return {
    labels: entries.map((e) => STATUS_LABELS[e.status] || e.status),
    datasets: [{
      data: entries.map((e) => e.count),
      backgroundColor: ["#DDE1E5", "#39495B", "#C0272D", "#1E7B4D", "#A66A00", "#8E44AD", "#2980B9", "#16A085", "#E67E22", "#7F8C8D", "#D35400", "#C0392B", "#2C3E50", "#27AE60", "#F39C12", "#95A5A6"],
      borderWidth: 0,
    }],
  };
});

const chartOptionsBar = {
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true, grid: { color: "#eef0f2" } }, x: { grid: { display: false } } },
};
const chartOptionsDoughnut = { plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } } };

onMounted(loadStats);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-truck" style="color: var(--ie-red); margin-right: 8px;"></i>Tableau de bord transport</h1>

    <div class="ie-kpi-grid">
      <KpiCard label="Total livraisons" :value="stats?.total ?? 0" :loading="loading" />
      <KpiCard label="En attente" :value="stats?.pending ?? 0" :loading="loading" />
      <KpiCard label="En cours" :value="stats?.in_progress ?? 0" :loading="loading" />
      <KpiCard label="Livrées" :value="stats?.completed ?? 0" :loading="loading" />
      <KpiCard label="Aujourd'hui" :value="stats?.today ?? 0" :loading="loading" />
      <KpiCard label="Programmées" :value="stats?.scheduled ?? 0" :loading="loading" />
      <KpiCard label="Échecs" :value="stats?.failed ?? 0" :loading="loading" />
      <KpiCard label="Annulées" :value="stats?.cancelled ?? 0" :loading="loading" />
      <KpiCard label="Chiffre d'affaires livré (XAF)" :value="(stats?.revenue ?? 0).toLocaleString('fr-FR')" :loading="loading" />
      <KpiCard label="En attente de paiement (XAF)" :value="(stats?.outstanding ?? 0).toLocaleString('fr-FR')" :loading="loading" />
      <KpiCard label="Transporteurs disponibles" :value="stats?.active_carriers ?? 0" :loading="loading" />
      <KpiCard label="Chauffeurs disponibles" :value="stats?.available_drivers ?? 0" :loading="loading" />
    </div>

    <div class="ie-dashboard-grid">
      <div class="ie-card" style="padding: 20px;">
        <h2 style="margin-bottom: 14px;">Livraisons créées — 7 derniers jours</h2>
        <ChartCanvas type="bar" :data="byDayChart" :options="chartOptionsBar" />
      </div>
      <div class="ie-card" style="padding: 20px;">
        <h2 style="margin-bottom: 14px;">Répartition par statut</h2>
        <ChartCanvas type="doughnut" :data="byStatusChart" :options="chartOptionsDoughnut" />
      </div>
    </div>
  </div>
</template>
