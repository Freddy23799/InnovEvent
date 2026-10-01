<script setup>
import { computed, onMounted, ref } from "vue";
import ChartCanvas from "../../components/ChartCanvas.vue";
import HorizontalBarList from "../../components/HorizontalBarList.vue";
import KpiCard from "../../components/KpiCard.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();

const BOOKING_STATUS_LABELS = { pending: "En attente", confirmed: "Confirmée", cancelled: "Annulée" };
const BOOKING_STATUS_BADGE = { pending: "ie-badge-warning", confirmed: "ie-badge-success", cancelled: "ie-badge-danger" };
const RESOURCE_ICONS = { venue: "fa-solid fa-building-columns", provider: "fa-solid fa-handshake", equipment: "fa-solid fa-sliders" };
const CHART_COLORS = ["#C0272D", "#39495B", "#1E7B4D", "#A66A00", "#7C8894", "#8C744A", "#5A6672"];

const loading = ref(true);
const events = ref([]);
const ticketTypes = ref([]);
const bookings = ref([]);

async function loadDashboard() {
  loading.value = true;
  try {
    const [eventsRes, bookingsRes] = await Promise.all([
      api.get("/events/"),
      api.get("/bookings/", { params: { ordering: "-created_at" } }),
    ]);
    events.value = eventsRes.data.results || eventsRes.data;
    bookings.value = bookingsRes.data.results || bookingsRes.data;
    const typeRequests = events.value.map((e) => api.get("/tickets/types/", { params: { event: e.id } }));
    const typeResults = await Promise.all(typeRequests);
    ticketTypes.value = typeResults.flatMap((r) => r.data.results || r.data);
  } finally {
    loading.value = false;
  }
}

const publicEventsCount = computed(() => events.value.filter((e) => e.is_public).length);
const totalTicketsSold = computed(() => ticketTypes.value.reduce((sum, t) => sum + Number(t.sold_count || 0), 0));
const totalRevenue = computed(() => ticketTypes.value.reduce((sum, t) => sum + Number(t.sold_count || 0) * Number(t.price), 0));

const nextEvent = computed(() => {
  const now = new Date();
  const upcoming = events.value.filter((e) => new Date(e.start_date) >= now && e.status !== "cancelled");
  return [...upcoming].sort((a, b) => (b.is_public - a.is_public) || (new Date(a.start_date) - new Date(b.start_date)))[0] || null;
});

const daysUntilNextEvent = computed(() => {
  if (!nextEvent.value) return null;
  const diff = new Date(nextEvent.value.start_date) - new Date();
  return Math.max(Math.ceil(diff / (1000 * 60 * 60 * 24)), 0);
});

const salesBars = computed(() =>
  ticketTypes.value.map((t) => ({
    label: `${t.event_title} — ${t.name}`,
    value: Number(t.sold_count || 0),
    display: `${t.sold_count || 0} / ${t.quota} vendus`,
  }))
);

const ticketsByEventChart = computed(() => {
  const byEvent = {};
  ticketTypes.value.forEach((t) => { byEvent[t.event_title] = (byEvent[t.event_title] || 0) + Number(t.sold_count || 0); });
  const entries = Object.entries(byEvent).filter(([, v]) => v > 0);
  return {
    labels: entries.map(([label]) => label),
    datasets: [{ data: entries.map(([, v]) => v), backgroundColor: CHART_COLORS, borderWidth: 0 }],
  };
});

const chartOptionsDoughnut = {
  plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } },
};

const ticketsSoldByEvent = computed(() => {
  const byEvent = {};
  ticketTypes.value.forEach((t) => { byEvent[t.event] = (byEvent[t.event] || 0) + Number(t.sold_count || 0); });
  return byEvent;
});

const recentBookings = computed(() => bookings.value.slice(0, 6));

