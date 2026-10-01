<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import StarRating from "../../components/StarRating.vue";
import { useFeatureFlags } from "../../composables/useFeatureFlags";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";

const props = defineProps({ id: { type: [String, Number], required: true } });
const router = useRouter();
const auth = useAuthStore();

const loading = ref(true);
const notFound = ref(false);
const profile = ref(null);
const features = computed(() => profile.value?.features || []);
const { isVisible, isUsable, upsellMessage } = useFeatureFlags(features);

// --- Disponibilités (lecture seule) ---
const availCursor = ref(new Date());
const availMonthData = ref({});
const availLoading = ref(false);
const availMonthLabel = computed(() => availCursor.value.toLocaleDateString("fr-FR", { month: "long", year: "numeric" }));
const availWeeks = computed(() => {
  const year = availCursor.value.getFullYear();
  const month = availCursor.value.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let day = 1; day <= daysInMonth; day++) cells.push(new Date(year, month, day));
  while (cells.length % 7 !== 0) cells.push(null);
  const result = [];
  for (let i = 0; i < cells.length; i += 7) result.push(cells.slice(i, i + 7));
  return result;
});
function availStatusFor(date) {
  if (!date) return null;
  return availMonthData.value[date.toISOString().slice(0, 10)] || null;
}
async function loadAvailabilityMonth() {
  if (!isUsable("availability_calendar")) return;
  availLoading.value = true;
  try {
    const { data } = await api.get(`/marketplace/profiles/${props.id}/availability/`, {
      params: { year: availCursor.value.getFullYear(), month: availCursor.value.getMonth() + 1 },
    });
    availMonthData.value = data;
  } finally {
    availLoading.value = false;
  }
}
function changeAvailMonth(delta) {
  availCursor.value = new Date(availCursor.value.getFullYear(), availCursor.value.getMonth() + delta, 1);
  loadAvailabilityMonth();
}

const reviews = ref([]);
const reviewsLoading = ref(false);
const reviewForm = reactive({ rating: 5, comment: "" });
const reviewSubmitting = ref(false);
const reviewError = ref("");

const specialtiesList = computed(() =>
  (profile.value?.specialties || "").split(",").map((s) => s.trim()).filter(Boolean)
);

const myReview = computed(() =>
  reviews.value.find((r) => r.author === auth.user?.id)
);

// --- Demande de devis via la plateforme : aucune coordonnée du prestataire
// n'est jamais affichée ici — le prestataire répond par un devis structuré,
// entièrement au sein de l'application.
const bookingForm = reactive({
  service: "", event_type: "", event_date: "", event_time: "", location: "", city: profile.value?.city || "",
  guest_count: null, budget_estimate: null, options_wanted: "", contact_phone: auth.user?.phone || "", message: "",
});
const bookingSubmitting = ref(false);
const bookingError = ref("");
const bookingSent = ref(false);
const bookingPanelRef = ref(null);

// --- Matériel souhaité (facultatif) : le client peut joindre une liste de
// matériel (chaises, tables, projecteur...) à sa demande de devis, plutôt que
// de le décrire en texte libre — le prestataire voit ainsi précisément ce
// qui est attendu dès la demande, catalogue réutilisé (apps.equipment).
const equipmentCatalog = ref([]);
const requestedItems = reactive([{ equipment: "", quantity: 1 }]);

async function loadEquipmentCatalog() {
  try {
    const { data } = await api.get("/equipment/");
    equipmentCatalog.value = data.results || data;
  } catch {
    equipmentCatalog.value = [];
  }
}

function addRequestedItem() {
  requestedItems.push({ equipment: "", quantity: 1 });
}
function removeRequestedItem(index) {
  requestedItems.splice(index, 1);
}

