<script setup>
import { computed, onMounted, ref } from "vue";
import ChartCanvas from "../../components/ChartCanvas.vue";
import HorizontalBarList from "../../components/HorizontalBarList.vue";
import api from "../../services/api";

const payments = ref([]);
const loading = ref(true);

const PROVIDER_LABELS = { paypal: "PayPal", mobile_money: "Mobile Money", freemopay: "FreemoPay", kob: "KOB", demo: "Démonstration" };

const kpis = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  const completed = payments.value.filter((p) => p.status === "completed");
  const today_completed = completed.filter((p) => p.completed_at && p.completed_at.slice(0, 10) === today);
  return {
    totalAmount: completed.reduce((sum, p) => sum + Number(p.amount), 0),
    todayAmount: today_completed.reduce((sum, p) => sum + Number(p.amount), 0),
    pendingCount: payments.value.filter((p) => p.status === "pending").length,
    failedCount: payments.value.filter((p) => p.status === "failed").length,
  };
});

const providerBars = computed(() => {
  const totals = {};
  payments.value
    .filter((p) => p.status === "completed")
    .forEach((p) => {
      totals[p.provider] = (totals[p.provider] || 0) + Number(p.amount);
    });
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .map(([provider, amount]) => ({
      label: PROVIDER_LABELS[provider] || provider,
      value: amount,
      display: `${amount.toLocaleString("fr-FR")} XAF`,
    }));
});

const last14DaysChart = computed(() => {
  const days = [];
  for (let i = 13; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  const totals = days.map((day) =>
    payments.value
      .filter((p) => p.status === "completed" && p.completed_at?.slice(0, 10) === day)
      .reduce((sum, p) => sum + Number(p.amount), 0)
  );
  return {
    labels: days.map((d) => new Date(d).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })),
    datasets: [
      {
        label: "Montant encaissé (XAF)",
        data: totals,
        borderColor: "#C0272D",
        backgroundColor: "rgba(192,39,45,0.12)",
        tension: 0.35,
        fill: true,
        pointRadius: 2,
      },
    ],
  };
});

const chartOptions = {
  plugins: { legend: { display: false } },
  scales: {
    y: { beginAtZero: true, grid: { color: "#eef0f2" }, ticks: { callback: (v) => v.toLocaleString("fr-FR") } },
    x: { grid: { display: false } },
  },
};

async function loadPayments() {
  loading.value = true;
  try {
    const { data } = await api.get("/payments/");
    payments.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadPayments);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-chart-pie" style="color: var(--ie-red); margin-right: 8px;"></i>Dashboard paiements</h1>

    <div class="ie-kpi-grid" style="margin-top: 20px;">
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ kpis.totalAmount.toLocaleString('fr-FR') }} XAF</b><span>Total encaissé</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ kpis.todayAmount.toLocaleString('fr-FR') }} XAF</b><span>Encaissé aujourd'hui</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ kpis.pendingCount }}</b><span>Paiements en attente</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num" style="color: var(--ie-red);">{{ kpis.failedCount }}</b><span>Paiements échoués</span></div>
    </div>

    <div class="ie-card" style="margin-top: 20px; padding: 20px;">
      <h2 style="margin-bottom: 14px;">Encaissements — 14 derniers jours</h2>
      <ChartCanvas type="line" :data="last14DaysChart" :options="chartOptions" />
    </div>

    <div class="ie-card" style="margin-top: 20px; padding: 20px;">
      <h2 style="margin-bottom: 18px;">Répartition par passerelle</h2>
      <HorizontalBarList :items="providerBars" />
    </div>
  </div>
</template>

<style scoped>
.ie-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.ie-kpi-num { display: block; font-size: 20px; color: var(--ie-navy); }
@media (max-width: 900px) { .ie-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