onMounted(loadDashboard);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-gauge-high" style="color: var(--ie-red); margin-right: 8px;"></i>Mon espace organisateur</h1>

    <div v-if="!loading && nextEvent" class="ie-spotlight">
      <div class="ie-spotlight-photo" :class="{ 'is-empty': !nextEvent.photo }">
        <img v-if="nextEvent.photo" :src="nextEvent.photo" :alt="nextEvent.title" class="ie-zoomable" @click="lightbox.open(nextEvent.photo, nextEvent.title)" />
        <i v-else class="fa-solid fa-calendar-week"></i>
      </div>
      <div class="ie-spotlight-body">
        <span class="ie-spotlight-eyebrow">Prochain événement{{ nextEvent.is_public ? " public" : "" }}</span>
        <router-link :to="{ name: 'event-detail', params: { id: nextEvent.id } }" class="ie-spotlight-title">{{ nextEvent.title }}</router-link>
        <div class="ie-spotlight-meta">
          <span><i class="fa-solid fa-calendar-day"></i> {{ new Date(nextEvent.start_date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) }}</span>
          <span v-if="nextEvent.venue_name"><i class="fa-solid fa-location-dot"></i> {{ nextEvent.venue_name }}</span>
          <span><i class="fa-solid fa-ticket"></i> {{ ticketsSoldByEvent[nextEvent.id] || 0 }} billets vendus</span>
        </div>
        <div class="ie-spotlight-progress">
          <div class="ie-spotlight-progress-track"><div class="ie-spotlight-progress-fill" :style="{ width: nextEvent.progress_percent + '%' }"></div></div>
          <span>{{ nextEvent.progress_percent }}% de préparation complétée</span>
        </div>
      </div>
      <div class="ie-spotlight-countdown">
        <b>{{ daysUntilNextEvent }}</b>
        <span>{{ daysUntilNextEvent === 1 ? "jour restant" : "jours restants" }}</span>
      </div>
    </div>

    <div class="ie-kpi-grid">
      <KpiCard label="Mes événements" :value="events.length" :loading="loading" icon="fa-solid fa-calendar-week" tone="navy" />
      <KpiCard label="Événements publics" :value="publicEventsCount" :loading="loading" icon="fa-solid fa-earth-africa" tone="success" />
      <KpiCard label="Billets vendus" :value="totalTicketsSold" :loading="loading" icon="fa-solid fa-ticket" tone="red" />
      <KpiCard label="Recette billetterie (XAF)" :value="totalRevenue.toLocaleString('fr-FR')" :loading="loading" icon="fa-solid fa-sack-dollar" tone="warning" />
    </div>

    <div class="ie-dashboard-grid">
      <div class="ie-card" style="padding: 20px;" v-if="ticketTypes.length">
        <h2 style="margin-bottom: 18px;">Ventes par type de billet</h2>
        <HorizontalBarList :items="salesBars" />
      </div>
      <div class="ie-card" style="padding: 20px;">
        <h2 style="margin-bottom: 14px;">Billets vendus par événement</h2>
        <ChartCanvas type="doughnut" :data="ticketsByEventChart" :options="chartOptionsDoughnut" />
      </div>
    </div>

    <div class="ie-card" style="margin-top: 20px; padding: 20px;">
      <div class="ie-section-head">
        <h2>Réservations récentes</h2>
        <router-link :to="{ name: 'bookings' }" class="text-link-sm">Voir tout <i class="fa-solid fa-arrow-right"></i></router-link>
      </div>
      <div class="ie-table-wrap" v-if="recentBookings.length"><table class="ie-table">
        <thead>
          <tr><th></th><th>Ressource</th><th>Événement</th><th>Période</th><th>Statut</th><th class="ie-num">Coût estimé</th></tr>
        </thead>
        <tbody>
          <tr v-for="booking in recentBookings" :key="booking.id">
            <td><i :class="RESOURCE_ICONS[booking.resource_type]" style="color: var(--ie-red);"></i></td>
            <td>{{ booking.resource_label }}</td>
            <td>{{ booking.event_title }}</td>
            <td>{{ new Date(booking.start_datetime).toLocaleDateString('fr-FR') }}</td>
            <td><span class="ie-badge" :class="BOOKING_STATUS_BADGE[booking.status] || 'ie-badge-neutral'">{{ BOOKING_STATUS_LABELS[booking.status] || booking.status }}</span></td>
            <td class="ie-num">{{ booking.estimated_cost != null ? Number(booking.estimated_cost).toLocaleString('fr-FR') + ' XAF' : '—' }}</td>
          </tr>
        </tbody>
      </table></div>
      <div v-else class="ie-empty-state">Aucune réservation pour le moment.</div>
    </div>

    <div class="ie-card" style="margin-top: 20px; padding: 20px;">
      <h2 style="margin-bottom: 14px;">Mes événements</h2>
      <div class="ie-table-wrap" v-if="events.length"><table class="ie-table">
        <thead>
          <tr><th></th><th>Titre</th><th>Date</th><th>Visibilité</th><th class="ie-num">Billets vendus</th><th>Statut</th></tr>
        </thead>
        <tbody>
          <tr v-for="event in events" :key="event.id">
            <td>
              <div class="ie-event-thumb">
                <img v-if="event.photo" :src="event.photo" :alt="event.title" class="ie-zoomable" @click="lightbox.open(event.photo, event.title)" />
                <i v-else class="fa-solid fa-calendar-week"></i>
              </div>
            </td>
            <td><router-link :to="{ name: 'event-detail', params: { id: event.id } }">{{ event.title }}</router-link></td>
            <td>{{ new Date(event.start_date).toLocaleDateString('fr-FR') }}</td>
            <td><span class="ie-badge" :class="event.is_public ? 'ie-badge-success' : 'ie-badge-neutral'">{{ event.is_public ? "Public" : "Privé" }}</span></td>
            <td class="ie-num">{{ ticketsSoldByEvent[event.id] || 0 }}</td>
            <td><span class="ie-badge ie-badge-neutral">{{ event.status }}</span></td>
          </tr>
        </tbody>
      </table></div>
      <div v-else class="ie-empty-state">
        Vous n'avez pas encore créé d'événement.
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 18px; }
.ie-dashboard-grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 20px; margin-top: 20px; }
@media (max-width: 1100px) { .ie-dashboard-grid { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .ie-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.ie-event-thumb {
  width: 40px; height: 40px; border-radius: 8px; overflow: hidden;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-event-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-event-thumb i { color: var(--ie-navy); opacity: 0.4; font-size: 14px; }

.ie-section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.ie-section-head h2 { margin: 0; }
.text-link-sm { font-size: 12.5px; font-weight: 700; color: var(--ie-red); display: inline-flex; align-items: center; gap: 5px; }
.text-link-sm:hover { text-decoration: underline; }

/* Spotlight prochain événement */
.ie-spotlight {
  display: grid; grid-template-columns: 140px 1fr auto; gap: 22px; align-items: center;
  background: linear-gradient(120deg, var(--ie-navy) 0%, #2c394a 100%); border-radius: var(--ie-radius-lg);
  padding: 20px 26px; margin-top: 18px; color: #fff; box-shadow: var(--ie-shadow);
}
.ie-spotlight-photo { width: 140px; height: 100px; border-radius: 12px; overflow: hidden; background: rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ie-spotlight-photo img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.ie-spotlight-photo.is-empty i { font-size: 30px; color: rgba(255,255,255,0.4); }
.ie-spotlight-eyebrow { display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255,255,255,0.6); margin-bottom: 6px; }
.ie-spotlight-title { display: block; font-size: 19px; font-weight: 700; color: #fff; margin-bottom: 10px; }
.ie-spotlight-title:hover { text-decoration: underline; }
.ie-spotlight-meta { display: flex; gap: 18px; flex-wrap: wrap; font-size: 12.5px; color: rgba(255,255,255,0.78); margin-bottom: 12px; }
.ie-spotlight-meta i { color: var(--ie-red); margin-right: 5px; }
.ie-spotlight-progress { display: flex; align-items: center; gap: 10px; }
.ie-spotlight-progress-track { width: 160px; height: 7px; border-radius: 999px; background: rgba(255,255,255,0.16); overflow: hidden; }
.ie-spotlight-progress-fill { height: 100%; background: var(--ie-red); border-radius: 999px; }
.ie-spotlight-progress span { font-size: 11.5px; color: rgba(255,255,255,0.7); }
.ie-spotlight-countdown { text-align: center; padding-left: 22px; border-left: 1px solid rgba(255,255,255,0.18); flex-shrink: 0; }
.ie-spotlight-countdown b { display: block; font-size: 34px; font-weight: 800; line-height: 1; color: #fff; }
.ie-spotlight-countdown span { font-size: 11.5px; color: rgba(255,255,255,0.7); white-space: nowrap; }

@media (max-width: 860px) {
  .ie-spotlight { grid-template-columns: 1fr; text-align: center; }
  .ie-spotlight-photo { margin: 0 auto; }
  .ie-spotlight-meta, .ie-spotlight-progress { justify-content: center; }
  .ie-spotlight-countdown { border-left: none; border-top: 1px solid rgba(255,255,255,0.18); padding: 12px 0 0; }
}
</style>
