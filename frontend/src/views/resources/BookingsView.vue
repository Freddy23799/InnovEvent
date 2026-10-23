<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import BookingCheckoutModal from "../../components/BookingCheckoutModal.vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const STATUS_BADGE = { pending: "ie-badge-warning", confirmed: "ie-badge-success", cancelled: "ie-badge-danger" };
const STATUS_LABELS = { pending: "En attente", confirmed: "Confirmée", cancelled: "Annulée" };

const bookings = ref([]);
const events = ref([]);
const venues = ref([]);
const providers = ref([]);
const equipment = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");

// Le paiement se fait désormais dans une fenêtre dédiée (mêmes moyens de
// paiement que la Marketplace : MTN/Orange Money, carte, PayPal), ouverte
// automatiquement juste après la création d'une réservation à tarification
// numérique — ou depuis le bouton « Payer » pour une réservation déjà en
// attente.
const checkoutBooking = ref(null);

const emptyForm = {
  event: "", resource_type: "venue", venue: "", provider: "", equipment: "",
  quantity: 1, start_datetime: "", end_datetime: "", notes: "",
};
const form = reactive({ ...emptyForm });

// Ressource choisie depuis un catalogue (« Réserver cette salle »…) : elle est
// verrouillée et affichée en récapitulatif, le client n'a plus à la
// re-sélectionner dans une liste (paginée, donc parfois incomplète).
const RESOURCE_ENDPOINTS = { venue: "/venues/", provider: "/providers/", equipment: "/equipment/" };
const LOCKED_RESOURCE_LABELS = { venue: "Salle sélectionnée", provider: "Prestataire sélectionné", equipment: "Matériel sélectionné" };
const LOCKED_RESOURCE_ICONS = { venue: "fa-building-columns", provider: "fa-user-tie", equipment: "fa-box-open" };
const lockedResource = ref(null);

const lockedResourceDetails = computed(() => {
  const item = lockedResource.value;
  if (!item) return [];
  if (form.resource_type === "venue") {
    return [
      item.city && `${item.address ? item.address + ", " : ""}${item.city}`,
      item.capacity && `${item.capacity} personnes`,
      item.price_per_day && `${Number(item.discounted_price_per_day || item.price_per_day).toLocaleString("fr-FR")} XAF / jour`,
    ].filter(Boolean);
  }
  if (form.resource_type === "equipment") {
    return [item.category, item.price_per_unit && `${Number(item.discounted_price_per_unit || item.price_per_unit).toLocaleString("fr-FR")} XAF / unité`].filter(Boolean);
  }
  return [item.category, item.city, item.price_range].filter(Boolean);
});

const resourceOptions = computed(() => {
  if (form.resource_type === "venue") return venues.value;
  if (form.resource_type === "provider") return providers.value;
  if (form.resource_type === "equipment") return equipment.value;
  return [];
});