function requestService(service) {
  bookingForm.service = service.id;
  bookingSent.value = false;
  bookingPanelRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function submitBooking() {
  bookingError.value = "";
  bookingSubmitting.value = true;
  try {
    const requested_equipment = requestedItems
      .filter((item) => item.equipment)
      .map((item) => ({ equipment: item.equipment, quantity: item.quantity || 1 }));
    await api.post("/marketplace/booking-requests/", {
      profile: props.id,
      service: bookingForm.service || null,
      event_type: bookingForm.event_type,
      event_date: bookingForm.event_date || null,
      event_time: bookingForm.event_time || null,
      location: bookingForm.location,
      city: bookingForm.city,
      guest_count: bookingForm.guest_count || null,
      budget_estimate: bookingForm.budget_estimate || null,
      options_wanted: bookingForm.options_wanted,
      contact_phone: bookingForm.contact_phone,
      message: bookingForm.message,
      requested_equipment,
    });
    bookingSent.value = true;
    bookingForm.message = "";
    requestedItems.splice(0, requestedItems.length, { equipment: "", quantity: 1 });
  } catch (e) {
    bookingError.value = e?.response?.data?.detail || "Impossible d'envoyer votre demande pour le moment.";
  } finally {
    bookingSubmitting.value = false;
  }
}

async function loadProfile() {
  loading.value = true;
  notFound.value = false;
  try {
    const { data } = await api.get(`/marketplace/profiles/${props.id}/`);
    profile.value = data;
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
  } finally {
    loading.value = false;
  }
}

async function loadReviews() {
  reviewsLoading.value = true;
  try {
    const { data } = await api.get("/reviews/professionals/", { params: { profile: props.id } });
    reviews.value = data.results || data;
  } finally {
    reviewsLoading.value = false;
  }
}

async function submitReview() {
  reviewError.value = "";
  reviewSubmitting.value = true;
  try {
    const { data } = await api.post("/reviews/professionals/", {
      profile: props.id, rating: reviewForm.rating, comment: reviewForm.comment,
    });
    reviews.value.unshift(data);
    reviewForm.comment = "";
    reviewForm.rating = 5;
  } catch (e) {
    reviewError.value = e?.response?.data?.non_field_errors?.[0] || e?.response?.data?.detail || "Impossible d'envoyer votre avis.";
  } finally {
    reviewSubmitting.value = false;
  }
}

function goBack() {
  router.push({ name: "premium-marketplace" });
}

const favoriteBusy = ref(false);
async function toggleFavorite() {
  favoriteBusy.value = true;
  try {
    if (profile.value.is_favorited) {
      await api.delete(`/marketplace/favorites/by-profile/${profile.value.id}/`);
      profile.value.is_favorited = false;
    } else {
      await api.post("/marketplace/favorites/", { profile: profile.value.id });
      profile.value.is_favorited = true;
    }
  } finally {
    favoriteBusy.value = false;
  }
}

const contactBusy = ref(false);
async function contactProvider() {
  contactBusy.value = true;
  try {
    const { data } = await api.post("/messaging/conversations/contact-provider/", { profile: profile.value.id });
    router.push({ name: "messaging", query: { conversation: data.id } });
  } finally {
    contactBusy.value = false;
  }
}

onMounted(async () => {
  await loadProfile();
  if (profile.value) {
    await loadReviews();
    await loadAvailabilityMonth();
    await loadEquipmentCatalog();
  }
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div class="ie-page-header-actions">
        <button type="button" class="ie-btn ie-btn-ghost" @click="goBack">
          <i class="fa-solid fa-arrow-left"></i> Retour au marketplace
        </button>
        <button
          v-if="profile && isUsable('favorites')" type="button" class="ie-btn ie-btn-ghost"
          :class="{ 'ie-favorited': profile.is_favorited }" :disabled="favoriteBusy" @click="toggleFavorite"
        >
          <i :class="profile.is_favorited ? 'fa-solid fa-heart' : 'fa-regular fa-heart'"></i>
          {{ profile.is_favorited ? "Dans mes favoris" : "Ajouter aux favoris" }}
        </button>
        <button
          v-if="profile && !profile.is_owner && isUsable('contact')" type="button" class="ie-btn ie-btn-secondary"
          :disabled="contactBusy" @click="contactProvider"
        >
          <i class="fa-solid fa-comment-dots"></i> {{ contactBusy ? "Connexion…" : "Contacter le prestataire" }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 320px;"></div>

    <EmptyState
      v-else-if="notFound" icon="fa-solid fa-lock"
      text="Ce profil est introuvable, masqué, ou nécessite un abonnement actif pour être consulté."
    />

    <template v-else-if="profile">
      <div class="ie-pro-detail-cover" :class="{ 'has-photo': profile.cover_photo }">
        <div class="ie-pro-detail-cover-img">
          <img v-if="profile.cover_photo" :src="profile.cover_photo" :alt="profile.business_name" />
        </div>
        <div class="ie-pro-detail-header">
          <div class="ie-pro-detail-logo">
            <img v-if="profile.logo" :src="profile.logo" :alt="profile.business_name" />
            <i v-else class="fa-solid fa-handshake"></i>
          </div>
          <div>
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <h1 style="margin: 0;">{{ profile.business_name }}</h1>
              <span v-if="profile.is_verified" class="ie-badge ie-badge-success"><i class="fa-solid fa-circle-check"></i> Vérifié</span>
              <span v-if="profile.is_top" class="ie-badge ie-badge-top"><i class="fa-solid fa-trophy"></i> Top prestataire</span>
              <span v-if="profile.is_recommended" class="ie-badge ie-badge-recommended"><i class="fa-solid fa-star"></i> Recommandé</span>
              <span v-if="profile.price_range" class="ie-badge ie-badge-neutral">{{ profile.price_range }}</span>
            </div>
            <p class="ie-page-subtitle" style="margin: 4px 0 0;">
              {{ profile.category_display }}
              <template v-if="profile.city"> · <i class="fa-solid fa-location-dot"></i> {{ [profile.neighborhood, profile.city].filter(Boolean).join(', ') }}</template>
              <template v-if="profile.client_type_display"> · <i class="fa-solid fa-user-tie"></i> {{ profile.client_type_display }}</template>
            </p>
            <div class="ie-pro-meta" style="margin-top: 8px; align-items: center;">
              <StarRating v-if="profile.average_rating" :model-value="profile.average_rating" :count="profile.review_count" />
              <span v-if="profile.review_count" style="font-size: 11.5px; color: var(--ie-muted);">
                <i class="fa-solid fa-shield-check"></i> Avis vérifiés
              </span>
              <span>{{ profile.services.length }} service{{ profile.services.length > 1 ? 's' : '' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="ie-pro-detail-grid">
        <div>
          <div class="ie-card ie-card-body" v-if="profile.description || profile.team_presentation || specialtiesList.length">
            <h2><i class="fa-solid fa-circle-info ie-section-icon"></i>À propos</h2>
            <p v-if="profile.description" style="color: var(--ie-ink); line-height: 1.6;">{{ profile.description }}</p>
            <template v-if="profile.team_presentation">
              <h3 style="margin-top: 16px; font-size: 14px;">Notre équipe</h3>
              <p style="color: var(--ie-muted); line-height: 1.6;">{{ profile.team_presentation }}</p>
            </template>
            <div v-if="specialtiesList.length" style="margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px;">
              <span v-for="s in specialtiesList" :key="s" class="ie-badge ie-badge-neutral">{{ s }}</span>
            </div>
            <p v-if="profile.service_area" style="margin-top: 14px; font-size: 12.5px; color: var(--ie-muted);">
              <i class="fa-solid fa-map"></i> Zone d'intervention : {{ profile.service_area }}
            </p>
            <p v-if="profile.conditions" style="margin-top: 8px; font-size: 12.5px; color: var(--ie-muted);">
              <i class="fa-solid fa-circle-info"></i> {{ profile.conditions }}
            </p>
          </div>

          <div class="ie-card ie-card-body" style="margin-top: 20px;" v-if="isVisible('view_services')">
            <h2><i class="fa-solid fa-concierge-bell ie-section-icon"></i>Services proposés</h2>
            <div v-if="!isUsable('view_services')" class="ie-upsell-block">
              <i class="fa-solid fa-lock"></i>
              <p>{{ upsellMessage('view_services') || "Abonnez-vous pour consulter les services et tarifs de ce prestataire." }}</p>
              <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-primary ie-btn-sm">S'abonner</router-link>
            </div>
            <template v-else>
              <div v-if="profile.services.length" class="ie-service-list">
                <div v-for="s in profile.services" :key="s.id" class="ie-service-row">
                  <div class="ie-service-photo">
                    <img v-if="s.photo" :src="s.photo" :alt="s.name" />
                    <i v-else class="fa-solid fa-concierge-bell"></i>
                  </div>
                  <div class="ie-service-info">
                    <strong>{{ s.name }}</strong>
                    <p v-if="s.description" style="margin: 2px 0; font-size: 12px; color: var(--ie-muted);">{{ s.description }}</p>
                    <span>
                      {{ s.pricing_type === 'fixed' ? `À partir de ${Number(s.price_from).toLocaleString('fr-FR')} ${s.currency}` : "Sur devis" }}
                      <template v-if="s.duration_label"> · {{ s.duration_label }}</template>
                      <template v-if="s.capacity"> · {{ s.capacity }} pers.</template>
                    </span>
                  </div>
                  <button v-if="isUsable('book')" type="button" class="ie-btn ie-btn-primary ie-btn-sm" @click="requestService(s)">
                    <i class="fa-solid fa-file-invoice"></i> Demander un devis
                  </button>
                </div>
              </div>
              <p v-else class="ie-field-hint">Aucun service publié pour le moment.</p>
            </template>
          </div>

          <div class="ie-card ie-card-body" style="margin-top: 20px;" v-if="isVisible('availability_calendar')">
            <h2><i class="fa-solid fa-calendar-check ie-section-icon"></i>Disponibilités</h2>
            <div v-if="!isUsable('availability_calendar')" class="ie-upsell-block">
              <i class="fa-solid fa-lock"></i>
              <p>{{ upsellMessage('availability_calendar') || "Abonnez-vous pour consulter les disponibilités en temps réel." }}</p>
              <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-primary ie-btn-sm">S'abonner</router-link>
            </div>
            <template v-else>
              <div class="ie-avail-nav">
                <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="changeAvailMonth(-1)"><i class="fa-solid fa-chevron-left"></i></button>
                <strong class="ie-avail-month-label">{{ availMonthLabel }}</strong>
                <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="changeAvailMonth(1)"><i class="fa-solid fa-chevron-right"></i></button>
              </div>
              <div class="ie-availability-legend">
                <span><i class="ie-dot ie-dot-available"></i> Disponible</span>
                <span><i class="ie-dot ie-dot-blocked"></i> Indisponible</span>
              </div>
              <div v-if="availLoading" class="ie-skeleton" style="height: 220px; margin-top: 10px;"></div>
              <table v-else class="ie-calendar" style="margin-top: 10px;">
                <thead><tr><th v-for="d in ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']" :key="d">{{ d }}</th></tr></thead>
                <tbody>
                  <tr v-for="(week, wi) in availWeeks" :key="wi">
                    <td
                      v-for="(day, di) in week" :key="di" class="ie-calendar-cell ie-avail-cell"
                      :class="[{ empty: !day }, day ? `status-${availStatusFor(day)}` : '']"
                    >
                      <span v-if="day">{{ day.getDate() }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </template>
          </div>

          <div class="ie-card ie-card-body" style="margin-top: 20px;" v-if="profile.portfolio_items.length">
            <h2><i class="fa-solid fa-images ie-section-icon"></i>Réalisations</h2>
            <div class="ie-portfolio-grid">
              <div v-for="p in profile.portfolio_items" :key="p.id" class="ie-portfolio-item">
                <div v-if="p.before_image" class="ie-portfolio-before-after">
                  <img :src="p.before_image" alt="Avant" />
                  <img :src="p.image" :alt="p.caption" />
                  <span class="ie-badge ie-badge-neutral ie-portfolio-ba-label ie-portfolio-ba-before">Avant</span>
                  <span class="ie-badge ie-badge-neutral ie-portfolio-ba-label ie-portfolio-ba-after">Après</span>
                </div>
                <img v-else :src="p.image" :alt="p.caption" />
                <span v-if="p.caption" class="ie-portfolio-caption">{{ p.caption }}</span>
              </div>
            </div>
          </div>

          <div class="ie-card ie-card-body" style="margin-top: 20px;" v-if="isVisible('reviews')">
            <h2><i class="fa-solid fa-star ie-section-icon"></i>Avis clients</h2>
            <form v-if="!myReview" @submit.prevent="submitReview" style="margin-bottom: 18px; padding-bottom: 18px; border-bottom: 1px solid var(--ie-line);">
              <label class="ie-label">Votre note</label>
              <div><StarRating v-model="reviewForm.rating" :readonly="false" :size="24" /></div>
              <label class="ie-label" style="margin-top: 12px;">Votre commentaire</label>
              <textarea v-model="reviewForm.comment" class="ie-input" rows="2"></textarea>
              <p v-if="reviewError" class="ie-alert ie-alert-danger" style="margin-top: 8px;">{{ reviewError }}</p>
              <button class="ie-btn ie-btn-primary ie-btn-sm" type="submit" style="margin-top: 10px;" :disabled="reviewSubmitting">
                {{ reviewSubmitting ? "Envoi…" : "Publier mon avis" }}
              </button>
            </form>
            <div v-if="reviewsLoading" class="ie-skeleton" style="height: 60px;"></div>
            <div v-else-if="reviews.length" style="display: flex; flex-direction: column; gap: 12px;">
              <div v-for="r in reviews" :key="r.id" style="border: 1px solid var(--ie-line); border-radius: 8px; padding: 10px 14px;">
                <StarRating :model-value="r.rating" :size="13" />
                <p v-if="r.comment" style="margin: 4px 0 0; font-size: 12.5px; color: var(--ie-muted);">{{ r.comment }}</p>
              </div>
            </div>
            <p v-else class="ie-field-hint">Aucun avis pour le moment.</p>
          </div>
        </div>

        <div class="ie-card ie-card-body ie-pro-contact-card" ref="bookingPanelRef" v-if="isVisible('book')">
          <h2 style="margin-bottom: 4px;"><i class="fa-solid fa-file-invoice ie-section-icon"></i>Demander un devis</h2>
          <p class="ie-field-hint" style="margin: 0 0 14px;">
            {{ profile.business_name }} vous répondra directement avec un devis détaillé, entièrement via la plateforme — aucune coordonnée n'est partagée directement.
          </p>

          <div v-if="!isUsable('book')" class="ie-upsell-block">
            <i class="fa-solid fa-lock"></i>
            <p>{{ upsellMessage('book') || "Abonnez-vous pour demander un devis à ce prestataire directement via la plateforme." }}</p>
            <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-primary ie-btn-sm">S'abonner</router-link>
          </div>

          <div v-else-if="bookingSent" class="ie-alert ie-alert-success">
            <i class="fa-solid fa-circle-check"></i> Demande de devis envoyée ! Le prestataire va vous répondre.
            <router-link :to="{ name: 'my-booking-requests' }" style="display: block; margin-top: 6px; font-weight: 700;">Voir mes demandes →</router-link>
          </div>

          <form v-else @submit.prevent="submitBooking">
            <label class="ie-label">Service souhaité</label>
            <select v-model="bookingForm.service" class="ie-select">
              <option value="">Non spécifié / à discuter</option>
              <option v-for="s in profile.services" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <label class="ie-label" style="margin-top: 12px;">Type d'événement</label>
            <input v-model="bookingForm.event_type" class="ie-input" placeholder="Ex : Mariage, Anniversaire, Séminaire" />
            <div class="ie-form-row" style="margin-top: 12px;">
              <div>
                <label class="ie-label">Date</label>
                <input v-model="bookingForm.event_date" type="date" class="ie-input" />
              </div>
              <div>
                <label class="ie-label">Heure</label>
                <input v-model="bookingForm.event_time" type="time" class="ie-input" />
              </div>
            </div>
            <label class="ie-label" style="margin-top: 12px;">Position précise</label>
            <input v-model="bookingForm.location" class="ie-input" placeholder="Ex : Douala, PK14 — ou un lieu-dit / quartier précis" />
            <p class="ie-field-hint" style="margin: 4px 0 0;">Aide le prestataire à estimer ses frais de déplacement.</p>
            <div class="ie-form-row" style="margin-top: 12px;">
              <div>
                <label class="ie-label">Ville</label>
                <input v-model="bookingForm.city" class="ie-input" />
              </div>
              <div>
                <label class="ie-label">Nombre d'invités</label>
                <input v-model.number="bookingForm.guest_count" type="number" min="0" class="ie-input" />
              </div>
            </div>
            <label class="ie-label" style="margin-top: 12px;">Budget estimatif (XAF)</label>
            <input v-model.number="bookingForm.budget_estimate" type="number" min="0" class="ie-input" placeholder="Optionnel" />
            <label class="ie-label" style="margin-top: 12px;">Options souhaitées</label>
            <input v-model="bookingForm.options_wanted" class="ie-input" placeholder="Ex : éclairage, arche florale..." />

            <label class="ie-label" style="margin-top: 12px;">Matériel souhaité (facultatif)</label>
            <p class="ie-field-hint" style="margin: 0 0 8px;">Ajoutez chaises, tables, projecteur, couverts... le prestataire verra précisément ce qu'il faut inclure dans son devis.</p>
            <div v-for="(item, index) in requestedItems" :key="index" class="ie-requested-item-row">
              <select v-model="item.equipment" class="ie-select">
                <option value="">Choisir un matériel…</option>
                <option v-for="eq in equipmentCatalog" :key="eq.id" :value="eq.id">{{ eq.name }}</option>
              </select>
              <input v-model.number="item.quantity" type="number" min="1" class="ie-input" style="width: 70px;" />
              <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="removeRequestedItem(index)" :disabled="requestedItems.length <= 1">
                <i class="fa-solid fa-trash"></i>
              </button>
            </div>
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="addRequestedItem">
              <i class="fa-solid fa-plus"></i> Ajouter un matériel
            </button>

            <label class="ie-label" style="margin-top: 16px;">Votre téléphone</label>
            <input v-model="bookingForm.contact_phone" class="ie-input" placeholder="Pour que le prestataire puisse vous recontacter via l'application" />
            <label class="ie-label" style="margin-top: 12px;">Description de votre besoin</label>
            <textarea v-model="bookingForm.message" class="ie-input" rows="3" placeholder="Décrivez votre projet..."></textarea>
            <p v-if="bookingError" class="ie-alert ie-alert-danger" style="margin-top: 10px;">{{ bookingError }}</p>
            <button class="ie-btn ie-btn-primary" type="submit" style="width: 100%; margin-top: 14px;" :disabled="bookingSubmitting">
              <i class="fa-solid fa-paper-plane"></i> {{ bookingSubmitting ? "Envoi…" : "Demander un devis" }}
            </button>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-requested-item-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.ie-requested-item-row .ie-select { flex: 1; }

.ie-pro-detail-cover { position: relative; margin-bottom: 52px; height: 90px; }
.ie-pro-detail-cover.has-photo { height: 220px; }
.ie-pro-detail-cover-img { position: absolute; inset: 0; border-radius: 14px; overflow: hidden; background: var(--ie-navy-soft); }
.ie-pro-detail-cover-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
.ie-pro-detail-header {
  position: absolute; left: 0; right: 0; bottom: -44px; padding: 0 24px;
  display: flex; align-items: flex-end; gap: 18px;
}
.ie-pro-detail-cover:not(.has-photo) .ie-pro-detail-header { align-items: center; }
.ie-pro-detail-logo {
  width: 96px; height: 96px; border-radius: 16px; overflow: hidden; background: #fff;
  border: 4px solid #fff; box-shadow: 0 4px 14px rgba(0,0,0,0.18); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.ie-pro-detail-logo img { width: 100%; height: 100%; object-fit: cover; }
.ie-pro-detail-logo i { font-size: 30px; color: var(--ie-navy); opacity: 0.35; }
.ie-pro-meta { display: flex; gap: 14px; font-size: 12.5px; color: var(--ie-muted); }

.ie-pro-detail-grid { display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: flex-start; }
.ie-section-icon { color: var(--ie-red); margin-right: 8px; font-size: 15px; }

.ie-pro-contact-card { position: sticky; top: 20px; box-shadow: 0 10px 26px rgba(23, 27, 38, 0.08); }

.ie-favorited { color: var(--ie-red); border-color: var(--ie-red); }
.ie-badge-top { background: #fff3d6; color: #92650a; }
.ie-badge-recommended { background: var(--ie-red-soft); color: var(--ie-red); }

.ie-upsell-block {
  display: flex; flex-direction: column; align-items: flex-start; gap: 10px;
  padding: 16px; background: var(--ie-red-soft); border: 1px dashed var(--ie-red); border-radius: 10px;
}
.ie-favorited { color: var(--ie-red) !important; border-color: var(--ie-red) !important; }
.ie-upsell-block i { color: var(--ie-red); font-size: 18px; }
.ie-upsell-block p { margin: 0; font-size: 12.5px; color: var(--ie-ink); line-height: 1.5; }

.ie-avail-nav { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.ie-avail-month-label { color: var(--ie-navy); text-transform: capitalize; font-size: 13px; min-width: 130px; text-align: center; }
.ie-availability-legend { display: flex; gap: 16px; font-size: 11.5px; color: var(--ie-muted); }
.ie-availability-legend span { display: inline-flex; align-items: center; gap: 6px; }
.ie-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.ie-dot-available { background: var(--ie-success); }
.ie-dot-blocked { background: var(--ie-red); }
.ie-calendar { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ie-calendar th { padding: 6px; font-size: 10px; color: var(--ie-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.ie-calendar-cell { border: 1px solid var(--ie-line); text-align: center; font-size: 11.5px; color: var(--ie-navy); height: 34px; }
.ie-calendar-cell.empty { background: #fafbfc; }
.ie-avail-cell.status-available { background: var(--ie-success-soft); }
.ie-avail-cell.status-blocked, .ie-avail-cell.status-full { background: var(--ie-red-soft); color: var(--ie-muted); }
.ie-avail-cell.status-past, .ie-avail-cell.status-too_soon { color: #b7bcc2; }

.ie-service-list { display: flex; flex-direction: column; gap: 10px; }
.ie-service-row {
  display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--ie-line);
  border-radius: 10px; transition: border-color 0.15s ease, box-shadow 0.15s ease; flex-wrap: wrap;
}
.ie-service-row:hover { border-color: var(--ie-navy); box-shadow: 0 4px 14px rgba(23, 27, 38, 0.08); }
.ie-service-photo { width: 56px; height: 56px; border-radius: 10px; overflow: hidden; background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ie-service-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-service-photo i { color: var(--ie-navy); opacity: 0.4; font-size: 18px; }
.ie-service-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.ie-service-info strong { font-size: 14px; color: var(--ie-navy); }
.ie-service-info span { font-size: 12px; color: var(--ie-red); font-weight: 600; }

.ie-portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; }
.ie-portfolio-item { position: relative; aspect-ratio: 1; border-radius: 10px; overflow: hidden; }
.ie-portfolio-item img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.25s ease; }
.ie-portfolio-item:hover img { transform: scale(1.06); }
.ie-portfolio-before-after { position: relative; width: 100%; height: 100%; display: flex; }
.ie-portfolio-before-after img { width: 50%; height: 100%; object-fit: cover; }
.ie-portfolio-ba-label { position: absolute; bottom: 4px; font-size: 9px; padding: 1px 5px; }
.ie-portfolio-ba-before { left: 4px; }
.ie-portfolio-ba-after { right: 4px; }
.ie-portfolio-caption {
  position: absolute; bottom: 0; left: 0; right: 0; padding: 4px 6px; font-size: 10.5px; color: #fff;
  background: linear-gradient(to top, rgba(0,0,0,0.65), transparent);
}

@media (max-width: 860px) {
  .ie-pro-detail-grid { grid-template-columns: 1fr; }
  .ie-pro-contact-card { position: static; }
}
</style>
