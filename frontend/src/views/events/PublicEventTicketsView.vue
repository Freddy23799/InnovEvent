<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";

const props = defineProps({ eventId: { type: [String, Number], required: true } });

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const lightbox = useLightboxStore();

const loading = ref(true);
const notFound = ref(false);
const event = ref(null);
const ticketTypes = ref([]);

const form = reactive({
  ticketType: "",
  quantity: 1,
  paymentProvider: "mobile_money",
  firstName: "",
  lastName: "",
  email: "",
  phone: "",
});
const purchasing = ref(false);
const purchaseError = ref("");
const purchaseSuccess = ref("");

const PAYMENT_PROVIDERS = [
  { value: "mobile_money", label: "Orange Money / Mobile Money" },
  { value: "paypal", label: "Carte bancaire (PayPal)" },
  { value: "demo", label: "Mode démonstration" },
];

function eventQuery() {
  if (!event.value) return "";
  return [event.value.venue_name, event.value.venue_address, event.value.venue_city].filter(Boolean).join(", ");
}

function mapLinkUrl() {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(eventQuery())}`;
}

const minPrice = computed(() => {
  if (!ticketTypes.value.length) return null;
  return Math.min(...ticketTypes.value.map((t) => Number(t.price)));
});

function selectTicketType(id) {
  form.ticketType = id;
}

async function loadEvent() {
  loading.value = true;
  notFound.value = false;
  try {
    const [eventRes, typesRes] = await Promise.all([
      api.get(`/events/${props.eventId}/`),
      api.get("/tickets/types/marketplace/", { params: { event: props.eventId } }),
    ]);
    event.value = eventRes.data;
    ticketTypes.value = typesRes.data.results || typesRes.data;
    form.ticketType = ticketTypes.value[0]?.id || "";
    if (auth.isAuthenticated && auth.user) {
      form.firstName = auth.user.first_name || "";
      form.lastName = auth.user.last_name || "";
      form.email = auth.user.email || "";
      form.phone = auth.user.phone || "";
    }
  } catch (e) {
    notFound.value = true;
  } finally {
    loading.value = false;
  }
}

// La billetterie est consultable sans connexion ; l'achat, lui, exige un compte.
// Bouton "type=button" dédié (plutôt que de compter sur le submit) : sinon la
// validation HTML5 des champs "required", vides pour un invité, bloquerait le
// clic avant même d'atteindre cette redirection.
function goToLogin() {
  router.push({ name: "login", query: { next: route.fullPath } });
}

async function buyTicket() {
  purchaseError.value = "";
  if (!form.ticketType) {
    purchaseError.value = "Choisissez un type de billet.";
    return;
  }
  purchasing.value = true;
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
    purchaseSuccess.value = "Paiement confirmé — votre billet est prêt dans « Mes billets ».";
    const { data } = await api.get("/tickets/types/marketplace/", { params: { event: props.eventId } });
    ticketTypes.value = data.results || data;
  } catch (e) {
    const d = e?.response?.data;
    purchaseError.value = d?.detail || d?.non_field_errors?.[0] || "L'achat a échoué.";
  } finally {
    purchasing.value = false;
  }
}

onMounted(loadEvent);
</script>

<template>
  <div class="ie-public-tickets">
    <div v-if="loading" class="ie-skeleton" style="height: 420px; border-radius: 16px;"></div>

    <EmptyState v-else-if="notFound" icon="fa-solid fa-ticket" text="Cet événement n'est plus disponible à la billetterie." />

    <div v-else class="ie-ticket-page">
      <div class="ie-ticket-photo" :class="{ 'is-empty': !event.photo }">
        <img v-if="event.photo" :src="event.photo" :alt="event.title" class="ie-zoomable" @click="lightbox.open(event.photo, event.title)" />
        <i v-else class="fa-solid fa-calendar-week"></i>
        <span v-if="minPrice !== null" class="ie-ticket-price-badge">
          à partir de {{ minPrice.toLocaleString('fr-FR') }} {{ ticketTypes[0].currency }}
        </span>
      </div>

      <div class="ie-ticket-info">
        <span class="ie-ticket-eyebrow"><i class="fa-solid fa-calendar-check"></i> Billetterie InnovEvent</span>
        <h1>{{ event.title }}</h1>
        <p class="ie-ticket-desc">{{ event.description || "Aucune description fournie." }}</p>
        <div class="ie-ticket-meta">
          <span><i class="fa-solid fa-calendar-day"></i> {{ new Date(event.start_date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) }}</span>
          <span v-if="event.venue_name"><i class="fa-solid fa-location-dot"></i> {{ event.venue_name }}</span>
          <a v-if="event.venue_name" :href="mapLinkUrl()" target="_blank" rel="noopener" class="ie-ticket-itinerary">
            <i class="fa-solid fa-diamond-turn-right"></i> Voir l'itinéraire
          </a>
        </div>
      </div>

      <div class="ie-ticket-purchase ie-card">
        <h2>Réserver mes billets</h2>
        <p v-if="purchaseSuccess" class="ie-alert ie-alert-success">{{ purchaseSuccess }}</p>
        <template v-if="ticketTypes.length">
          <div class="ie-ticket-type-pills">
            <button
              v-for="tt in ticketTypes" :key="tt.id" type="button"
              class="ie-ticket-type-pill" :class="{ active: form.ticketType === tt.id }"
              @click="selectTicketType(tt.id)"
            >
              <i class="fa-solid fa-ticket"></i> {{ tt.name }} — {{ Number(tt.price).toLocaleString('fr-FR') }} {{ tt.currency }}
            </button>
          </div>

          <form class="ie-ticket-form" @submit.prevent="buyTicket">
            <div class="ie-form-row">
              <select v-model.number="form.quantity" class="ie-select">
                <option v-for="n in 10" :key="n" :value="n">{{ n }} billet{{ n > 1 ? 's' : '' }}</option>
              </select>
              <select v-model="form.paymentProvider" class="ie-select">
                <option v-for="p in PAYMENT_PROVIDERS" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </div>
            <div class="ie-form-row">
              <input v-model="form.firstName" class="ie-input" placeholder="Prénom" required />
              <input v-model="form.lastName" class="ie-input" placeholder="Nom" required />
            </div>
            <input v-model="form.email" type="email" class="ie-input" placeholder="Email" required />
            <input v-model="form.phone" class="ie-input" placeholder="Téléphone" required />

            <p v-if="purchaseError" class="ie-alert ie-alert-danger">{{ purchaseError }}</p>
            <p v-if="!auth.isAuthenticated" class="ie-ticket-login-hint">
              <i class="fa-solid fa-circle-info"></i> Connexion requise pour finaliser l'achat — vous reviendrez directement ici après connexion.
            </p>

            <button v-if="auth.isAuthenticated" class="ie-btn ie-btn-primary" type="submit" style="width: 100%;" :disabled="purchasing">
              <i class="fa-solid fa-lock"></i> {{ purchasing ? "Traitement…" : "Commander ce billet" }}
            </button>
            <button v-else class="ie-btn ie-btn-primary" type="button" style="width: 100%;" @click="goToLogin">
              <i class="fa-solid fa-lock"></i> Se connecter pour commander
            </button>
          </form>
        </template>
        <p v-else class="ie-empty-inline">Aucun billet disponible pour le moment.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-public-tickets { max-width: 760px; margin: 0 auto; }
.ie-ticket-page { display: flex; flex-direction: column; gap: 22px; }

.ie-ticket-photo {
  height: 260px; border-radius: 16px; overflow: hidden; position: relative;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-ticket-photo img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.ie-ticket-photo.is-empty i { font-size: 48px; color: var(--ie-navy); opacity: 0.3; }
.ie-ticket-price-badge {
  position: absolute; bottom: 14px; right: 14px;
  background: rgba(23, 27, 38, 0.82); color: #fff; font-size: 12.5px; font-weight: 700;
  padding: 7px 14px; border-radius: 999px;
}

.ie-ticket-eyebrow {
  font-size: 11px; font-weight: 800; letter-spacing: 0.06em; color: var(--ie-red);
  text-transform: uppercase; display: flex; align-items: center; gap: 6px; margin-bottom: 8px;
}
.ie-ticket-info h1 { font-size: 26px; color: var(--ie-navy); margin: 0 0 10px; }
.ie-ticket-desc { font-size: 14px; color: var(--ie-ink); line-height: 1.6; margin: 0 0 14px; }
.ie-ticket-meta { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ie-ink); }
.ie-ticket-meta i { color: var(--ie-red); width: 16px; }
.ie-ticket-itinerary { color: var(--ie-red); font-weight: 600; }

.ie-ticket-purchase { padding: 22px; }
.ie-ticket-purchase h2 { margin: 0 0 16px; font-size: 16px; }
.ie-ticket-type-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.ie-ticket-type-pill {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--ie-line); background: #fff; color: var(--ie-navy);
  font-size: 12.5px; font-weight: 600; padding: 8px 14px; border-radius: 999px; cursor: pointer;
}
.ie-ticket-type-pill.active { background: var(--ie-red); border-color: var(--ie-red); color: #fff; }
.ie-ticket-form { display: flex; flex-direction: column; gap: 12px; border-top: 1px solid var(--ie-line); padding-top: 16px; }
.ie-ticket-form .ie-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.ie-ticket-login-hint { font-size: 12px; color: var(--ie-muted); background: var(--ie-navy-soft); padding: 10px 12px; border-radius: 8px; margin: 0; }
.ie-empty-inline { font-size: 13px; color: var(--ie-muted); margin: 0; }

@media (max-width: 640px) {
  .ie-ticket-form .ie-form-row { grid-template-columns: 1fr; }
}
</style>