async function loadAll() {
  loading.value = true;
  try {
    const [bookingsRes, eventsRes, venuesRes, providersRes, equipmentRes] = await Promise.all([
      api.get("/bookings/"),
      api.get("/events/"),
      api.get("/venues/", { params: { is_active: true } }),
      api.get("/providers/", { params: { is_active: true } }),
      api.get("/equipment/", { params: { is_active: true } }),
    ]);
    bookings.value = bookingsRes.data.results || bookingsRes.data;
    events.value = eventsRes.data.results || eventsRes.data;
    venues.value = venuesRes.data.results || venuesRes.data;
    providers.value = providersRes.data.results || providersRes.data;
    equipment.value = equipmentRes.data.results || equipmentRes.data;
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  Object.assign(form, emptyForm);
  lockedResource.value = null;
  errorMessage.value = "";
}

async function lockResource(resourceType, resourceId) {
  const endpoint = RESOURCE_ENDPOINTS[resourceType];
  if (!endpoint) return;
  const id = Number(resourceId);
  const fromList = { venue: venues, provider: providers, equipment: equipment }[resourceType].value.find((r) => r.id === id);
  try {
    lockedResource.value = fromList || (await api.get(`${endpoint}${id}/`)).data;
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Cette ressource n'est pas disponible à la réservation.");
    return;
  }
  Object.assign(form, emptyForm, { resource_type: resourceType, [resourceType]: id });
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  const payload = {
    event: form.event,
    resource_type: form.resource_type,
    start_datetime: form.start_datetime,
    end_datetime: form.end_datetime,
    notes: form.notes,
    venue: form.resource_type === "venue" ? form.venue : null,
    provider: form.resource_type === "provider" ? form.provider : null,
    equipment: form.resource_type === "equipment" ? form.equipment : null,
    quantity: form.resource_type === "equipment" ? form.quantity : 1,
  };
  try {
    const { data } = await api.post("/bookings/", payload);
    showForm.value = false;
    resetForm();
    await loadAll();
    if (data.estimated_cost !== null) {
      // Tarification numérique (salle, matériel) : on enchaîne directement
      // sur le paiement, comme sur la Marketplace, plutôt que de laisser la
      // réservation « en attente » sans étape suivante visible.
      checkoutBooking.value = bookings.value.find((b) => b.id === data.id) || data;
    } else {
      toast.success("Réservation enregistrée — en attente de devis du prestataire.");
    }
  } catch (e) {
    const data = e?.response?.data;
    errorMessage.value = data?.detail?.non_field_errors?.[0] || data?.detail || "Conflit ou erreur de validation.";
  } finally {
    submitting.value = false;
  }
}

async function cancelBooking(booking) {
  if (!confirm("Annuler cette réservation ?")) return;
  await api.patch(`/bookings/${booking.id}/`, { status: "cancelled" });
  await loadAll();
}

function openPayment(booking) {
  checkoutBooking.value = booking;
}

async function handleBookingPaid(updatedBooking) {
  checkoutBooking.value = null;
  toast.success("Paiement confirmé, réservation validée.");
  await loadAll();
}

const creatingDeliveryForId = ref(null);
const deliveryForm = reactive({ destination_address: "", scheduled_date: "" });
const deliverySubmitting = ref(false);

function openCreateDelivery(booking) {
  creatingDeliveryForId.value = booking.id;
  deliveryForm.destination_address = "";
  deliveryForm.scheduled_date = "";
}

async function confirmCreateDelivery(booking) {
  deliverySubmitting.value = true;
  try {
    const { data } = await api.post("/deliveries/create-from-booking/", {
      booking: booking.id,
      destination_address: deliveryForm.destination_address,
      scheduled_date: deliveryForm.scheduled_date || null,
    });
    creatingDeliveryForId.value = null;
    toast.success("Livraison créée.");
    router.push({ name: "delivery-detail", params: { id: data.id } });
  } catch (e) {
    toast.error(e?.response?.data?.detail || e?.response?.data?.non_field_errors?.[0] || "Impossible de créer cette livraison.");
  } finally {
    deliverySubmitting.value = false;
  }
}

async function downloadReceipt(booking) {
  const response = await api.get(`/bookings/${booking.id}/receipt/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `recu-reservation-${booking.id}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

onMounted(async () => {
  await loadAll();
  const { resource_type, resource_id, quantity } = route.query;
  if (resource_type && resource_id) {
    router.replace({ query: {} });
    await lockResource(resource_type, resource_id);
    form.quantity = quantity ? Number(quantity) : 1;
  }
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-check" style="color: var(--ie-red); margin-right: 8px;"></i>Réservations</h1>
        <p class="ie-page-subtitle">Salles, prestataires et matériel réservés pour vos événements.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : (resetForm(), (showForm = true))">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle réservation" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Événement</label>
            <select v-model="form.event" class="ie-select" required>
              <option value="" disabled>Choisir un événement</option>
              <option v-for="ev in events" :key="ev.id" :value="ev.id">{{ ev.title }}</option>
            </select>
          </div>
          <div v-if="!lockedResource">
            <label class="ie-label">Type de ressource</label>
            <select v-model="form.resource_type" class="ie-select">
              <option value="venue">Salle</option>
              <option value="provider">Prestataire</option>
              <option value="equipment">Matériel</option>
            </select>
          </div>
        </div>

        <div v-if="lockedResource" class="ie-booking-locked">
          <img v-if="lockedResource.photo" :src="lockedResource.photo" :alt="lockedResource.name" class="ie-booking-locked-photo" />
          <div v-else class="ie-booking-locked-photo ie-booking-locked-placeholder"><i class="fa-solid" :class="LOCKED_RESOURCE_ICONS[form.resource_type]"></i></div>
          <div>
            <span class="ie-booking-locked-type">{{ LOCKED_RESOURCE_LABELS[form.resource_type] }}</span>
            <strong class="ie-booking-locked-name">{{ lockedResource.name }}</strong>
            <span v-for="detail in lockedResourceDetails" :key="detail" class="ie-booking-locked-detail">{{ detail }}</span>
          </div>
        </div>
        <template v-else>
          <label class="ie-label" style="margin-top: 14px;">Ressource</label>
          <select v-model="form[form.resource_type]" class="ie-select" required>
            <option value="" disabled>Choisir…</option>
            <option v-for="res in resourceOptions" :key="res.id" :value="res.id">{{ res.name }}</option>
          </select>
        </template>

        <div v-if="form.resource_type === 'equipment'" style="margin-top: 14px;">
          <label class="ie-label">Quantité</label>
          <input v-model.number="form.quantity" type="number" min="1" class="ie-input" />
        </div>

        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Début</label>
            <input v-model="form.start_datetime" type="datetime-local" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Fin</label>
            <input v-model="form.end_datetime" type="datetime-local" class="ie-input" required />
          </div>
        </div>

        <label class="ie-label" style="margin-top: 14px;">Notes</label>
        <textarea v-model="form.notes" class="ie-input" rows="2"></textarea>

        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Vérification des conflits…" : "Réserver" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="bookings.length">
        <table class="ie-table">
          <thead>
            <tr><th>Événement</th><th>Ressource</th><th>Début</th><th>Fin</th><th class="ie-num">Coût</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <template v-for="booking in bookings" :key="booking.id">
              <tr>
                <td><strong>{{ booking.event_title }}</strong></td>
                <td>{{ booking.resource_label }}</td>
                <td>{{ new Date(booking.start_datetime).toLocaleString('fr-FR') }}</td>
                <td>{{ new Date(booking.end_datetime).toLocaleString('fr-FR') }}</td>
                <td class="ie-num">
                  {{ booking.estimated_cost !== null ? Number(booking.estimated_cost).toLocaleString('fr-FR') + " XAF" : "Sur devis" }}
                </td>
                <td><span class="ie-badge" :class="STATUS_BADGE[booking.status] || 'ie-badge-neutral'">{{ STATUS_LABELS[booking.status] || booking.status }}</span></td>
                <td class="ie-table-actions">
                  <button
                    v-if="booking.status === 'pending' && booking.estimated_cost !== null"
                    class="ie-btn ie-btn-primary ie-btn-sm"
                    @click="openPayment(booking)"
                  >
                    <i class="fa-solid fa-credit-card"></i> Payer
                  </button>
                  <button
                    v-if="booking.payment_status === 'completed'"
                    class="ie-btn ie-btn-secondary ie-btn-sm"
                    @click="downloadReceipt(booking)"
                  >
                    <i class="fa-solid fa-download"></i> Reçu
                  </button>
                  <button v-if="booking.status !== 'cancelled'" class="ie-btn ie-btn-danger ie-btn-sm" @click="cancelBooking(booking)">Annuler</button>
                  <button
                    v-if="auth.role === 'admin' && booking.status !== 'cancelled'"
                    class="ie-btn ie-btn-ghost ie-btn-sm"
                    @click="openCreateDelivery(booking)"
                  >
                    <i class="fa-solid fa-truck"></i> Créer une livraison
                  </button>
                </td>
              </tr>
              <tr v-if="creatingDeliveryForId === booking.id">
                <td colspan="7" style="background: #fafbfc;">
                  <div style="display:flex; align-items:center; gap:12px; flex-wrap: wrap; padding: 6px 0;">
                    <strong style="font-size: 13px;">Nouvelle livraison pour « {{ booking.resource_label }} » :</strong>
                    <input v-model="deliveryForm.destination_address" class="ie-input" placeholder="Adresse de destination" style="width: 260px;" />
                    <input v-model="deliveryForm.scheduled_date" type="date" class="ie-input" style="width: 160px;" />
                    <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="deliverySubmitting" @click="confirmCreateDelivery(booking)">
                      {{ deliverySubmitting ? "Création…" : "Créer" }}
                    </button>
                    <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="creatingDeliveryForId = null">Annuler</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-calendar-check" text="Aucune réservation pour le moment." />
    </div>

    <BookingCheckoutModal
      v-if="checkoutBooking"
      :booking="checkoutBooking"
      @close="checkoutBooking = null"
      @paid="handleBookingPaid"
    />
  </div>
</template>

<style scoped>
.ie-booking-locked { display: flex; align-items: center; gap: 14px; margin-top: 14px; padding: 12px; border: 1px solid var(--ie-border, #e3e6ea); border-radius: 12px; background: #fafbfc; }
.ie-booking-locked-photo { width: 88px; height: 66px; flex: 0 0 88px; border-radius: 8px; object-fit: cover; }
.ie-booking-locked-placeholder { display: grid; place-items: center; background: #eef0f2; color: #9aa3ac; font-size: 22px; }
.ie-booking-locked-type { display: block; color: var(--ie-muted); font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.ie-booking-locked-name { display: block; margin: 2px 0 4px; color: var(--ie-ink); font-size: 15px; }
.ie-booking-locked-detail { display: inline-block; margin-right: 12px; color: #3c4b5b; font-size: 12px; }
</style>
