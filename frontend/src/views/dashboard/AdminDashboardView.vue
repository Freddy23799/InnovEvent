<script setup>
import { computed, onMounted, ref } from "vue";
import ChartCanvas from "../../components/ChartCanvas.vue";
import api from "../../services/api";

const loading = ref(true);
const error = ref("");
const period = ref(30);
const data = ref(null);
const numberFormat = new Intl.NumberFormat("fr-FR");
const dateFormat = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" });
const dateTimeFormat = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

async function loadDashboard() {
  loading.value = true;
  error.value = "";
  try {
    const response = await api.get("/auth/admin-dashboard/", { params: { days: period.value } });
    data.value = response.data;
  } catch {
    error.value = "Les statistiques n’ont pas pu être chargées. Vérifiez votre connexion puis réessayez.";
  } finally {
    loading.value = false;
  }
}

function formatMoney(amount) {
  return `${numberFormat.format(Math.round(Number(amount || 0)))} F`;
}
function formatDate(value) {
  return value ? dateFormat.format(new Date(value)) : "—";
}
function formatDateTime(value) {
  return value ? dateTimeFormat.format(new Date(value)) : "—";
}

const revenueChart = computed(() => ({
  labels: (data.value?.finance.daily || []).map((item) => formatDate(item.date)),
  datasets: [{
    label: "Revenus encaissés",
    data: (data.value?.finance.daily || []).map((item) => item.amount),
    borderColor: "#c0272d",
    backgroundColor: "rgba(192, 39, 45, .12)",
    fill: true,
    tension: 0.35,
    pointRadius: period.value <= 30 ? 3 : 0,
    pointHoverRadius: 5,
  }],
}));
const usersChart = computed(() => ({
  labels: (data.value?.users.daily || []).map((item) => formatDate(item.date)),
  datasets: [{
    label: "Nouveaux comptes",
    data: (data.value?.users.daily || []).map((item) => item.total),
    backgroundColor: "#24364b",
    borderRadius: 5,
    maxBarThickness: 18,
  }],
}));
const rolesChart = computed(() => ({
  labels: (data.value?.users.by_role || []).map((item) => item.label),
  datasets: [{
    data: (data.value?.users.by_role || []).map((item) => item.total),
    backgroundColor: ["#c0272d", "#344b65", "#e3a13b", "#51a47b", "#8c78c4", "#62a7b7"],
    borderWidth: 0,
    hoverOffset: 5,
  }],
}));
const totalRevenue = computed(() => formatMoney(data.value?.finance.revenue_total_xaf));
const periodRevenue = computed(() => formatMoney(data.value?.finance.revenue_period_xaf));
const roleTotal = computed(() => (data.value?.users.by_role || []).reduce((sum, item) => sum + item.total, 0));
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
  scales: {
    x: { grid: { display: false }, ticks: { maxTicksLimit: 8, color: "#8390a0", font: { size: 10 } } },
    y: { beginAtZero: true, grid: { color: "#edf0f3" }, ticks: { color: "#8390a0", callback: (value) => numberFormat.format(value) } },
  },
};
const roleChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: "72%",
  plugins: { legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "circle", padding: 16, color: "#596779", font: { size: 11 } } } },
};

onMounted(loadDashboard);
</script>

