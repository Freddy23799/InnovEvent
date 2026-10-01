<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import KpiCard from "../../components/KpiCard.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";

const auth = useAuthStore();
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

const loading = ref(true);
const tickets = ref([]);
const marketEvents = ref([]);
const minPriceByEvent = ref({});
const paidPaymentsCount = ref(0);
const certificatesCount = ref(0);

const STATUS_LABELS = { valid: "Payé", used: "Utilisé", cancelled: "Annulé" };
const STATUS_BADGE = { valid: "ie-badge-success", used: "ie-badge-neutral", cancelled: "ie-badge-danger" };

async function loadDashboard() {
  loading.value = true;
  try {
    const [ticketsRes, eventsRes, typesRes, paymentsRes, certificatesRes] = await Promise.all([
      api.get("/tickets/my/"),
      api.get("/events/marketplace/"),
      api.get("/tickets/types/marketplace/"),
      api.get("/payments/", { params: { status: "completed" } }),
      api.get("/training/certificates/"),
    ]);
    tickets.value = ticketsRes.data.results || ticketsRes.data;
    marketEvents.value = (eventsRes.data.results || eventsRes.data).slice(0, 4);

    const types = typesRes.data.results || typesRes.data;
    const byEvent = {};
    types.forEach((t) => {
      const price = Number(t.price);
      if (!(t.event in byEvent) || price < byEvent[t.event]) byEvent[t.event] = price;
    });
    minPriceByEvent.value = byEvent;

    const paymentsData = paymentsRes.data;
    paidPaymentsCount.value = paymentsData.count ?? (paymentsData.results || paymentsData).length;
    const certificatesData = certificatesRes.data;
    certificatesCount.value = certificatesData.count ?? (certificatesData.results || certificatesData).length;
  } finally {
    loading.value = false;
  }
}

const upcomingTickets = computed(() =>
  tickets.value
    .filter((t) => new Date(t.event_start_date) > new Date() && t.status !== "cancelled")
    .sort((a, b) => new Date(a.event_start_date) - new Date(b.event_start_date))
    .slice(0, 3)
);

const upcomingEventsCount = computed(() => {
  const ids = new Set(
    tickets.value
      .filter((t) => new Date(t.event_start_date) > new Date() && t.status !== "cancelled")
      .map((t) => t.event)
  );
  return ids.size;
});

