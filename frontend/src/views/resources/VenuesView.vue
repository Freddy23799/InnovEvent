<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import SubscriptionCheckoutModal from "../../components/SubscriptionCheckoutModal.vue";
import { fetchMarketplaceFeatures, useFeatureFlags } from "../../composables/useFeatureFlags";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";
import { useMarketplaceAccessStore } from "../../stores/marketplaceAccess";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const lightbox = useLightboxStore();
const router = useRouter();

const auth = useAuthStore();
const canManage = computed(() => auth.role === "admin");

// Les salles rejoignent le même système d'abonnement que les autres
// marketplaces premium : un compte connecté (client/organisateur) non abonné
// au marketplace « Salles de réception » ne voit rien (le backend renvoie déjà
// une liste vide) — ce panneau explique pourquoi et propose l'abonnement.
// Un visiteur anonyme (page marketing publique) continue de tout voir.
const venuesFeatures = ref([]);
const { isVisible: isVenuesVisible } = useFeatureFlags(venuesFeatures);
const needsSubscription = computed(
  () => auth.isAuthenticated && !canManage.value && !isVenuesVisible("browse")
);
const subscriptionInfo = reactive({ plans: [], tiers: [], marketplace: null, price: 0, currency: "XAF" });
const checkoutOpen = ref(false);

async function loadVenuesAccess() {
  if (!auth.isAuthenticated || canManage.value) return;
  try {
    venuesFeatures.value = await fetchMarketplaceFeatures("venues");
  } catch (e) {
    venuesFeatures.value = [];
  }
  try {
    const { data } = await api.get("/marketplace/subscriptions/", { params: { marketplace_type: "venues" } });
    subscriptionInfo.plans = data.plans || [];
    subscriptionInfo.tiers = data.tiers || [];
    subscriptionInfo.price = data.price || 0;
    subscriptionInfo.currency = data.currency || "XAF";
    subscriptionInfo.marketplace = (data.marketplaces || []).find((m) => m.marketplace_type === "venues") || null;
  } catch (e) {
    // non bloquant : le bandeau d'abonnement se contente alors du statut "verrouillé"
  }
}

const marketplaceAccess = useMarketplaceAccessStore();

async function handleSubscribed() {
  checkoutOpen.value = false;
  await loadVenuesAccess();
  await loadVenues();
  await marketplaceAccess.refresh();
}
const canReview = computed(() => auth.role === "client" || auth.role === "organizer");
// Bouton visible même sans connexion : la garde de navigation redirige alors vers la connexion
// (redirection automatique vers cette page après authentification).
const canBook = computed(() => !auth.isAuthenticated || auth.role === "client" || auth.role === "organizer");
const canContactAdmin = computed(() => auth.isAuthenticated && auth.role !== "admin");

function goToBooking(venue) {
  router.push({ name: "bookings", query: { resource_type: "venue", resource_id: venue.id } });
}

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

const venues = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = {
  name: "", city: "", address: "", capacity: 0, price_per_day: 0, description: "", is_active: true,
  discount_percent: 0, discount_label: "", discount_valid_until: "",
};
const form = reactive({ ...emptyForm });

const expandedMapId = ref(null);

function toggleMap(venue) {
  expandedMapId.value = expandedMapId.value === venue.id ? null : venue.id;
}

const expandedReviewsId = ref(null);
const reviewsByVenue = reactive({});
const reviewSubmitting = ref(false);
const reviewError = ref("");
const reviewForm = reactive({ rating: 5, comment: "" });
const RATING_OPTIONS = [5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5];

function starIcons(rating) {
  const value = Number(rating) || 0;
  const icons = [];
  for (let i = 1; i <= 5; i++) {
    if (value >= i) icons.push("fa-solid fa-star");
    else if (value >= i - 0.5) icons.push("fa-solid fa-star-half-stroke");
    else icons.push("fa-regular fa-star");
  }
  return icons;
}

function myReview(venueId) {
  const list = reviewsByVenue[venueId] || [];
  return list.find((r) => r.author === auth.user?.id) || null;
}