<template>
  <main class="admin-dashboard">
    <header class="dashboard-heading">
      <div>
        <span class="eyebrow"><i class="fa-solid fa-chart-line"></i> PILOTAGE DE LA PLATEFORME</span>
        <h1>Vue d’ensemble</h1>
        <p>Suivez l’activité, les utilisateurs et les revenus d’InnovEvent.</p>
      </div>
      <div class="heading-actions">
        <label class="period-picker">
          <i class="fa-regular fa-calendar"></i>
          <select v-model.number="period" @change="loadDashboard">
            <option :value="7">7 derniers jours</option>
            <option :value="30">30 derniers jours</option>
            <option :value="90">90 derniers jours</option>
          </select>
        </label>
        <button class="refresh-button" :disabled="loading" aria-label="Actualiser les statistiques" @click="loadDashboard">
          <i class="fa-solid fa-rotate" :class="{ spinning: loading }"></i><span>Actualiser</span>
        </button>
      </div>
    </header>

    <div v-if="error" class="dashboard-error" role="alert">
      <i class="fa-solid fa-triangle-exclamation"></i><span>{{ error }}</span>
      <button @click="loadDashboard">Réessayer</button>
    </div>

    <section class="kpi-grid" aria-label="Indicateurs clés">
      <article class="metric-card metric-users">
        <div class="metric-top"><span class="metric-icon"><i class="fa-solid fa-users"></i></span><span class="metric-caption">COMPTES ACTIFS</span></div>
        <strong>{{ loading && !data ? "—" : numberFormat.format(data?.users.active || 0) }}</strong>
        <small>{{ numberFormat.format(data?.users.new_period || 0) }} nouveaux sur {{ period }} jours</small>
      </article>
      <article class="metric-card metric-revenue">
        <div class="metric-top"><span class="metric-icon"><i class="fa-solid fa-sack-dollar"></i></span><span class="metric-caption">REVENUS · PÉRIODE</span></div>
        <strong>{{ loading && !data ? "—" : periodRevenue }}</strong>
        <small>{{ totalRevenue }} encaissés au total</small>
      </article>
      <article class="metric-card metric-subscriptions">
        <div class="metric-top"><span class="metric-icon"><i class="fa-solid fa-crown"></i></span><span class="metric-caption">ABONNEMENTS ACTIFS</span></div>
        <strong>{{ loading && !data ? "—" : numberFormat.format(data?.activity.active_subscriptions || 0) }}</strong>
        <small>Accès Marketplace en cours</small>
      </article>
      <article class="metric-card metric-online">
        <div class="metric-top"><span class="metric-icon"><i class="fa-solid fa-signal"></i></span><span class="metric-caption">EN LIGNE</span></div>
        <strong>{{ loading && !data ? "—" : numberFormat.format(data?.users.online || 0) }}</strong>
        <small>{{ numberFormat.format(data?.users.total || 0) }} comptes enregistrés</small>
      </article>
    </section>

    <section class="chart-grid">
      <article class="panel revenue-panel">
        <div class="panel-heading">
          <div><span class="panel-kicker">FINANCES</span><h2>Revenus encaissés</h2><p>Évolution quotidienne · XAF</p></div>
          <span class="panel-icon red"><i class="fa-solid fa-arrow-trend-up"></i></span>
        </div>
        <div v-if="loading && !data" class="chart-loading">Chargement des données…</div>
        <ChartCanvas v-else type="line" :data="revenueChart" :options="chartOptions" />
      </article>
      <article class="panel users-panel">
        <div class="panel-heading">
          <div><span class="panel-kicker">ACQUISITION</span><h2>Nouveaux utilisateurs</h2><p>Inscriptions quotidiennes</p></div>
          <span class="panel-icon navy"><i class="fa-solid fa-user-plus"></i></span>
        </div>
        <div v-if="loading && !data" class="chart-loading">Chargement des données…</div>
        <ChartCanvas v-else type="bar" :data="usersChart" :options="chartOptions" />
      </article>
    </section>

    <section class="lower-grid">
      <article class="panel role-panel">
        <div class="panel-heading"><div><span class="panel-kicker">COMMUNAUTÉ</span><h2>Utilisateurs par profil</h2><p>{{ numberFormat.format(roleTotal) }} comptes au total</p></div></div>
        <div class="roles-content">
          <div class="role-chart"><ChartCanvas type="doughnut" :data="rolesChart" :options="roleChartOptions" /></div>
          <ul class="role-list">
            <li v-for="role in data?.users.by_role || []" :key="role.role">
              <span>{{ role.label }}</span><strong>{{ numberFormat.format(role.total) }}</strong>
            </li>
          </ul>
        </div>
      </article>
      <article class="panel activity-panel">
        <div class="panel-heading"><div><span class="panel-kicker">ACTIVITÉ</span><h2>La plateforme en chiffres</h2><p>Volumes actuellement suivis</p></div></div>
        <div class="activity-grid">
          <div><span class="activity-icon"><i class="fa-regular fa-calendar-check"></i></span><strong>{{ numberFormat.format(data?.activity.events || 0) }}</strong><small>Événements</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-ticket"></i></span><strong>{{ numberFormat.format(data?.activity.tickets_sold || 0) }}</strong><small>Billets vendus</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-bookmark"></i></span><strong>{{ numberFormat.format(data?.activity.bookings || 0) }}</strong><small>Réservations</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-store"></i></span><strong>{{ numberFormat.format(data?.activity.marketplace_listings || 0) }}</strong><small>Annonces actives</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-clipboard-list"></i></span><strong>{{ numberFormat.format(data?.activity.open_booking_requests || 0) }}</strong><small>Demandes à traiter</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-wand-magic-sparkles"></i></span><strong>{{ numberFormat.format(data?.activity.active_missions || 0) }}</strong><small>Missions talent</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-graduation-cap"></i></span><strong>{{ numberFormat.format(data?.activity.training_enrollments || 0) }}</strong><small>Inscriptions formation</small></div>
          <div><span class="activity-icon"><i class="fa-solid fa-circle-check"></i></span><strong>{{ numberFormat.format(data?.activity.confirmed_bookings || 0) }}</strong><small>Réservations confirmées</small></div>
        </div>
      </article>
    </section>

    <section class="tables-grid">
      <article class="panel table-panel">
        <div class="panel-heading"><div><span class="panel-kicker">TRANSACTIONS</span><h2>Paiements récents</h2></div><span class="table-total">{{ numberFormat.format(data?.finance.pending_payments || 0) }} en attente</span></div>
        <div class="table-scroll">
          <table><thead><tr><th>Utilisateur</th><th>Objet</th><th>Montant</th><th>Statut</th><th>Date</th></tr></thead>
            <tbody><tr v-for="payment in data?.finance.recent || []" :key="payment.id">
              <td><strong>{{ payment.name }}</strong></td><td>{{ payment.purpose.replaceAll("_", " ") }}</td>
              <td class="amount-cell">{{ numberFormat.format(payment.amount) }} {{ payment.currency }}</td>
              <td><span class="status-pill" :class="`status-${payment.status_code}`">{{ payment.status }}</span></td>
              <td>{{ formatDateTime(payment.created_at) }}</td>
            </tr><tr v-if="!loading && !data?.finance.recent?.length"><td colspan="5" class="empty-cell">Aucun paiement enregistré.</td></tr></tbody>
          </table>
        </div>
        <div class="payment-summary"><span><i class="fa-solid fa-circle-check"></i> {{ numberFormat.format(data?.finance.completed_payments || 0) }} paiements réussis</span><span><i class="fa-solid fa-circle-xmark"></i> {{ numberFormat.format(data?.finance.failed_payments || 0) }} échoués</span><span><i class="fa-solid fa-coins"></i> {{ formatMoney(data?.finance.revenue_today_xaf) }} aujourd’hui</span></div>
      </article>
      <article class="panel table-panel new-users-panel">
        <div class="panel-heading"><div><span class="panel-kicker">COMMUNAUTÉ</span><h2>Derniers inscrits</h2></div><span class="table-total">{{ numberFormat.format(data?.users.total || 0) }} au total</span></div>
        <div class="recent-user-list">
          <div v-for="user in data?.users.recent || []" :key="user.id" class="recent-user">
            <span class="user-avatar">{{ user.name.slice(0, 1).toUpperCase() }}</span>
            <span class="recent-user-info"><strong>{{ user.name }}</strong><small>{{ user.email || "Adresse e-mail non renseignée" }}</small></span>
            <span class="recent-user-role">{{ user.role }}</span>
            <time>{{ formatDate(user.joined_at) }}</time>
          </div>
          <p v-if="!loading && !data?.users.recent?.length" class="empty-cell">Aucun utilisateur enregistré.</p>
        </div>
      </article>
    </section>
    <p class="data-footnote" v-if="data?.generated_at">Données actualisées le {{ formatDateTime(data.generated_at) }} · Revenus comptés uniquement sur les paiements confirmés en XAF.</p>
  </main>
