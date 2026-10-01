<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import ChartCanvas from "../../components/ChartCanvas.vue";
import HorizontalBarList from "../../components/HorizontalBarList.vue";
import KpiCard from "../../components/KpiCard.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();
const router = useRouter();

const contactingAdmin = ref(false);

async function contactAdmin() {
  contactingAdmin.value = true;
  try {
    const { data } = await api.post("/messaging/conversations/contact-admin/");
    router.push({ name: "messaging", query: { conversation: data.id } });
  } finally {
    contactingAdmin.value = false;
  }
}

const BOOKING_STATUS_LABELS = { pending: "En attente", confirmed: "Confirmée", cancelled: "Annulée" };
const BOOKING_STATUS_BADGE = { pending: "ie-badge-warning", confirmed: "ie-badge-success", cancelled: "ie-badge-danger" };
const RESOURCE_ICONS = { venue: "fa-solid fa-building-columns", provider: "fa-solid fa-handshake", equipment: "fa-solid fa-sliders" };

// Statuts des demandes de devis marketplace — mêmes libellés que MyBookingRequestsView,
// pour rester cohérent sur toute la plateforme.
const QUOTE_STATUS_META = {
  pending: { label: "En attente de réponse", badge: "ie-badge-neutral" },
  quoted: { label: "Devis reçu", badge: "ie-badge-warning" },
  modification_requested: { label: "Modification demandée", badge: "ie-badge-warning" },
  accepted: { label: "Devis accepté — paiement attendu", badge: "ie-badge-warning" },
  confirmed: { label: "Confirmée (payée)", badge: "ie-badge-success" },
  completed: { label: "Prestation réalisée", badge: "ie-badge-success" },
  declined: { label: "Refusée", badge: "ie-badge-danger" },
  cancelled: { label: "Annulée", badge: "ie-badge-danger" },
  contacted: { label: "Mise en relation effectuée", badge: "ie-badge-neutral" },
};
const OPEN_QUOTE_STATUSES = new Set(["pending", "quoted", "modification_requested", "accepted"]);

const loading = ref(true);
const events = ref([]);
const bookings = ref([]);
const totalBudget = ref(0);
const totalSpent = ref(0);
const pendingBookings = ref(0);

// --- Activité marketplace (abonnements, devis, favoris) --------------------
const marketplaces = ref([]);
const quoteRequests = ref([]);
const favoritesCount = ref(0);

async function loadDashboard() {
  loading.value = true;
  try {
    const [eventsRes, bookingsRes, subsRes, requestsRes, favoritesRes] = await Promise.all([
      api.get("/events/"),
      api.get("/bookings/", { params: { ordering: "-created_at" } }),
      api.get("/marketplace/subscriptions/"),
      api.get("/marketplace/booking-requests/", { params: { ordering: "-created_at" } }),
      api.get("/marketplace/favorites/"),
    ]);
    events.value = eventsRes.data.results || eventsRes.data;
    bookings.value = bookingsRes.data.results || bookingsRes.data;
    totalBudget.value = events.value.reduce((sum, e) => sum + Number(e.budget_total), 0);
    totalSpent.value = events.value.reduce((sum, e) => sum + Number(e.spent_amount), 0);
    pendingBookings.value = bookings.value.filter((b) => b.status === "pending").length;
    marketplaces.value = subsRes.data.marketplaces || [];
    quoteRequests.value = requestsRes.data.results || requestsRes.data;
    favoritesCount.value = (favoritesRes.data.results || favoritesRes.data).length;
  } finally {
    loading.value = false;
  }
}

const activeSubscriptionsCount = computed(() => marketplaces.value.filter((m) => m.is_active).length);
const openQuotesCount = computed(() => quoteRequests.value.filter((r) => OPEN_QUOTE_STATUSES.has(r.status)).length);
const recentQuoteRequests = computed(() => quoteRequests.value.slice(0, 5));