async function downloadTicketPdf(ticket) {
  const response = await api.get(`/tickets/my/${ticket.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `billet-${ticket.code}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

onMounted(loadDashboard);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1>Bonjour {{ auth.user?.first_name || auth.user?.username }} 👋</h1>
        <p class="ie-page-subtitle">Billets, événements &amp; notifications</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-ghost" :disabled="contactingAdmin" @click="contactAdmin">
          <i class="fa-solid fa-headset"></i> {{ contactingAdmin ? "Connexion…" : "Contacter le support" }}
        </button>
        <router-link :to="{ name: 'my-tickets' }" class="ie-btn ie-btn-secondary">
          <i class="fa-solid fa-ticket"></i> Mes billets
        </router-link>
        <router-link :to="{ name: 'marketplace' }" class="ie-btn ie-btn-primary">
          <i class="fa-solid fa-store"></i> Billetterie
        </router-link>
      </div>
    </div>

    <div class="ie-kpi-grid">
      <KpiCard label="Billets total" :value="tickets.length" :loading="loading" icon="fa-solid fa-ticket" tone="red" />
      <KpiCard label="Événements à venir" :value="upcomingEventsCount" :loading="loading" icon="fa-solid fa-calendar-check" tone="navy" />
      <KpiCard label="Paiements confirmés" :value="paidPaymentsCount" :loading="loading" icon="fa-solid fa-circle-check" tone="success" />
      <KpiCard label="Attestations disponibles" :value="certificatesCount" :loading="loading" icon="fa-solid fa-file-invoice" tone="warning" />
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-ticket"></i> Mes prochains billets</h2>
        <router-link :to="{ name: 'my-tickets' }" class="ie-section-link">Voir tout <i class="fa-solid fa-arrow-right"></i></router-link>
      </div>
      <div class="ie-card-body" v-if="loading">
        <div class="ie-skeleton" style="height: 70px; margin-bottom: 10px;"></div>
        <div class="ie-skeleton" style="height: 70px;"></div>
      </div>
      <div class="ie-card-body" v-else-if="upcomingTickets.length">
        <div v-for="ticket in upcomingTickets" :key="ticket.id" class="ie-upticket-row">
          <div class="ie-upticket-thumb">
            <img v-if="ticket.event_photo" :src="ticket.event_photo" :alt="ticket.event_title" class="ie-zoomable" @click="lightbox.open(ticket.event_photo, ticket.event_title)" />
            <i v-else class="fa-solid fa-ticket"></i>
          </div>
          <div class="ie-upticket-info">
            <strong>{{ ticket.event_title }}</strong>
            <div class="ie-upticket-meta">
              <span class="ie-badge ie-badge-neutral">{{ ticket.ticket_type_name }}</span>
              <span><i class="fa-solid fa-calendar-day"></i> {{ new Date(ticket.event_start_date).toLocaleDateString('fr-FR') }}</span>
              <span v-if="ticket.venue_name"><i class="fa-solid fa-location-dot"></i> {{ ticket.venue_name }}</span>
            </div>
          </div>
          <span class="ie-badge" :class="STATUS_BADGE[ticket.status] || 'ie-badge-neutral'">{{ STATUS_LABELS[ticket.status] || ticket.status }}</span>
          <button class="ie-btn ie-btn-primary ie-btn-sm" @click="downloadTicketPdf(ticket)">
            <i class="fa-solid fa-eye"></i> Ouvrir
          </button>
        </div>
      </div>
      <div class="ie-card-body" v-else>
        <p class="ie-empty-inline">Aucun billet à venir. Direction la billetterie pour découvrir les prochains événements !</p>
      </div>
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-store"></i> Événements disponibles</h2>
        <router-link :to="{ name: 'marketplace' }" class="ie-section-link">Voir la billetterie <i class="fa-solid fa-arrow-right"></i></router-link>
      </div>
      <div class="ie-card-body">
        <div v-if="loading" class="ie-catalog-grid">
          <div v-for="i in 4" :key="i" class="ie-skeleton" style="height: 220px;"></div>
        </div>
        <div v-else-if="marketEvents.length" class="ie-catalog-grid">
          <div v-for="event in marketEvents" :key="event.id" class="ie-market-card">
            <div class="ie-market-photo">
              <img v-if="event.photo" :src="event.photo" :alt="event.title" class="ie-zoomable" @click="lightbox.open(event.photo, event.title)" />
              <i v-else class="fa-solid fa-calendar-week"></i>
            </div>
            <div class="ie-market-body">
              <span class="ie-market-eyebrow">Événement</span>
              <strong class="ie-market-title">{{ event.title }}</strong>
              <div class="ie-market-meta">
                <span><i class="fa-solid fa-calendar-day"></i> {{ new Date(event.start_date).toLocaleDateString('fr-FR') }}</span>
                <span v-if="event.venue_name"><i class="fa-solid fa-location-dot"></i> {{ event.venue_name }}</span>
              </div>
              <div class="ie-market-footer">
                <span class="ie-market-price">
                  {{ event.id in minPriceByEvent ? `${minPriceByEvent[event.id].toLocaleString('fr-FR')}+ XAF` : "Sur devis" }}
                </span>
                <router-link :to="{ name: 'marketplace' }" class="ie-btn ie-btn-primary ie-btn-sm">
                  <i class="fa-solid fa-bag-shopping"></i> Acheter
                </router-link>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="ie-empty-inline">Aucun événement public disponible pour le moment.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 4px; }
@media (max-width: 900px) { .ie-kpi-grid { grid-template-columns: repeat(2, 1fr); } }

.ie-section { margin-top: 22px; }
.ie-card-header { display: flex; align-items: center; justify-content: space-between; }
.ie-section-link { font-size: 12.5px; font-weight: 700; color: var(--ie-red); white-space: nowrap; }
.ie-section-link i { margin-left: 4px; font-size: 11px; }
.ie-empty-inline { color: var(--ie-muted); font-size: 13px; margin: 0; }

.ie-upticket-row {
  display: flex; align-items: center; gap: 14px;
  padding: 12px 0; border-bottom: 1px solid var(--ie-line);
}
.ie-upticket-row:last-child { border-bottom: none; padding-bottom: 0; }
.ie-upticket-thumb {
  width: 52px; height: 52px; border-radius: 10px; overflow: hidden; flex-shrink: 0;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-upticket-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-upticket-thumb i { color: var(--ie-navy); opacity: 0.4; font-size: 18px; }
.ie-upticket-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.ie-upticket-info strong { font-size: 13.5px; color: var(--ie-navy); }
.ie-upticket-meta { display: flex; align-items: center; gap: 12px; font-size: 11.5px; color: var(--ie-muted); flex-wrap: wrap; }
.ie-upticket-meta i { color: var(--ie-red); margin-right: 3px; }

.ie-catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.ie-market-card { border: 1px solid var(--ie-line); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
.ie-market-photo {
  height: 120px; background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-market-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-market-photo i { font-size: 28px; color: var(--ie-navy); opacity: 0.35; }
.ie-market-body { padding: 12px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
.ie-market-eyebrow { font-size: 10px; font-weight: 800; letter-spacing: 0.06em; color: var(--ie-red); text-transform: uppercase; }
.ie-market-title { font-size: 13.5px; color: var(--ie-navy); }
.ie-market-meta { display: flex; flex-direction: column; gap: 3px; font-size: 11px; color: var(--ie-muted); }
.ie-market-meta i { color: var(--ie-red); width: 12px; }
.ie-market-footer { display: flex; align-items: center; justify-content: space-between; margin-top: auto; padding-top: 8px; }
.ie-market-price { font-size: 12.5px; font-weight: 800; color: var(--ie-navy); }
</style>