</template>

<style scoped>
.admin-dashboard { --dash-ink: #192536; --dash-muted: #778496; --dash-line: #e8edf2; --dash-surface: #fff; color: var(--dash-ink); padding-bottom: 34px; }
.dashboard-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-bottom: 25px; }
.eyebrow, .panel-kicker { display: block; color: #9a6370; font-size: 10px; font-weight: 800; letter-spacing: .13em; }
.eyebrow { margin-bottom: 8px; }
.eyebrow i { margin-right: 6px; }
.dashboard-heading h1 { color: var(--dash-ink); font-size: clamp(25px, 3vw, 34px); font-weight: 750; letter-spacing: -.04em; margin: 0; }
.dashboard-heading p { color: var(--dash-muted); margin: 6px 0 0; font-size: 14px; }
.heading-actions { display: flex; align-items: center; gap: 9px; }
.period-picker, .refresh-button { height: 41px; display: inline-flex; align-items: center; gap: 9px; border: 1px solid var(--dash-line); background: #fff; border-radius: 10px; padding: 0 12px; color: #536176; font-size: 12px; }
.period-picker select { color: inherit; border: 0; outline: 0; background: transparent; font: inherit; cursor: pointer; }
.refresh-button { cursor: pointer; font-weight: 650; }.refresh-button:disabled { opacity: .65; cursor: wait; }
.spinning { animation: spin 1s linear infinite; }@keyframes spin { to { transform: rotate(360deg); } }
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.metric-card, .panel { background: var(--dash-surface); border: 1px solid var(--dash-line); border-radius: 15px; box-shadow: 0 5px 20px rgba(25, 37, 54, .035); }
.metric-card { min-width: 0; padding: 18px 19px; }
.metric-top { display: flex; align-items: center; gap: 10px; }
.metric-icon, .panel-icon, .activity-icon { width: 35px; height: 35px; flex: 0 0 35px; display: grid; place-items: center; border-radius: 10px; background: #f2f4f7; color: #53657c; }
.metric-users .metric-icon { background: #edf3fa; color: #3c648c; }.metric-revenue .metric-icon, .panel-icon.red { background: #faeded; color: #b52d38; }.metric-subscriptions .metric-icon { background: #fbf4e5; color: #ad7a1f; }.metric-online .metric-icon { background: #eaf5ee; color: #388258; }.panel-icon.navy { background: #edf2f7; color: #405d7a; }
.metric-caption { color: #748195; font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.metric-card > strong { display: block; margin-top: 16px; color: var(--dash-ink); font-size: clamp(22px, 2.2vw, 29px); line-height: 1.15; letter-spacing: -.035em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric-card > small { display: block; margin-top: 6px; color: #8994a3; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chart-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 15px; margin-top: 15px; }
.lower-grid { display: grid; grid-template-columns: .9fr 1.35fr; gap: 15px; margin-top: 15px; }
.tables-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 15px; margin-top: 15px; }
.panel { padding: 19px; min-width: 0; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.panel-heading h2 { margin: 5px 0 0; color: var(--dash-ink); font-size: 15px; font-weight: 720; letter-spacing: -.015em; }
.panel-heading p { margin: 4px 0 0; color: #8994a3; font-size: 11px; }
.panel-icon { width: 33px; height: 33px; flex-basis: 33px; }
.chart-loading { height: 280px; display: grid; place-items: center; color: #96a1ae; font-size: 13px; }
.revenue-panel :deep(.ie-chart-wrap), .users-panel :deep(.ie-chart-wrap) { height: 245px; }
.roles-content { display: grid; grid-template-columns: minmax(125px, .9fr) 1fr; gap: 16px; align-items: center; }
.role-chart :deep(.ie-chart-wrap) { height: 190px; }
.role-list { list-style: none; padding: 0; margin: 0; }
.role-list li { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f2f5; color: #6b7788; font-size: 11px; }
.role-list li:last-child { border-bottom: 0; }.role-list strong { color: var(--dash-ink); font-variant-numeric: tabular-nums; }
.activity-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.activity-grid > div { min-width: 0; display: grid; justify-items: start; gap: 7px; padding: 12px 10px; border-radius: 10px; background: #f8f9fb; }
.activity-icon { width: 28px; height: 28px; flex-basis: 28px; border-radius: 8px; color: #667c96; font-size: 11px; background: #edf1f5; }
.activity-grid strong { color: var(--dash-ink); font-size: 18px; line-height: 1; }.activity-grid small { color: #8793a2; font-size: 10px; line-height: 1.3; }
.table-panel { padding: 0; overflow: hidden; }.table-panel .panel-heading { padding: 18px 19px 0; }
.table-total { color: #7e8a99; font-size: 10px; white-space: nowrap; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; text-align: left; white-space: nowrap; }
th { padding: 10px 14px; color: #8994a2; background: #fafbfc; font-size: 9px; letter-spacing: .06em; text-transform: uppercase; font-weight: 750; }
td { padding: 12px 14px; border-top: 1px solid #eff1f4; color: #6d7989; font-size: 10px; }
td strong { color: #344154; font-weight: 650; }.amount-cell { color: #25374c; font-weight: 700; }
.status-pill { display: inline-block; padding: 4px 8px; border-radius: 20px; background: #f1f3f6; color: #637084; font-size: 9px; }
.status-completed { background: #eaf5ee; color: #388258; }.status-pending { background: #fbf3e5; color: #9b701f; }.status-failed, .status-refunded { background: #faeded; color: #ae3740; }
.payment-summary { display: flex; flex-wrap: wrap; gap: 8px 15px; padding: 12px 15px; border-top: 1px solid #eff1f4; color: #7d8998; font-size: 9px; }
.payment-summary i { margin-right: 3px; color: #8192a5; }
.recent-user-list { padding: 0 18px 8px; }.recent-user { display: grid; grid-template-columns: 32px minmax(0, 1fr) auto auto; align-items: center; gap: 9px; padding: 10px 0; border-top: 1px solid #eff1f4; }
.user-avatar { width: 31px; height: 31px; display: grid; place-items: center; border-radius: 50%; background: #f3e9eb; color: #9b4a55; font-size: 12px; font-weight: 750; }
.recent-user-info { min-width: 0; display: grid; gap: 3px; }.recent-user-info strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #39485c; font-size: 10px; }.recent-user-info small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #96a0ad; font-size: 9px; }
.recent-user-role { padding: 4px 6px; border-radius: 6px; color: #62758c; background: #f1f4f7; font-size: 8px; white-space: nowrap; }.recent-user time { color: #929daa; font-size: 9px; white-space: nowrap; }
.empty-cell { padding: 18px; text-align: center; color: #9aa4b0; }.data-footnote { margin: 12px 2px; color: #909ba9; font-size: 10px; }
.dashboard-error { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; padding: 12px 14px; border: 1px solid #f0d7b0; border-radius: 10px; background: #fff9ed; color: #856321; font-size: 12px; }.dashboard-error button { margin-left: auto; border: 0; background: transparent; color: #725219; font-weight: 700; cursor: pointer; }
@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.chart-grid, .lower-grid, .tables-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .dashboard-heading { align-items: flex-start; flex-direction: column; }.heading-actions { width: 100%; }.period-picker { flex: 1; }.period-picker select { width: 100%; }.refresh-button { justify-content: center; }.kpi-grid { gap: 9px; }.metric-card { padding: 14px 12px; border-radius: 12px; }.metric-top { align-items: flex-start; gap: 7px; flex-direction: column; }.metric-icon { width: 30px; height: 30px; flex-basis: 30px; }.metric-caption { font-size: 8px; }.metric-card > strong { margin-top: 11px; font-size: 21px; }.metric-card > small { white-space: normal; min-height: 26px; font-size: 9px; }.panel { padding: 15px; border-radius: 12px; }.roles-content { grid-template-columns: 1fr; }.role-chart :deep(.ie-chart-wrap) { height: 190px; }.role-list { display: grid; grid-template-columns: 1fr 1fr; column-gap: 14px; }.activity-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.recent-user { grid-template-columns: 31px minmax(0, 1fr) auto; }.recent-user time { grid-column: 2 / 4; }.table-panel .panel-heading { padding: 15px 15px 0; }.payment-summary { padding: 11px 12px; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; } }
</style>