const budgetUsedPercent = computed(() => (totalBudget.value > 0 ? Math.round((totalSpent.value / totalBudget.value) * 100) : 0));

const nextEvent = computed(() => {
  const now = new Date();
  return [...events.value]
    .filter((e) => new Date(e.start_date) >= now && e.status !== "cancelled")
    .sort((a, b) => new Date(a.start_date) - new Date(b.start_date))[0] || null;
});

const daysUntilNextEvent = computed(() => {
  if (!nextEvent.value) return null;
  const diff = new Date(nextEvent.value.start_date) - new Date();
  return Math.max(Math.ceil(diff / (1000 * 60 * 60 * 24)), 0);
});

const budgetBars = computed(() =>
  events.value.map((e) => ({
    label: e.title,
    value: Number(e.spent_amount),
    display: `${Number(e.spent_amount).toLocaleString('fr-FR')} / ${Number(e.budget_total).toLocaleString('fr-FR')} XAF`,
  }))
);

const budgetDoughnut = computed(() => {
  const remaining = Math.max(totalBudget.value - totalSpent.value, 0);
  return {
    labels: ["Dépensé", "Restant"],
    datasets: [{ data: [totalSpent.value, remaining], backgroundColor: ["#C0272D", "#EEF1F4"], borderWidth: 0 }],
  };
});

const bookingsDoughnut = computed(() => {
  const statuses = ["pending", "confirmed", "cancelled"];
  const counts = statuses.map((s) => bookings.value.filter((b) => b.status === s).length);
  return {
    labels: statuses.map((s) => BOOKING_STATUS_LABELS[s]),
    datasets: [{ data: counts, backgroundColor: ["#A66A00", "#1E7B4D", "#C0272D"], borderWidth: 0 }],
  };
});

const chartOptionsDoughnut = {
  plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } },
};

const recentBookings = computed(() => bookings.value.slice(0, 6));