async function toggleReviews(venue) {
  if (expandedReviewsId.value === venue.id) {
    expandedReviewsId.value = null;
    return;
  }
  expandedReviewsId.value = venue.id;
  reviewError.value = "";
  if (!reviewsByVenue[venue.id]) {
    const { data } = await api.get("/reviews/venues/", { params: { venue: venue.id } });
    reviewsByVenue[venue.id] = data.results || data;
  }
  const mine = myReview(venue.id);
  reviewForm.rating = mine ? Number(mine.rating) : 5;
  reviewForm.comment = mine ? mine.comment : "";
}

async function submitReview(venue) {
  reviewError.value = "";
  reviewSubmitting.value = true;
  try {
    const mine = myReview(venue.id);
    if (mine) {
      await api.patch(`/reviews/venues/${mine.id}/`, { rating: reviewForm.rating, comment: reviewForm.comment });
    } else {
      await api.post("/reviews/venues/", { venue: venue.id, rating: reviewForm.rating, comment: reviewForm.comment });
    }
    const { data } = await api.get("/reviews/venues/", { params: { venue: venue.id } });
    reviewsByVenue[venue.id] = data.results || data;
    await loadVenues();
  } catch (e) {
    reviewError.value = e?.response?.data?.detail?.non_field_errors?.[0] || e?.response?.data?.detail || "Impossible d'enregistrer votre avis.";
  } finally {
    reviewSubmitting.value = false;
  }
}

async function deleteMyReview(venue) {
  const mine = myReview(venue.id);
  if (!mine || !confirm("Supprimer votre avis ?")) return;
  await api.delete(`/reviews/venues/${mine.id}/`);
  reviewsByVenue[venue.id] = (reviewsByVenue[venue.id] || []).filter((r) => r.id !== mine.id);
  reviewForm.rating = 5;
  reviewForm.comment = "";
  await loadVenues();
}

function venueQuery(venue) {
  return [venue.name, venue.address, venue.city].filter(Boolean).join(", ");
}

function mapEmbedUrl(venue) {
  return `https://www.google.com/maps?q=${encodeURIComponent(venueQuery(venue))}&output=embed`;
}

function mapLinkUrl(venue) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(venueQuery(venue))}`;
}

function formatSlot(slot) {
  const opts = { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
  const start = new Date(slot.start).toLocaleString("fr-FR", opts);
  const end = new Date(slot.end).toLocaleString("fr-FR", opts);
  return `${start} → ${end}`;
}

async function loadVenues() {
  loading.value = true;
  try {
    const { data } = await api.get("/venues/");
    venues.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(venue) {
  Object.assign(form, venue);
  editingId.value = venue.id;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  // discount_valid_until est un DateField côté API : une chaîne vide est rejetée
  // (400), il faut soit null (JSON), soit omettre le champ (FormData).
  const base = { ...form, discount_valid_until: form.discount_valid_until || null };
  if (!photoFile.value) return base;
  const payload = new FormData();
  Object.entries(base).forEach(([key, value]) => {
    if (key === "discount_valid_until" && !value) return;
    payload.append(key, value);
  });
  payload.append("photo", photoFile.value);
  return payload;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/venues/${editingId.value}/`, payload);
    } else {
      await api.post("/venues/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Salle enregistrée.");
    await loadVenues();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette salle.";
  } finally {
    submitting.value = false;
  }
}

async function deleteVenue(venue) {
  if (!confirm(`Supprimer la salle « ${venue.name} » ?`)) return;
  await api.delete(`/venues/${venue.id}/`);
  await loadVenues();
}

