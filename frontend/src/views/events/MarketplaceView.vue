<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";

const auth = useAuthStore();
const lightbox = useLightboxStore();

const events = ref([]);
const ticketTypesByEvent = reactive({});
const loading = ref(true);

const formByEvent = reactive({});
const purchasing = ref(null);
const purchaseError = reactive({});
const purchaseSuccess = reactive({});

const PAYMENT_PROVIDERS = [
  { value: "mobile_money", label: "Orange Money / Mobile Money" },
  { value: "paypal", label: "Carte bancaire (PayPal)" },
  { value: "demo", label: "Mode démonstration" },
];

function eventQuery(event) {
  return [event.venue_name, event.venue_address, event.venue_city].filter(Boolean).join(", ");
}

function mapLinkUrl(event) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(eventQuery(event))}`;
}

function minPrice(eventId) {
  const types = ticketTypesByEvent[eventId] || [];
  if (!types.length) return null;
  return Math.min(...types.map((t) => Number(t.price)));
}

function quantityOptions(event) {
  const form = formByEvent[event.id];
  const selected = (ticketTypesByEvent[event.id] || []).find((ticket) => String(ticket.id) === String(form?.ticketType));
  const available = Math.min(10, selected?.remaining_quota || 0);
  return Array.from({ length: available }, (_, index) => index + 1);
}

function syncTicketSelection(event) {
  const form = formByEvent[event.id];
  const types = ticketTypesByEvent[event.id] || [];
  if (!types.some((ticket) => String(ticket.id) === String(form.ticketType))) {
    form.ticketType = types[0]?.id || "";
  }
  const selected = types.find((ticket) => String(ticket.id) === String(form.ticketType));
  form.quantity = Math.min(form.quantity, Math.max(1, Math.min(10, selected?.remaining_quota || 1)));
}

function initForm(event) {
  const types = ticketTypesByEvent[event.id] || [];
  formByEvent[event.id] = {
    ticketType: types[0]?.id || "",
    quantity: 1,
    paymentProvider: "mobile_money",
    firstName: auth.user?.first_name || "",
    lastName: auth.user?.last_name || "",
    email: auth.user?.email || "",
    phone: auth.user?.phone || "",
  };
}

function selectTicketType(event, ticketTypeId) {
  formByEvent[event.id].ticketType = ticketTypeId;
  syncTicketSelection(event);
}

async function loadEvents() {
  loading.value = true;
  try {
    const [eventsRes, typesRes] = await Promise.all([
      api.get("/events/marketplace/"),
      api.get("/tickets/types/marketplace/"),
    ]);
    events.value = eventsRes.data.results || eventsRes.data;
    const allTypes = typesRes.data.results || typesRes.data;
    events.value.forEach((event) => {
      ticketTypesByEvent[event.id] = allTypes.filter((t) => t.event === event.id);
      initForm(event);
    });
  } finally {
    loading.value = false;
  }
}

async function buyTicket(event) {
  const form = formByEvent[event.id];
  purchaseError[event.id] = "";
  if (!form.ticketType) {
    purchaseError[event.id] = "Choisissez un type de billet.";
    return;
  }
  purchasing.value = event.id;
  try {
    await api.post("/tickets/purchase/", {
      ticket_type: form.ticketType,
      quantity: form.quantity,
      payment_provider: form.paymentProvider,
      buyer_first_name: form.firstName,
      buyer_last_name: form.lastName,
      buyer_email: form.email,
      buyer_phone: form.phone,
    });
    purchaseSuccess[event.id] = "Paiement confirmé — votre billet est prêt dans « Mes billets ».";
    const { data } = await api.get("/tickets/types/marketplace/", { params: { event: event.id } });
    ticketTypesByEvent[event.id] = data.results || data;
    syncTicketSelection(event);
  } catch (e) {
    const d = e?.response?.data;
    purchaseError[event.id] = d?.detail || d?.non_field_errors?.[0] || "L'achat a échoué.";
    if ([400, 409].includes(e?.response?.status)) {
      try {
        const { data } = await api.get("/tickets/types/marketplace/", { params: { event: event.id } });
        ticketTypesByEvent[event.id] = data.results || data;
        syncTicketSelection(event);
      } catch { /* Le message d'erreur de l'achat reste affiché. */ }
    }
  } finally {
    purchasing.value = null;
  }
}

onMounted(loadEvents);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-store" style="color: var(--ie-red); margin-right: 8px;"></i>Billetterie</h1>
        <p class="ie-page-subtitle">Découvrez les événements publics et achetez vos billets directement.</p>
      </div>
    </div>

    <div class="ie-instant-banner">
      <div class="ie-instant-icon"><i class="fa-solid fa-bolt"></i></div>
      <div class="ie-instant-text">
        <strong>Paiement instantané → Billet PAYÉ</strong>
        <p>Vous payez, la transaction se confirme, votre billet passe en statut PAYÉ et votre QR d'entrée est généré. Aucune étape supplémentaire requise.</p>
      </div>
      <span class="ie-badge ie-badge-success">PAYÉ</span>
    </div>

    <div v-if="loading" class="ie-catalog-grid">
      <div v-for="i in 3" :key="i" class="ie-skeleton" style="height: 480px;"></div>
    </div>

    <div v-else-if="events.length" class="ie-catalog-grid">
      <div v-for="event in events" :key="event.id" class="ie-card ie-market-card">
        <div class="ie-market-photo">
          <img v-if="event.photo" :src="event.photo" :alt="event.title" class="ie-zoomable" @click="lightbox.open(event.photo, event.title)" />
          <i v-else class="fa-solid fa-calendar-week"></i>
          <div class="ie-market-pills">
            <span v-for="tt in (ticketTypesByEvent[event.id] || []).slice(0, 2)" :key="tt.id" class="ie-market-pill-overlay">{{ tt.name }}</span>
          </div>
          <span class="ie-market-price-badge">
            {{ minPrice(event.id) !== null ? `à partir de ${minPrice(event.id).toLocaleString('fr-FR')} ${ticketTypesByEvent[event.id][0].currency}` : "Sur devis" }}
          </span>
        </div>

        <div class="ie-card-body">
          <span class="ie-market-eyebrow"><i class="fa-solid fa-calendar-check"></i> Événement</span>
          <h3 class="ie-market-title">{{ event.title }}</h3>
          <p class="ie-market-desc">{{ event.description || "Aucune description fournie." }}</p>
          <div class="ie-market-meta">
            <span><i class="fa-solid fa-calendar-day"></i> {{ new Date(event.start_date).toLocaleDateString('fr-FR') }}</span>
            <span v-if="event.venue_name"><i class="fa-solid fa-location-dot"></i> {{ event.venue_name }}</span>
            <a v-if="event.venue_name" :href="mapLinkUrl(event)" target="_blank" rel="noopener" class="ie-market-itinerary">
              <i class="fa-solid fa-diamond-turn-right"></i> Voir l'itinéraire
            </a>
          </div>

          <div v-if="(ticketTypesByEvent[event.id] || []).length" class="ie-market-type-pills">
            <button
              v-for="tt in ticketTypesByEvent[event.id]" :key="tt.id" type="button"
              class="ie-market-type-pill" :class="{ active: formByEvent[event.id]?.ticketType === tt.id }"
              @click="selectTicketType(event, tt.id)"
            >
              <i class="fa-solid fa-ticket"></i> {{ tt.name }}
            </button>
          </div>

          <template v-if="(ticketTypesByEvent[event.id] || []).length && formByEvent[event.id]">
          <p v-if="purchaseSuccess[event.id]" class="ie-alert ie-alert-success" style="margin-top: 10px;">{{ purchaseSuccess[event.id] }}</p>
          <p v-if="purchaseError[event.id]" class="ie-alert ie-alert-danger" style="margin-top: 10px;">{{ purchaseError[event.id] }}</p>
            <form class="ie-market-form" @submit.prevent="buyTicket(event)">
              <select v-model="formByEvent[event.id].ticketType" class="ie-select">
                <option value="" disabled>Choisir le type de billet</option>
                <option v-for="tt in ticketTypesByEvent[event.id]" :key="tt.id" :value="tt.id">
                  {{ tt.name }} — {{ Number(tt.price).toLocaleString('fr-FR') }} {{ tt.currency }} ({{ tt.remaining_quota }} restant(s))
                </option>
              </select>

              <div class="ie-form-row">
                <select v-model.number="formByEvent[event.id].quantity" class="ie-select">
                  <option v-for="n in quantityOptions(event)" :key="n" :value="n">{{ n }} billet{{ n > 1 ? 's' : '' }}</option>
                </select>
                <select v-model="formByEvent[event.id].paymentProvider" class="ie-select">
                  <option v-for="p in PAYMENT_PROVIDERS" :key="p.value" :value="p.value">{{ p.label }}</option>
                </select>
              </div>

              <div class="ie-form-row">
                <input v-model="formByEvent[event.id].firstName" class="ie-input" placeholder="Prénom" required />
                <input v-model="formByEvent[event.id].lastName" class="ie-input" placeholder="Nom" required />
              </div>
              <input v-model="formByEvent[event.id].email" type="email" class="ie-input" placeholder="Email" required />
              <input v-model="formByEvent[event.id].phone" class="ie-input" placeholder="Téléphone" required />

              <button class="ie-btn ie-btn-primary" type="submit" style="width: 100%;" :disabled="purchasing === event.id">
                <i class="fa-solid fa-lock"></i> {{ purchasing === event.id ? "Traitement…" : "Commander ce billet" }}
              </button>
            </form>
          </template>
          <p v-else class="ie-empty-inline">Aucun billet disponible pour le moment.</p>
        </div>
      </div>
    </div>
    <EmptyState v-else icon="fa-solid fa-store" text="Aucun événement public disponible pour le moment." />
  </div>
</template>

<style scoped>
.ie-instant-banner {
  display: flex; align-items: center; gap: 14px;
  background: var(--ie-red-soft); border: 1px solid var(--ie-red); border-radius: 12px;
  padding: 14px 16px; margin-bottom: 22px;
}
.ie-instant-icon {
  width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
  background: var(--ie-red); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.ie-instant-text { flex: 1; }
.ie-instant-text strong { display: block; font-size: 13.5px; color: var(--ie-red); margin-bottom: 2px; }
.ie-instant-text p { margin: 0; font-size: 12px; color: var(--ie-ink); line-height: 1.5; }

.ie-catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; }
.ie-market-card { overflow: hidden; display: flex; flex-direction: column; }
.ie-market-photo {
  height: 150px; background: var(--ie-navy-soft); position: relative;
  display: flex; align-items: center; justify-content: center;
}
.ie-market-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-market-photo i { font-size: 36px; color: var(--ie-navy); opacity: 0.35; }
.ie-market-pills { position: absolute; top: 10px; left: 10px; display: flex; gap: 6px; flex-wrap: wrap; max-width: calc(100% - 20px); }
.ie-market-pill-overlay {
  background: rgba(23, 27, 38, 0.72); color: #fff; font-size: 10px; font-weight: 700;
  padding: 4px 9px; border-radius: 999px; backdrop-filter: blur(2px);
}
.ie-market-price-badge {
  position: absolute; bottom: 10px; right: 10px;
  background: rgba(23, 27, 38, 0.82); color: #fff; font-size: 11px; font-weight: 700;
  padding: 5px 10px; border-radius: 999px;
}

.ie-market-eyebrow {
  font-size: 10.5px; font-weight: 800; letter-spacing: 0.05em; color: var(--ie-red);
  text-transform: uppercase; display: flex; align-items: center; gap: 5px;
}
.ie-market-title { margin: 6px 0 6px; font-size: 15px; color: var(--ie-navy); }
.ie-market-desc {
  font-size: 12.5px; color: var(--ie-muted); line-height: 1.5; margin: 0 0 10px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.ie-market-meta { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--ie-ink); margin-bottom: 10px; }
.ie-market-meta i { color: var(--ie-red); width: 14px; }
.ie-market-itinerary { color: var(--ie-red); font-weight: 600; }

.ie-market-type-pills { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.ie-market-type-pill {
  display: inline-flex; align-items: center; gap: 5px;
  border: 1px solid var(--ie-line); background: #fff; color: var(--ie-navy);
  font-size: 11.5px; font-weight: 600; padding: 5px 10px; border-radius: 999px; cursor: pointer;
}
.ie-market-type-pill i { font-size: 10px; }
.ie-market-type-pill.active { background: var(--ie-red); border-color: var(--ie-red); color: #fff; }

.ie-market-form { display: flex; flex-direction: column; gap: 10px; border-top: 1px solid var(--ie-line); padding-top: 12px; }
.ie-market-form .ie-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ie-empty-inline { font-size: 12px; color: var(--ie-muted); margin: 0; }
</style>
