<script setup>
import { onMounted, ref } from "vue";
import api from "../../services/api";

const data = ref(null);
const loading = ref(true);

function fmt(n) {
  return Number(n || 0).toLocaleString("fr-FR");
}

async function loadData() {
  loading.value = true;
  try {
    const { data: d } = await api.get("/marketplace/analytics/");
    data.value = d;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-chart-line" style="color: var(--ie-red); margin-right: 8px;"></i>Analytics Marketplace</h1>
        <p class="ie-page-subtitle">Vue d'ensemble de l'activité des marketplaces premium.</p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 400px;"></div>

    <template v-else-if="data">
      <div class="ie-analytics-kpis">
        <div class="ie-card ie-kpi"><span class="ie-kpi-value">{{ fmt(data.clients_count) }}</span><span class="ie-kpi-label">Clients</span></div>
        <div class="ie-card ie-kpi"><span class="ie-kpi-value">{{ fmt(data.providers_count) }}</span><span class="ie-kpi-label">Prestataires</span></div>
        <div class="ie-card ie-kpi"><span class="ie-kpi-value">{{ fmt(data.active_subscriptions_count) }}</span><span class="ie-kpi-label">Abonnements actifs</span></div>
        <div class="ie-card ie-kpi"><span class="ie-kpi-value">{{ fmt(data.expired_subscriptions_count) }}</span><span class="ie-kpi-label">Abonnements expirés</span></div>
        <div class="ie-card ie-kpi"><span class="ie-kpi-value">{{ fmt(data.quote_requests_count) }}</span><span class="ie-kpi-label">Demandes de devis</span></div>
        <div class="ie-card ie-kpi"><span class="ie-kpi-value">{{ fmt(data.confirmed_bookings_count) }}</span><span class="ie-kpi-label">Réservations confirmées</span></div>
      </div>

      <div class="ie-card ie-card-body ie-revenue-card">
        <h2 style="margin: 0 0 12px;"><i class="fa-solid fa-sack-dollar" style="color: var(--ie-red);"></i> Chiffre d'affaires</h2>
        <div class="ie-revenue-grid">
          <div><strong>{{ fmt(data.revenue.total) }} {{ data.revenue.currency }}</strong><span>Total</span></div>
          <div><strong>{{ fmt(data.revenue.subscriptions) }} {{ data.revenue.currency }}</strong><span>Abonnements</span></div>
          <div><strong>{{ fmt(data.revenue.quotes) }} {{ data.revenue.currency }}</strong><span>Devis payés</span></div>
          <div><strong>{{ fmt(data.revenue.orders) }} {{ data.revenue.currency }}</strong><span>Marketplace vente</span></div>
        </div>
      </div>

      <div class="ie-card ie-card-body ie-revenue-card">
        <h2 style="margin: 0 0 12px;"><i class="fa-solid fa-percent" style="color: var(--ie-red);"></i> Commission InnovEvent</h2>
        <div class="ie-revenue-grid">
          <div><strong>{{ fmt(data.commission.total_commission) }} {{ data.commission.currency }}</strong><span>Commission perçue</span></div>
          <div><strong>{{ fmt(data.commission.total_provider_payouts) }} {{ data.commission.currency }}</strong><span>Reversé aux prestataires</span></div>
          <div><strong>{{ fmt(data.commission.paid_quotes_count) }}</strong><span>Devis payés</span></div>
        </div>
        <router-link :to="{ name: 'marketplace-commissions-manage' }" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 14px;">
          <i class="fa-solid fa-gear"></i> Régler les taux de commission
        </router-link>
      </div>

      <div class="ie-analytics-grid">
        <div class="ie-card ie-card-body">
          <h2 style="margin: 0 0 12px;"><i class="fa-solid fa-eye" style="color: var(--ie-red);"></i> Prestataires les plus consultés</h2>
          <ol class="ie-rank-list">
            <li v-for="p in data.most_viewed_profiles" :key="p.id">
              <span>{{ p.business_name }}</span><strong>{{ fmt(p.view_count) }} vues</strong>
            </li>
          </ol>
          <p v-if="!data.most_viewed_profiles.length" class="ie-field-hint">Pas encore de données.</p>
        </div>

        <div class="ie-card ie-card-body">
          <h2 style="margin: 0 0 12px;"><i class="fa-solid fa-calendar-check" style="color: var(--ie-red);"></i> Prestataires les plus réservés</h2>
          <ol class="ie-rank-list">
            <li v-for="p in data.most_booked_profiles" :key="p.id">
              <span>{{ p.business_name }}</span><strong>{{ fmt(p.confirmed_count) }} résa.</strong>
            </li>
          </ol>
          <p v-if="!data.most_booked_profiles.length" class="ie-field-hint">Pas encore de données.</p>
        </div>

        <div class="ie-card ie-card-body">
          <h2 style="margin: 0 0 12px;"><i class="fa-solid fa-concierge-bell" style="color: var(--ie-red);"></i> Services les plus demandés</h2>
          <ol class="ie-rank-list">
            <li v-for="s in data.most_requested_services" :key="s.id">
              <span>{{ s.name }} <em>— {{ s.business_name }}</em></span><strong>{{ fmt(s.request_count) }}</strong>
            </li>
          </ol>
          <p v-if="!data.most_requested_services.length" class="ie-field-hint">Pas encore de données.</p>
        </div>

        <div class="ie-card ie-card-body">
          <h2 style="margin: 0 0 12px;"><i class="fa-solid fa-location-dot" style="color: var(--ie-red);"></i> Villes les plus actives</h2>
          <ol class="ie-rank-list">
            <li v-for="c in data.top_cities" :key="c.city">
              <span>{{ c.city }}</span><strong>{{ fmt(c.count) }}</strong>
            </li>
          </ol>
          <p v-if="!data.top_cities.length" class="ie-field-hint">Pas encore de données.</p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-analytics-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin-bottom: 20px; }
.ie-kpi { padding: 18px; display: flex; flex-direction: column; gap: 4px; }
.ie-kpi-value { font-size: 24px; font-weight: 800; color: var(--ie-navy); }
.ie-kpi-label { font-size: 12px; color: var(--ie-muted); }

.ie-revenue-card { margin-bottom: 20px; }
.ie-revenue-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
.ie-revenue-grid div { display: flex; flex-direction: column; gap: 4px; }
.ie-revenue-grid strong { font-size: 18px; color: var(--ie-red); }
.ie-revenue-grid span { font-size: 12px; color: var(--ie-muted); }

.ie-analytics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.ie-rank-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.ie-rank-list li { display: flex; justify-content: space-between; gap: 10px; font-size: 12.5px; color: var(--ie-ink); padding-bottom: 6px; border-bottom: 1px solid var(--ie-line); }
.ie-rank-list li:last-child { border-bottom: 0; }
.ie-rank-list em { color: var(--ie-muted); font-style: normal; font-size: 11.5px; }
.ie-rank-list strong { color: var(--ie-red); white-space: nowrap; }

@media (max-width: 700px) { .ie-analytics-kpis { grid-template-columns: repeat(2, 1fr); } }
</style>