onMounted(() => {
  loadVenues();
  loadVenuesAccess();
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-building-columns" style="color: var(--ie-red); margin-right: 8px;"></i>Salles</h1>
        <p class="ie-page-subtitle">Catalogue des salles disponibles pour vos événements.</p>
      </div>
      <div class="ie-page-header-actions">
        <button v-if="canManage" class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle salle" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Ville</label>
            <input v-model="form.city" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Adresse</label>
        <input v-model="form.address" class="ie-input" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Capacité</label>
            <input v-model.number="form.capacity" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Tarif / jour (XAF)</label>
            <input v-model.number="form.price_per_day" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Salle active (disponible aux réservations)
        </label>
        <div class="ie-discount-fieldset">
          <p class="ie-discount-fieldset-title"><i class="fa-solid fa-tag"></i> Offre promotionnelle (optionnel)</p>
          <div class="ie-form-row">
            <div>
              <label class="ie-label">Réduction (%)</label>
              <input v-model.number="form.discount_percent" type="number" min="0" max="90" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Libellé de l'offre</label>
              <input v-model="form.discount_label" class="ie-input" placeholder="Ex: Offre de rentrée" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 10px;">Valable jusqu'au</label>
          <input v-model="form.discount_valid_until" type="date" class="ie-input" />
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div v-if="loading" class="ie-catalog-grid">
      <div v-for="i in 3" :key="i" class="ie-card ie-catalog-card">
        <div class="ie-skeleton" style="height: 150px; border-radius: 0;"></div>
        <div class="ie-card-body">
          <div class="ie-skeleton" style="height: 14px; width: 60%; margin-bottom: 8px;"></div>
          <div class="ie-skeleton" style="height: 12px; width: 90%;"></div>
        </div>
      </div>
    </div>

    <div v-else-if="venues.length" class="ie-catalog-grid">
      <div v-for="venue in venues" :key="venue.id" class="ie-card ie-catalog-card">
        <div class="ie-catalog-photo">
          <img v-if="venue.photo" :src="venue.photo" :alt="venue.name" class="ie-zoomable" @click="lightbox.open(venue.photo, venue.name)" />
          <i v-else class="fa-solid fa-building-columns"></i>
          <span class="ie-badge ie-catalog-availability" :class="venue.is_available ? 'ie-badge-success' : 'ie-badge-danger'">
            {{ venue.is_available ? "Disponible" : "Occupée actuellement" }}
          </span>
          <div v-if="venue.has_active_discount" class="ie-catalog-discount-badge">
            <span class="ie-catalog-discount-percent">-{{ venue.discount_percent }}%</span>
            <span v-if="venue.discount_label" class="ie-catalog-discount-label">{{ venue.discount_label }}</span>
          </div>
        </div>
        <div class="ie-card-body">
          <h3 class="ie-catalog-title">{{ venue.name }}</h3>
          <div class="ie-rating-line">
            <span class="ie-rating-stars">
              <i v-for="(icon, i) in starIcons(venue.average_rating)" :key="i" :class="icon"></i>
            </span>
            <span v-if="venue.review_count" class="ie-rating-count">{{ venue.average_rating }} ({{ venue.review_count }} avis)</span>
            <span v-else class="ie-rating-count">Aucun avis</span>
          </div>
          <p class="ie-catalog-desc">{{ venue.description || "Aucune description fournie." }}</p>
          <div class="ie-catalog-meta">
            <span v-if="venue.city"><i class="fa-solid fa-location-dot"></i> {{ venue.city }}</span>
            <span><i class="fa-solid fa-people-group"></i> Capacité : {{ venue.capacity }}</span>
            <span v-if="!venue.has_active_discount"><i class="fa-solid fa-coins"></i> {{ Number(venue.price_per_day).toLocaleString('fr-FR') }} XAF / jour</span>
            <span v-else class="ie-catalog-price-line">
              <i class="fa-solid fa-coins"></i>
              <span class="ie-catalog-price-original">{{ Number(venue.price_per_day).toLocaleString('fr-FR') }} XAF</span>
              <span class="ie-catalog-price-discounted">{{ Number(venue.discounted_price_per_day).toLocaleString('fr-FR') }} XAF / jour</span>
            </span>
            <span v-if="venue.has_active_discount && venue.discount_valid_until" class="ie-catalog-discount-until">
              <i class="fa-solid fa-hourglass-half"></i> Offre valable jusqu'au {{ new Date(venue.discount_valid_until).toLocaleDateString('fr-FR') }}
            </span>
          </div>
          <div v-if="venue.upcoming_unavailability?.length" class="ie-catalog-unavail">
            <span class="ie-catalog-unavail-label"><i class="fa-solid fa-calendar-xmark"></i> Prochaines indisponibilités</span>
            <span v-for="(slot, i) in venue.upcoming_unavailability" :key="i" class="ie-catalog-unavail-slot">{{ formatSlot(slot) }}</span>
          </div>
          <button v-if="canBook" class="ie-btn ie-btn-primary ie-btn-sm" style="width: 100%; margin-top: 10px;" @click="goToBooking(venue)">
            <i class="fa-solid fa-calendar-plus"></i> Réserver cette salle
          </button>
          <button class="ie-btn ie-btn-ghost ie-btn-sm" style="width: 100%; margin-top: 4px;" @click="toggleMap(venue)">
            <i class="fa-solid fa-map-location-dot"></i> {{ expandedMapId === venue.id ? "Masquer la carte" : "Voir sur la carte" }}
          </button>
          <div v-if="expandedMapId === venue.id" class="ie-venue-map">
            <iframe
              :src="mapEmbedUrl(venue)"
              width="100%"
              height="220"
              style="border:0;"
              loading="lazy"
              referrerpolicy="no-referrer-when-downgrade"
            ></iframe>
            <a :href="mapLinkUrl(venue)" target="_blank" rel="noopener" class="ie-venue-map-link">
              <i class="fa-solid fa-up-right-from-square"></i> Ouvrir dans Google Maps
            </a>
          </div>
          <button v-if="auth.isAuthenticated" class="ie-btn ie-btn-ghost ie-btn-sm" style="width: 100%; margin-top: 6px;" @click="toggleReviews(venue)">
            <i class="fa-solid fa-comment-dots"></i> {{ expandedReviewsId === venue.id ? "Masquer les avis" : "Voir les avis" }}
          </button>
          <div v-if="expandedReviewsId === venue.id" class="ie-reviews-panel">
            <div v-if="!(reviewsByVenue[venue.id] || []).length" class="ie-reviews-empty">Aucun avis pour le moment.</div>
            <div v-for="review in reviewsByVenue[venue.id] || []" :key="review.id" class="ie-review-item">
              <div class="ie-review-head">
                <strong>{{ review.author_name }}</strong>
                <span class="ie-rating-stars ie-rating-stars-sm">
                  <i v-for="(icon, i) in starIcons(review.rating)" :key="i" :class="icon"></i>
                </span>
              </div>
              <p v-if="review.comment" class="ie-review-comment">{{ review.comment }}</p>
              <span class="ie-review-date">{{ new Date(review.created_at).toLocaleDateString('fr-FR') }}</span>
            </div>

            <div v-if="canReview" class="ie-review-form">
              <label class="ie-label">{{ myReview(venue.id) ? "Modifier mon avis" : "Laisser un avis" }}</label>
              <select v-model.number="reviewForm.rating" class="ie-select">
                <option v-for="opt in RATING_OPTIONS" :key="opt" :value="opt">{{ opt }} ★</option>
              </select>
              <textarea v-model="reviewForm.comment" class="ie-input" rows="2" placeholder="Votre commentaire (optionnel)" style="margin-top: 8px;"></textarea>
              <p v-if="reviewError" class="ie-alert ie-alert-danger" style="margin-top: 8px;">{{ reviewError }}</p>
              <div class="ie-table-actions" style="margin-top: 8px;">
                <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="reviewSubmitting" @click="submitReview(venue)">
                  {{ reviewSubmitting ? "Envoi…" : myReview(venue.id) ? "Mettre à jour" : "Publier" }}
                </button>
                <button v-if="myReview(venue.id)" class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteMyReview(venue)">Supprimer</button>
              </div>
            </div>
          </div>
          <button v-if="canContactAdmin" class="ie-btn ie-btn-ghost ie-btn-sm" style="width: 100%; margin-top: 6px;" :disabled="contactingAdmin" @click="contactAdmin">
            <i class="fa-solid fa-headset"></i> {{ contactingAdmin ? "Connexion…" : "Contacter l'administration" }}
          </button>
          <div v-if="canManage" class="ie-table-actions" style="margin-top: 14px;">
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(venue)">Modifier</button>
            <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteVenue(venue)">Supprimer</button>
          </div>
        </div>
      </div>
    </div>
    <EmptyState
      v-else-if="needsSubscription"
      icon="fa-solid fa-lock"
      text="Abonnez-vous au marketplace « Salles de réception » pour consulter et réserver nos salles."
    >
      <p v-if="subscriptionInfo.plans.length" class="ie-field-hint">À partir de {{ Number(subscriptionInfo.plans[0].price).toLocaleString('fr-FR') }} {{ subscriptionInfo.currency }}.</p>
      <p v-else class="ie-field-hint">Aucune formule tarifaire n’est configurée pour ce Marketplace.</p>
      <button type="button" class="ie-btn ie-btn-primary" :disabled="!subscriptionInfo.plans.length" @click="checkoutOpen = true">
        <i class="fa-solid fa-lock-open"></i> {{ subscriptionInfo.plans.length ? "S'abonner" : "Tarif non configuré" }}
      </button>
    </EmptyState>
    <EmptyState v-else icon="fa-solid fa-building" text="Aucune salle enregistrée." />

    <SubscriptionCheckoutModal
      v-if="checkoutOpen"
      marketplace-type="venues"
      marketplace-label="Salles de réception"
      :plans="subscriptionInfo.plans"
      :tiers="subscriptionInfo.tiers"
      @close="checkoutOpen = false"
      @subscribed="handleSubscribed"
    />
  </div>
</template>

<style scoped>
.ie-catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }
.ie-catalog-card { overflow: hidden; display: flex; flex-direction: column; }
.ie-catalog-photo {
  height: 150px; background: var(--ie-navy-soft); position: relative;
  display: flex; align-items: center; justify-content: center;
}
.ie-catalog-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-catalog-photo i { font-size: 36px; color: var(--ie-navy); opacity: 0.35; }
.ie-catalog-availability { position: absolute; top: 10px; right: 10px; }
.ie-catalog-title { margin: 0 0 6px; font-size: 14.5px; color: var(--ie-navy); }
.ie-catalog-desc { font-size: 12.5px; color: var(--ie-muted); margin: 0 0 12px; line-height: 1.5; min-height: 36px; }
.ie-catalog-meta { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--ie-ink); }
.ie-catalog-meta i { color: var(--ie-red); width: 14px; }
.ie-venue-map { margin-top: 10px; border: 1px solid var(--ie-line); border-radius: 8px; overflow: hidden; }
.ie-venue-map-link {
  display: block; text-align: center; padding: 8px; font-size: 11.5px;
  color: var(--ie-navy); background: #fafbfc; border-top: 1px solid var(--ie-line);
}
.ie-venue-map-link:hover { color: var(--ie-red); }

.ie-rating-line { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ie-rating-stars { color: #F5A623; font-size: 13px; letter-spacing: 1px; }
.ie-rating-stars-sm { font-size: 11px; }
.ie-rating-count { font-size: 11.5px; color: var(--ie-muted); }

.ie-reviews-panel {
  margin-top: 10px; padding: 12px; border: 1px solid var(--ie-line); border-radius: 8px;
  background: #fafbfc; display: flex; flex-direction: column; gap: 10px;
}
.ie-reviews-empty { font-size: 12px; color: var(--ie-muted); }
.ie-review-item { border-bottom: 1px solid var(--ie-line); padding-bottom: 8px; }
.ie-review-item:last-of-type { border-bottom: none; padding-bottom: 0; }
.ie-review-head { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; }
.ie-review-comment { font-size: 12px; color: var(--ie-ink); margin: 4px 0; }
.ie-review-date { font-size: 10.5px; color: var(--ie-muted); }
.ie-review-form { border-top: 1px dashed var(--ie-line); padding-top: 10px; }
</style>