onMounted(loadDashboard);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <h1><i class="fa-solid fa-gauge-high" style="color: var(--ie-red); margin-right: 8px;"></i>Mon espace client</h1>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-ghost" :disabled="contactingAdmin" @click="contactAdmin">
          <i class="fa-solid fa-headset"></i> {{ contactingAdmin ? "Connexion…" : "Contacter le support" }}
        </button>
        <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-marketplace">
          <i class="fa-solid fa-store"></i> Marketplace InnovEvent
          <i class="fa-solid fa-arrow-right"></i>
        </router-link>
      </div>
    </div>

    <div v-if="!loading && nextEvent" class="ie-spotlight">
      <div class="ie-spotlight-photo" :class="{ 'is-empty': !nextEvent.photo }">
        <img v-if="nextEvent.photo" :src="nextEvent.photo" :alt="nextEvent.title" class="ie-zoomable" @click="lightbox.open(nextEvent.photo, nextEvent.title)" />
        <i v-else class="fa-solid fa-calendar-week"></i>
      </div>
      <div class="ie-spotlight-body">
        <span class="ie-spotlight-eyebrow">Prochain événement</span>
        <router-link :to="{ name: 'event-detail', params: { id: nextEvent.id } }" class="ie-spotlight-title">{{ nextEvent.title }}</router-link>
        <div class="ie-spotlight-meta">
          <span><i class="fa-solid fa-calendar-day"></i> {{ new Date(nextEvent.start_date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) }}</span>
          <span v-if="nextEvent.venue_name"><i class="fa-solid fa-location-dot"></i> {{ nextEvent.venue_name }}</span>
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
      <KpiCard label="Budget utilisé" :value="`${budgetUsedPercent}%`" :loading="loading" icon="fa-solid fa-coins" tone="red" />
      <KpiCard label="Dépensé (XAF)" :value="totalSpent.toLocaleString('fr-FR')" :loading="loading" icon="fa-solid fa-sack-dollar" tone="warning" />
      <KpiCard label="Réservations en attente" :value="pendingBookings" :loading="loading" icon="fa-solid fa-hourglass-half" tone="success" />
    </div>

    <div class="ie-kpi-grid" style="margin-top: 14px;">
      <KpiCard label="Marketplaces abonnés" :value="`${activeSubscriptionsCount}/${marketplaces.length}`" :loading="loading" icon="fa-solid fa-store" tone="navy" />
      <KpiCard label="Devis en cours" :value="openQuotesCount" :loading="loading" icon="fa-solid fa-file-invoice-dollar" tone="warning" />
      <KpiCard label="Prestataires favoris" :value="favoritesCount" :loading="loading" icon="fa-solid fa-heart" tone="red" />
      <KpiCard label="Devis confirmés" :value="quoteRequests.filter((r) => r.status === 'confirmed' || r.status === 'completed').length" :loading="loading" icon="fa-solid fa-circle-check" tone="success" />
    </div>

    <div class="ie-dashboard-grid">
      <div class="ie-card" style="padding: 20px;" v-if="events.length">
        <h2 style="margin-bottom: 18px;">Consommation budgétaire par événement</h2>
        <HorizontalBarList :items="budgetBars" />
      </div>
      <div class="ie-card" style="padding: 20px;">
        <h2 style="margin-bottom: 14px;">Budget global</h2>
        <ChartCanvas type="doughnut" :data="budgetDoughnut" :options="chartOptionsDoughnut" />
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
      <div class="ie-section-head">
        <h2>Mes demandes de devis marketplace</h2>
        <router-link :to="{ name: 'my-booking-requests' }" class="text-link-sm">Voir tout <i class="fa-solid fa-arrow-right"></i></router-link>
      </div>
      <div class="ie-table-wrap" v-if="recentQuoteRequests.length"><table class="ie-table">
        <thead>
          <tr><th>Prestataire</th><th>Événement</th><th>Ville</th><th>Statut</th><th class="ie-num">Devis</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in recentQuoteRequests" :key="r.id">
            <td>{{ r.business_name }}</td>
            <td>{{ r.event_type || "—" }}</td>
            <td>{{ r.city || "—" }}</td>
            <td><span class="ie-badge" :class="QUOTE_STATUS_META[r.status]?.badge || 'ie-badge-neutral'">{{ QUOTE_STATUS_META[r.status]?.label || r.status }}</span></td>
            <td class="ie-num">{{ r.latest_quote ? Number(r.latest_quote.total_amount).toLocaleString('fr-FR') + ' ' + r.latest_quote.currency : "—" }}</td>
          </tr>
        </tbody>
      </table></div>
      <div v-else class="ie-empty-state">
        Aucune demande de devis pour le moment.
        <router-link :to="{ name: 'premium-marketplace' }">Découvrir le Marketplace</router-link>
      </div>
    </div>

    <div class="ie-dashboard-grid" style="margin-top: 20px;">
      <div class="ie-card" style="padding: 20px; grid-column: span 2;">
        <h2 style="margin-bottom: 14px;">Mes événements</h2>
        <div class="ie-table-wrap" v-if="events.length"><table class="ie-table">
          <thead>
            <tr><th></th><th>Titre</th><th>Date</th><th>Avancement</th><th>Statut</th></tr>
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
              <td>
                <div class="ie-mini-progress">
                  <div class="ie-mini-progress-track"><div class="ie-mini-progress-fill" :style="{ width: event.progress_percent + '%' }"></div></div>
                  <span>{{ event.progress_percent }}%</span>
                </div>
              </td>
              <td><span class="ie-badge ie-badge-neutral">{{ event.status }}</span></td>
            </tr>
          </tbody>
        </table></div>
        <div v-else class="ie-empty-state">
          Vous n'avez pas encore créé d'événement.
        </div>
      </div>
    </div>

    <div class="ie-card ie-about-marketplace" style="margin-top: 20px;">
      <div class="ie-about-marketplace-head">
        <div>
          <span class="ie-spotlight-eyebrow" style="color: var(--ie-red);">À propos</span>
          <h2 style="margin: 4px 0 0;">Le Marketplace InnovEvent</h2>
        </div>
        <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-marketplace">
          <i class="fa-solid fa-store"></i> Explorer le Marketplace
        </router-link>
      </div>
      <div class="ie-table-wrap"><table class="ie-table ie-about-table">
        <tbody>
          <tr>
            <th><i class="fa-solid fa-circle-question"></i> Qu'est-ce que c'est ?</th>
            <td>Un espace où vous trouvez des prestataires événementiels vérifiés — DJ, traiteurs, décorateurs, photographes, agences — ainsi que des designers d'intérieur, organisés par métier, avec profil complet, portfolio, avis et tarifs indicatifs.</td>
          </tr>
          <tr>
            <th><i class="fa-solid fa-star"></i> Pourquoi s'abonner ?</th>
            <td>L'abonnement (mensuel ou annuel, au choix) donne un accès illimité aux profils détaillés, à la demande de devis, aux favoris, aux recommandations personnalisées et au calendrier de disponibilités de chaque prestataire — au lieu de chercher et négocier partout séparément.</td>
          </tr>
          <tr>
            <th><i class="fa-solid fa-route"></i> Comment ça marche ?</th>
            <td>Vous envoyez une demande de devis avec vos besoins (type d'événement, date, budget). Le prestataire répond avec une proposition détaillée et négociable. Une fois d'accord, vous payez et suivez la prestation directement depuis votre espace.</td>
          </tr>
          <tr>
            <th><i class="fa-solid fa-lock"></i> Vos données restent privées</th>
            <td>Le prestataire ne voit jamais votre téléphone ni votre email tant que vous ne le décidez pas : toute la négociation passe par les devis structurés et la messagerie intégrée de la plateforme.</td>
          </tr>
        </tbody>
      </table></div>
    </div>
  </div>
</template>

<style scoped>
.ie-btn-marketplace {
  display: inline-flex; align-items: center; gap: 8px;
  background: linear-gradient(120deg, var(--ie-red), #8a0e16); color: #fff; border: 0;
}
.ie-btn-marketplace:hover { background: linear-gradient(120deg, #8a0e16, #6b0a10); }
.ie-btn-marketplace i:last-child { font-size: 11px; }

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

.ie-mini-progress { display: flex; align-items: center; gap: 8px; }
.ie-mini-progress-track { width: 70px; height: 6px; border-radius: 999px; background: #eef0f2; overflow: hidden; }
.ie-mini-progress-fill { height: 100%; background: var(--ie-red); border-radius: 999px; }
.ie-mini-progress span { font-size: 12px; color: var(--ie-muted); white-space: nowrap; }

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

/* À propos du Marketplace */
.ie-about-marketplace { padding: 22px 24px; }
.ie-about-marketplace-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; flex-wrap: wrap; }
.ie-about-table { table-layout: fixed; }
.ie-about-table th {
  width: 220px; text-align: left; vertical-align: top; padding: 14px 16px 14px 0;
  font-size: 13px; font-weight: 700; color: var(--ie-navy);
}
.ie-about-table th i { color: var(--ie-red); margin-right: 7px; width: 16px; }
.ie-about-table td { padding: 14px 0; font-size: 13px; color: var(--ie-muted); line-height: 1.6; }
.ie-about-table tr + tr th, .ie-about-table tr + tr td { border-top: 1px solid var(--ie-line); }
@media (max-width: 700px) {
  .ie-about-table, .ie-about-table tbody, .ie-about-table tr, .ie-about-table th, .ie-about-table td { display: block; width: auto; }
  .ie-about-table td { padding-top: 4px; padding-bottom: 14px; }
}
</style>
