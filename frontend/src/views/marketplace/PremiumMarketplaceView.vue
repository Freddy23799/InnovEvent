<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import StarRating from "../../components/StarRating.vue";
import SubscriptionCheckoutModal from "../../components/SubscriptionCheckoutModal.vue";
import { fetchMarketplaceFeatures, useFeatureFlags } from "../../composables/useFeatureFlags";
import { ACTOR_CATEGORY_GROUPS, ACTOR_CATEGORY_LOOKUP } from "../../data/actorCategories";
import { citiesForCountry } from "../../data/countries";
import { EVENT_TYPE_CATEGORY_MAP, EVENT_TYPES } from "../../data/eventTypeCategories";
import { CLIENT_TYPES, INTERIOR_DESIGN_CATEGORY_GROUPS, INTERIOR_DESIGN_CATEGORY_LOOKUP, PRICE_RANGES } from "../../data/interiorDesignCategories";
import api from "../../services/api";
import { useMarketplaceAccessStore } from "../../stores/marketplaceAccess";
import { useToastStore } from "../../stores/toast";

const CAMEROON_CITIES = citiesForCountry("CM");

const { t } = useI18n();

// La Marketplace des acteurs ET « Décoration & design intérieur » proposent
// toutes deux une navigation par métier (blocs → catalogue filtré) ; les
// autres marketplaces gardent leur liste directe.
const CATEGORY_BROWSABLE_TYPES = new Set(["actors", "interior_design"]);

const MARKETPLACE_META = {
  sale: { icon: "fa-solid fa-bag-shopping", tagline: "Objets, mobilier et équipements événementiels à acheter directement.", kind: "listing" },
  interior_design: { icon: "fa-solid fa-couch", tagline: "Décorateurs et designers d'intérieur pour vos espaces, au-delà de l'événement.", kind: "profile" },
  actors: { icon: "fa-solid fa-people-group", tagline: "Prestataires et professionnels de l'événementiel disponibles à la réservation.", kind: "profile" },
  venues: { icon: "fa-solid fa-building-columns", tagline: "Salles de réception à réserver pour vos événements.", kind: "venue" },
};

const route = useRoute();
const router = useRouter();
const toast = useToastStore();

const loading = ref(true);
const info = reactive({ price: 0, currency: "XAF", duration_days: 30, plans: [], marketplaces: [], tiers: [] });
// Permet un lien direct depuis la sidebar (« Marketplace des acteurs » → un
// métier précis) : ?type=actors&category=dj ouvre directement le catalogue de
// ce métier, sans repasser par l'index des blocs.
const activeType = ref(typeof route.query.type === "string" ? route.query.type : null);
const activeKind = computed(() => MARKETPLACE_META[activeType.value]?.kind || "listing");
const checkoutMarketplace = ref(null);
// Catégorie verrouillée cliquée : on explique d'abord pourquoi (formule
// requise) et on propose un bouton pour passer au plan supérieur, plutôt que
// d'ouvrir directement la fenêtre de paiement sans contexte.
const upsellPromptGroup = ref(null);

function openCheckout(marketplace) {
  checkoutMarketplace.value = marketplace;
}

function onCategoryChipClick(group, item) {
  if (group.locked) {
    upsellPromptGroup.value = group;
    return;
  }
  selectCategory(item.value);
}

function confirmUpsell() {
  upsellPromptGroup.value = null;
  openCheckout(activeMarketplace.value);
}

const marketplaceAccess = useMarketplaceAccessStore();

async function handleSubscribed() {
  checkoutMarketplace.value = null;
  await loadInfo();
  await loadActiveContent();
  // La sidebar (layout persistant) lit ce store partagé plutôt que de
  // refaire son propre fetch — sans ça elle resterait figée sur l'état
  // d'avant paiement tant que la page n'est pas rechargée.
  await marketplaceAccess.refresh();
}

const listings = ref([]);
const listingsLoading = ref(false);
const ordering = reactive({});
const orderError = reactive({});
const orderSuccess = reactive({});
const orderCoupon = reactive({});

const profiles = ref([]);
// Alimenté par les valeurs réellement présentes dans les résultats affichés
// (pas de taxonomie de quartiers séparée à maintenir) — se met à jour au fil
// des recherches.
const neighborhoodOptions = computed(() =>
  [...new Set(profiles.value.map((p) => p.neighborhood).filter(Boolean))].sort()
);
const profilesLoading = ref(false);
const activeFeatures = ref([]);
const { isUsable, isVisible, isLocked, upsellMessage } = useFeatureFlags(activeFeatures);

const selectedCategory = ref(typeof route.query.category === "string" ? route.query.category : null);
const showCategoryIndex = computed(() =>
  CATEGORY_BROWSABLE_TYPES.has(activeType.value) && activeKind.value === "profile" && !selectedCategory.value
);
const selectedCategoryLabel = computed(() => {
  const lookup = activeType.value === "interior_design" ? INTERIOR_DESIGN_CATEGORY_LOOKUP : ACTOR_CATEGORY_LOOKUP;
  return lookup[selectedCategory.value] || "";
});

// Un client qui arrive directement sur un métier précis (lien de sidebar, ou
// après avoir choisi un métier dans l'index) a déjà fait son choix : pas
// besoin de lui remontrer la grille des 4 marketplaces à souscrire ni tout
// l'argumentaire commercial — seulement un statut compact (palier actuel +
// éventuelle incitation à monter de palier si des catégories restent
// verrouillées). Cette grille/argumentaire ne réapparaissent que sur la page
// d'accueil du Marketplace (aucun métier encore choisi).
const showFullHub = computed(() => !selectedCategory.value);
const hasLockedCategoryGroups = computed(
  () => activeType.value === "actors" && ACTOR_CATEGORY_GROUPS.some((g) => g.featureKey && isVisible(g.featureKey) && isLocked(g.featureKey))
);

// « Un seul parcours intelligent » : on demande d'abord le type d'événement
// pour ne montrer qu'une liste courte de métiers pertinents, au lieu des 42
// d'un coup. Un lien de secours reste disponible pour parcourir tous les
// métiers (ex : un prestataire hors des cas habituels), et un lien direct
// depuis la sidebar (?category=x) saute cette étape entièrement.
const selectedEventType = ref(null);
const showAllCategories = ref(false);
const filteredCategoryGroups = computed(() => {
  let groups = activeType.value === "interior_design" ? INTERIOR_DESIGN_CATEGORY_GROUPS : ACTOR_CATEGORY_GROUPS;
  if (selectedEventType.value) {
    const allowed = new Set(EVENT_TYPE_CATEGORY_MAP[selectedEventType.value] || []);
    groups = ACTOR_CATEGORY_GROUPS.map((group) => ({ ...group, items: group.items.filter((item) => allowed.has(item.value)) }))
      .filter((group) => group.items.length);
  }
  // Le palier d'abonnement (configurable par l'admin) décide quelles
  // catégories de métiers sont visibles : absentes tant que non abonné,
  // verrouillées (mais visibles, avec message d'incitation) si le palier
  // actuel ne suffit pas.
  if (activeType.value !== "actors") return groups;
  return groups
    .filter((group) => !group.featureKey || isVisible(group.featureKey))
    .map((group) => ({
      ...group,
      locked: group.featureKey ? isLocked(group.featureKey) : false,
      lockMessage: group.featureKey ? upsellMessage(group.featureKey) : "",
    }));
});
const selectedEventTypeLabel = computed(() => EVENT_TYPES.find((e) => e.value === selectedEventType.value)?.label || "");

function selectEventType(value) {
  selectedEventType.value = value;
  showAllCategories.value = false;
}

function backToEventTypes() {
  selectedEventType.value = null;
  showAllCategories.value = false;
}

function selectCategory(categoryValue) {
  selectedCategory.value = categoryValue;
  loadProfiles();
}

function backToCategories() {
  selectedCategory.value = null;
  profiles.value = [];
}

async function loadInfo() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/subscriptions/", { params: { marketplace_type: activeType.value } });
    Object.assign(info, data);
    if (!activeType.value) {
      activeType.value = data.marketplaces[0]?.marketplace_type;
      if (activeType.value) {
        const scoped = await api.get("/marketplace/subscriptions/", { params: { marketplace_type: activeType.value } });
        Object.assign(info, scoped.data);
      }
    }
  } finally {
    loading.value = false;
  }
}

const activeMarketplace = computed(() => info.marketplaces.find((m) => m.marketplace_type === activeType.value));

async function selectMarketplace(type) {
  activeType.value = type;
  await loadInfo();
  selectedCategory.value = null;
  selectedEventType.value = null;
  showAllCategories.value = false;
  // Toujours charger : le backend renvoie déjà les annonces/profils en accès libre même
  // sans abonnement (« mode client simple »), en plus du contenu réservé si abonné.
  await loadActiveContent();
}

async function loadActiveContent() {
  activeFeatures.value = await fetchMarketplaceFeatures(activeType.value).catch(() => []);
  if (activeKind.value === "venue") {
    // Les salles ont leur propre page dédiée (VenuesView) — rien à charger ici,
    // seul le statut d'abonnement (activeFeatures) importe pour ce panneau.
    return;
  }
  if (activeKind.value !== "profile") {
    await loadListings();
  } else {
    loadRecommended();
    if (!CATEGORY_BROWSABLE_TYPES.has(activeType.value) || selectedCategory.value) {
      await loadProfiles();
    }
  }
  // Sinon (marketplace navigable par métier, aucun métier encore choisi) : on
  // affiche l'index des catégories, rien à charger avant que le client clique.
}


async function loadListings() {
  listingsLoading.value = true;
  try {
    const { data } = await api.get("/marketplace/listings/", { params: { marketplace_type: activeType.value } });
    listings.value = data.results || data;
    listings.value.forEach((l) => { if (!(l.id in ordering)) ordering[l.id] = 1; });
  } finally {
    listingsLoading.value = false;
  }
}

// `search`/`city` peuvent arriver via l'URL (barre de recherche centrale de
// la page d'accueil, section 8 du CDC) — mêmes noms de paramètres que ceux
// envoyés à l'API, aucune traduction nécessaire.
const searchFilters = reactive({
  search: typeof route.query.search === "string" ? route.query.search : "",
  city: typeof route.query.city === "string" ? route.query.city : "",
  neighborhood: "",
  available_on: "",
  min_rating: "", is_verified: false, ordering: "", client_type: "", price_range: "",
});
let searchDebounce = null;

const nearMe = reactive({ active: false, lat: null, lng: null, maxDistanceKm: "", loading: false, error: "" });

function onFiltersChanged() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadProfiles, 350);
}

function useNearMe() {
  if (nearMe.active) {
    nearMe.active = false;
    nearMe.lat = null;
    nearMe.lng = null;
    nearMe.error = "";
    if (searchFilters.ordering === "nearest") searchFilters.ordering = "";
    loadProfiles();
    return;
  }
  if (!navigator.geolocation) {
    nearMe.error = t("marketplace.geolocationUnavailable");
    return;
  }
  nearMe.loading = true;
  nearMe.error = "";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      nearMe.lat = position.coords.latitude;
      nearMe.lng = position.coords.longitude;
      nearMe.active = true;
      nearMe.loading = false;
      searchFilters.ordering = "nearest";
      loadProfiles();
    },
    () => {
      nearMe.loading = false;
      nearMe.error = t("marketplace.geolocationDenied");
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

async function loadProfiles() {
  profilesLoading.value = true;
  try {
    const params = { marketplace_type: activeType.value };
    if (selectedCategory.value) params.category = selectedCategory.value;
    if (searchFilters.search) params.search = searchFilters.search;
    if (searchFilters.city) params.city = searchFilters.city;
    if (searchFilters.neighborhood) params.neighborhood = searchFilters.neighborhood;
    if (searchFilters.available_on) params.available_on = searchFilters.available_on;
    if (searchFilters.min_rating) params.min_rating = searchFilters.min_rating;
    if (searchFilters.is_verified) params.is_verified = true;
    if (searchFilters.client_type) params.client_type = searchFilters.client_type;
    if (searchFilters.price_range) params.price_range = searchFilters.price_range;
    if (searchFilters.ordering) params.ordering = searchFilters.ordering;
    if (nearMe.active && nearMe.lat != null && nearMe.lng != null) {
      params.near_lat = nearMe.lat;
      params.near_lng = nearMe.lng;
      if (nearMe.maxDistanceKm) params.max_distance_km = nearMe.maxDistanceKm;
    }
    const { data } = await api.get("/marketplace/profiles/", { params });
    profiles.value = data.results || data;
  } finally {
    profilesLoading.value = false;
  }
}

const favoriteBusy = reactive({});
async function toggleFavorite(profile) {
  favoriteBusy[profile.id] = true;
  try {
    if (profile.is_favorited) {
      await api.delete(`/marketplace/favorites/by-profile/${profile.id}/`);
      profile.is_favorited = false;
    } else {
      await api.post("/marketplace/favorites/", { profile: profile.id });
      profile.is_favorited = true;
    }
  } finally {
    favoriteBusy[profile.id] = false;
  }
}

const contactBusy = reactive({});
async function contactProviderFromCard(profile) {
  contactBusy[profile.id] = true;
  try {
    const { data } = await api.post("/messaging/conversations/contact-provider/", { profile: profile.id });
    router.push({ name: "messaging", query: { conversation: data.id } });
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible de contacter ce prestataire pour le moment.");
  } finally {
    contactBusy[profile.id] = false;
  }
}

async function shareProfile(profile) {
  const url = `${window.location.origin}${router.resolve({ name: "professional-profile-detail", params: { id: profile.id } }).href}`;
  if (navigator.share) {
    try {
      await navigator.share({ title: profile.business_name, url });
    } catch (e) {
      // partage annulé par l'utilisateur — rien à faire
    }
    return;
  }
  try {
    await navigator.clipboard.writeText(url);
    toast.success("Lien du profil copié.");
  } catch (e) {
    toast.error("Impossible de copier le lien.");
  }
}

const recommendedProfiles = ref([]);
const recommendedLoading = ref(false);

async function loadRecommended() {
  if (!isUsable("recommendations")) {
    recommendedProfiles.value = [];
    return;
  }
  recommendedLoading.value = true;
  try {
    const { data } = await api.get("/marketplace/profiles/recommended/", { params: { marketplace_type: activeType.value } });
    recommendedProfiles.value = data;
  } catch {
    recommendedProfiles.value = [];
  } finally {
    recommendedLoading.value = false;
  }
}

async function toggleFavoriteRecommended(profile) {
  await toggleFavorite(profile);
  if (profile.is_favorited) {
    recommendedProfiles.value = recommendedProfiles.value.filter((p) => p.id !== profile.id);
  }
}

async function orderListing(listing) {
  orderError[listing.id] = "";
  orderSuccess[listing.id] = "";
  try {
    await api.post("/marketplace/orders/pay/", {
      listing: listing.id,
      quantity: ordering[listing.id] || 1,
      payment_provider: "demo",
      coupon_code: orderCoupon[listing.id] || undefined,
    });
    orderSuccess[listing.id] = "Commande payée avec succès.";
  } catch (e) {
    orderError[listing.id] = e?.response?.data?.detail || "La commande a échoué.";
  }
}

// --- Marketplace vente : recherche/tri (liste déjà chargée en entier côté
// client, sans pagination — un tri/filtre local suffit, pas besoin d'aller-
// retour serveur supplémentaire pour ce volume d'annonces). ---------------
const listingFilters = reactive({ search: "", sort: "" });
const filteredListings = computed(() => {
  const query = listingFilters.search.trim().toLowerCase();
  let result = query
    ? listings.value.filter((l) => l.title.toLowerCase().includes(query) || (l.description || "").toLowerCase().includes(query))
    : listings.value;
  result = [...result];
  if (listingFilters.sort === "price_asc") result.sort((a, b) => Number(a.price) - Number(b.price));
  else if (listingFilters.sort === "price_desc") result.sort((a, b) => Number(b.price) - Number(a.price));
  else if (listingFilters.sort === "newest") result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return result;
});

function decrementQty(listing) { ordering[listing.id] = Math.max(1, (ordering[listing.id] || 1) - 1); }
function incrementQty(listing) { ordering[listing.id] = (ordering[listing.id] || 1) + 1; }
function subtotal(listing) { return Number(listing.price) * (ordering[listing.id] || 1); }

onMounted(async () => {
  await loadInfo();
  await loadActiveContent();
});

// La navigation depuis la sidebar (un lien par métier) ne change que la query
// string sur cette même route : Vue Router ne remonte pas le composant, donc on
// réagit explicitement pour ouvrir directement le bon catalogue.
watch(
  () => route.query,
  async (query) => {
    const nextType = typeof query.type === "string" ? query.type : activeType.value;
    const nextCategory = typeof query.category === "string" ? query.category : null;
    if (nextType === activeType.value && nextCategory === selectedCategory.value) return;
    activeType.value = nextType;
    selectedCategory.value = nextCategory;
    selectedEventType.value = null;
    showAllCategories.value = false;
    await loadActiveContent();
  }
);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-store" style="color: var(--ie-red); margin-right: 8px;"></i>{{ $t("marketplace.title") }}</h1>
        <p class="ie-page-subtitle">{{ $t("marketplace.subtitle") }}</p>
      </div>
      <div class="ie-page-header-actions">
        <router-link :to="{ name: 'dashboard' }" class="ie-btn ie-btn-ghost">
          <i class="fa-solid fa-arrow-left"></i> {{ $t("marketplace.backToDashboard") }}
        </router-link>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <template v-else>
      <template v-if="showFullHub">
      <div class="ie-mp-grid">
        <div v-for="m in info.marketplaces" :key="m.marketplace_type" class="ie-mp-card" :class="{ 'is-active': activeType === m.marketplace_type }">
          <button type="button" class="ie-mp-card-select" @click="selectMarketplace(m.marketplace_type)">
            <span class="ie-mp-icon"><i :class="MARKETPLACE_META[m.marketplace_type]?.icon"></i></span>
            <span class="ie-mp-title">{{ m.marketplace_label }}</span>
            <span class="ie-mp-tagline">{{ MARKETPLACE_META[m.marketplace_type]?.tagline }}</span>
            <span v-if="m.is_active" class="ie-badge ie-badge-success">
              <i class="fa-solid fa-circle-check"></i> {{ $t("marketplace.subscribedUntil", { date: new Date(m.expires_at).toLocaleDateString($i18n.locale) }) }}
            </span>
          </button>
          <template v-if="!m.is_active">
            <p class="ie-mp-price-from">
              À partir de {{ Number(info.plans[0]?.price || 0).toLocaleString('fr-FR') }} XAF/mois
            </p>
            <button type="button" class="ie-mp-subscribe-btn" @click="openCheckout(m)">
              <i class="fa-solid fa-lock-open"></i> {{ $t("marketplace.subscribe") }}
            </button>
          </template>
        </div>
      </div>

      <section class="ie-mp-about">
        <h2 class="ie-mp-section-title"><i class="fa-solid fa-circle-info"></i> Pourquoi s'abonner au Marketplace InnovEvent ?</h2>
        <div class="ie-mp-about-grid">
          <div class="ie-mp-benefit">
            <i class="fa-solid fa-shield-halved"></i>
            <div>
              <strong>Prestataires vérifiés</strong>
              <p>Chaque profil est contrôlé par notre équipe avant publication — badge « Vérifié » et avis clients authentiques.</p>
            </div>
          </div>
          <div class="ie-mp-benefit">
            <i class="fa-solid fa-file-signature"></i>
            <div>
              <strong>Devis structurés et sécurisés</strong>
              <p>Chaque devis est signé, exportable en PDF avec code QR de vérification — aucune mauvaise surprise sur le prix.</p>
            </div>
          </div>
          <div class="ie-mp-benefit">
            <i class="fa-solid fa-user-shield"></i>
            <div>
              <strong>Vos coordonnées restent privées</strong>
              <p>Toute la négociation passe par la messagerie intégrée de la plateforme — votre téléphone et votre email ne sont jamais partagés.</p>
            </div>
          </div>
          <div class="ie-mp-benefit">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            <div>
              <strong>Recommandations personnalisées</strong>
              <p>Des suggestions basées sur vos favoris et vos demandes, pour trouver le bon prestataire plus vite.</p>
            </div>
          </div>
          <div class="ie-mp-benefit">
            <i class="fa-solid fa-calendar-check"></i>
            <div>
              <strong>Réservation directe et suivi</strong>
              <p>Envoyez une demande, suivez son statut en temps réel et échangez jusqu'à la confirmation — tout depuis votre tableau de bord.</p>
            </div>
          </div>
          <div class="ie-mp-benefit">
            <i class="fa-solid fa-rotate-left"></i>
            <div>
              <strong>Sans engagement</strong>
              <p>Choisissez la durée qui vous convient et ne renouvelez que si vous le souhaitez — aucun engagement au-delà de la période payée.</p>
            </div>
          </div>
        </div>

        <h3 class="ie-mp-about-pricing-title">Tarifs</h3>
        <div class="ie-table-wrap">
          <table class="ie-table ie-mp-pricing-table">
            <thead>
              <tr><th>Formule</th><th>Prix</th><th>Équivalent mensuel</th><th>Réduction</th></tr>
            </thead>
            <tbody>
              <tr v-for="plan in info.plans" :key="plan.code">
                <td><strong>{{ plan.label }}</strong></td>
                <td class="ie-num">{{ Number(plan.price).toLocaleString('fr-FR') }} {{ plan.currency }}</td>
                <td class="ie-num">{{ Math.round(plan.price / plan.months).toLocaleString('fr-FR') }} {{ plan.currency }}/mois</td>
                <td>
                  <span v-if="plan.discount_percent" class="ie-badge ie-badge-success">-{{ plan.discount_percent }}%</span>
                  <span v-else class="ie-badge ie-badge-neutral">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="ie-field-hint" style="margin-top: 8px;">Tarif identique pour les 4 marketplaces premium (Marketplace vente, Décoration & design intérieur, Marketplace des acteurs, Salles de réception) — un abonnement par marketplace, choisissez celui qui correspond à votre besoin ci-dessus.</p>
      </section>
      </template>

      <div v-else-if="activeMarketplace" class="ie-tier-strip">
        <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-ghost ie-btn-sm">
          <i class="fa-solid fa-arrow-left"></i> Marketplaces
        </router-link>
        <template v-if="!activeMarketplace.is_active">
          <span class="ie-tier-strip-text"><i class="fa-solid fa-lock"></i> Vous n'êtes pas encore abonné à « {{ activeMarketplace.marketplace_label }} ».</span>
          <button type="button" class="ie-btn ie-btn-primary ie-btn-sm ie-tier-strip-cta" @click="openCheckout(activeMarketplace)">
            <i class="fa-solid fa-lock-open"></i> S'abonner
          </button>
        </template>
        <template v-else>
          <span class="ie-tier-strip-text">
            <i class="fa-solid fa-crown"></i> Vous êtes au palier <strong>{{ activeMarketplace.tier_label || "Basic" }}</strong>
          </span>
          <button v-if="hasLockedCategoryGroups" type="button" class="ie-btn ie-btn-outline ie-btn-sm ie-tier-strip-cta" @click="openCheckout(activeMarketplace)">
            <i class="fa-solid fa-arrow-up"></i> Voir les paliers supérieurs
          </button>
        </template>
      </div>

      <template v-if="activeMarketplace">
        <div v-if="!activeMarketplace.is_active" class="ie-mp-upsell-banner">
          <i class="fa-solid fa-lock"></i>
          <span>{{ $t("marketplace.upsellBanner", { label: activeMarketplace.marketplace_label }) }}</span>
        </div>

        <div v-if="activeKind === 'profile' && recommendedProfiles.length" class="ie-recommended-rail">
          <h2 class="ie-mp-section-title"><i class="fa-solid fa-wand-magic-sparkles"></i> {{ $t("marketplace.recommendedForYou") }}</h2>
          <div class="ie-recommended-scroll">
            <router-link
              v-for="profile in recommendedProfiles" :key="profile.id"
              :to="{ name: 'professional-profile-detail', params: { id: profile.id } }"
              class="ie-card ie-pro-card ie-pro-card-sm"
            >
              <button
                type="button" class="ie-pro-favorite" :class="{ 'is-favorited': profile.is_favorited }"
                :disabled="favoriteBusy[profile.id]" @click.prevent.stop="toggleFavoriteRecommended(profile)"
              >
                <i :class="profile.is_favorited ? 'fa-solid fa-heart' : 'fa-regular fa-heart'"></i>
              </button>
              <div class="ie-pro-cover">
                <img v-if="profile.cover_photo" :src="profile.cover_photo" :alt="profile.business_name" />
                <i v-else class="fa-solid fa-image"></i>
                <span v-if="profile.is_verified" class="ie-badge ie-badge-success ie-pro-verified">
                  <i class="fa-solid fa-circle-check"></i> {{ $t("marketplace.verified") }}
                </span>
              </div>
              <div class="ie-card-body ie-pro-card-body">
                <span class="ie-pro-category">{{ profile.category_display }}</span>
                <h3 class="ie-pro-name">{{ profile.business_name }}</h3>
                <p v-if="profile.city" class="ie-listing-provider"><i class="fa-solid fa-location-dot"></i> {{ profile.city }}</p>
                <StarRating v-if="profile.average_rating" :model-value="profile.average_rating" :count="profile.review_count" :size="12" class="ie-pro-rating" />
              </div>
            </router-link>
          </div>
        </div>

        <template v-if="showCategoryIndex">
          <template v-if="activeType === 'actors' && !selectedEventType && !showAllCategories">
            <div class="ie-event-quiz">
              <h2 class="ie-mp-section-title">Quel type d'événement organisez-vous ?</h2>
              <p class="ie-field-hint" style="margin: 0 0 18px;">Répondez à cette question pour ne voir que les prestataires utiles à votre événement — plus rapide que de parcourir les 42 métiers un par un.</p>
              <div class="ie-event-type-grid">
                <button
                  v-for="et in EVENT_TYPES" :key="et.value" type="button"
                  class="ie-event-type-card" @click="selectEventType(et.value)"
                >
                  <i :class="et.icon"></i>
                  <span>{{ et.label }}</span>
                </button>
              </div>
              <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 16px;" @click="showAllCategories = true">
                Parcourir tous les métiers plutôt
              </button>
            </div>
          </template>

          <template v-else>
            <div v-if="activeType === 'actors'" class="ie-page-header-actions" style="margin-bottom: 12px;">
              <button v-if="selectedEventType" type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="backToEventTypes">
                <i class="fa-solid fa-arrow-left"></i> Changer de type d'événement
              </button>
              <button v-else type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="showAllCategories = false">
                <i class="fa-solid fa-arrow-left"></i> Retour
              </button>
            </div>
            <h2 class="ie-mp-section-title">
              {{ selectedEventType ? `Pour « ${selectedEventTypeLabel} », il vous faut :` : `${activeMarketplace.marketplace_label} — ${$t("marketplace.chooseCategory")}` }}
            </h2>
            <EmptyState
              v-if="!filteredCategoryGroups.length"
              icon="fa-solid fa-lock"
              :text="`Abonnez-vous pour découvrir les métiers de « ${activeMarketplace.marketplace_label} ».`"
            >
              <button type="button" class="ie-btn ie-btn-marketplace" @click="openCheckout(activeMarketplace)">
                <i class="fa-solid fa-lock-open"></i> {{ $t("marketplace.subscribe") }}
              </button>
            </EmptyState>
            <div v-else class="ie-category-groups">
              <div v-for="group in filteredCategoryGroups" :key="group.title" class="ie-category-group" :class="{ 'is-locked': group.locked }">
                <h3>
                  <i :class="group.icon"></i> {{ group.title }}
                  <span v-if="group.locked" class="ie-badge ie-badge-neutral ie-category-lock-badge"><i class="fa-solid fa-lock"></i> Formule supérieure</span>
                </h3>
                <p v-if="group.hint" class="ie-field-hint" style="margin: 0 0 8px; font-style: italic;">{{ group.hint }}</p>
                <p v-if="group.locked" class="ie-field-hint" style="margin: 0 0 8px;">
                  {{ group.lockMessage || "Cette catégorie nécessite une formule d'abonnement supérieure." }}
                </p>
                <div class="ie-category-chips">
                  <button
                    v-for="item in group.items" :key="item.value" type="button"
                    class="ie-category-chip" :class="{ 'is-locked': group.locked }"
                    @click="onCategoryChipClick(group, item)"
                  >
                    <i v-if="group.locked" class="fa-solid fa-lock"></i> {{ item.label }}
                  </button>
                </div>
              </div>
            </div>
          </template>
        </template>

        <template v-else>
          <div v-if="CATEGORY_BROWSABLE_TYPES.has(activeType) && activeKind === 'profile'" class="ie-page-header-actions" style="margin-bottom: 12px;">
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="backToCategories">
              <i class="fa-solid fa-arrow-left"></i> {{ $t("marketplace.allTrades") }}
            </button>
          </div>
          <h2 class="ie-mp-section-title">
            {{ selectedCategoryLabel || activeMarketplace.marketplace_label }}
          </h2>

        <template v-if="activeKind === 'listing'">
          <div class="ie-sale-explainer">
            <i class="fa-solid fa-circle-info"></i>
            <p>Achetez directement objets, mobilier et équipements événementiels — annonces publiées par InnovEvent ou par des prestataires vérifiés. Paiement sécurisé sur la plateforme, sans abonnement requis.</p>
          </div>

          <div class="ie-search-bar">
            <div class="ie-search-input">
              <i class="fa-solid fa-magnifying-glass"></i>
              <input v-model="listingFilters.search" placeholder="Rechercher une annonce..." />
            </div>
            <select v-model="listingFilters.sort" class="ie-select ie-search-filter">
              <option value="">Pertinence</option>
              <option value="newest">Nouveautés</option>
              <option value="price_asc">Prix croissant</option>
              <option value="price_desc">Prix décroissant</option>
            </select>
          </div>

          <div v-if="listingsLoading" class="ie-catalog-grid">
            <div v-for="i in 3" :key="i" class="ie-skeleton" style="height: 300px;"></div>
          </div>
          <div v-else-if="filteredListings.length" class="ie-catalog-grid">
            <div v-for="listing in filteredListings" :key="listing.id" class="ie-card ie-listing-card">
              <div class="ie-listing-photo">
                <img v-if="listing.photo" :src="listing.photo" :alt="listing.title" />
                <i v-else class="fa-solid fa-box-open"></i>
                <span class="ie-badge ie-badge-neutral ie-listing-seller-badge">
                  <i class="fa-solid" :class="listing.provider_name || listing.created_by_name ? 'fa-handshake' : 'fa-store'"></i>
                  {{ listing.provider_name || listing.created_by_name || "InnovEvent" }}
                </span>
              </div>
              <div class="ie-card-body">
                <h3>{{ listing.title }}</h3>
                <p class="ie-listing-desc">{{ listing.description || "Aucune description fournie." }}</p>
                <strong class="ie-listing-price">{{ Number(listing.price).toLocaleString('fr-FR') }} {{ listing.currency }}</strong>

                <div class="ie-listing-order-row">
                  <div class="ie-qty-stepper">
                    <button type="button" @click="decrementQty(listing)" :disabled="(ordering[listing.id] || 1) <= 1"><i class="fa-solid fa-minus"></i></button>
                    <span>{{ ordering[listing.id] || 1 }}</span>
                    <button type="button" @click="incrementQty(listing)"><i class="fa-solid fa-plus"></i></button>
                  </div>
                  <button class="ie-btn ie-btn-primary ie-btn-sm" @click="orderListing(listing)">
                    <i class="fa-solid fa-cart-shopping"></i> Commander · {{ subtotal(listing).toLocaleString('fr-FR') }} {{ listing.currency }}
                  </button>
                </div>
                <input
                  v-model="orderCoupon[listing.id]" class="ie-input" style="margin-top: 6px; font-size: 12px; padding: 6px 10px;"
                  placeholder="Code de réduction (optionnel)"
                />
                <p v-if="orderSuccess[listing.id]" class="ie-alert ie-alert-success" style="margin-top: 8px;">{{ orderSuccess[listing.id] }}</p>
                <p v-if="orderError[listing.id]" class="ie-alert ie-alert-danger" style="margin-top: 8px;">{{ orderError[listing.id] }}</p>
              </div>
            </div>
          </div>
          <EmptyState v-else icon="fa-solid fa-box-open" :text="`Aucune annonce dans « ${activeMarketplace.marketplace_label} » pour le moment.`" />
        </template>

        <template v-else-if="activeKind === 'venue'">
          <div v-if="activeMarketplace.is_active" class="ie-venue-cta">
            <i class="fa-solid fa-building-columns"></i>
            <p>Consultez le catalogue complet et réservez directement une salle pour votre événement.</p>
            <router-link :to="{ name: 'venues' }" class="ie-btn ie-btn-primary">
              <i class="fa-solid fa-arrow-right"></i> Voir les salles de réception
            </router-link>
          </div>
          <EmptyState v-else icon="fa-solid fa-lock" text="Abonnez-vous pour consulter et réserver nos salles de réception." />
        </template>

        <template v-else>
          <div class="ie-search-bar">
            <div class="ie-search-input">
              <i class="fa-solid fa-magnifying-glass"></i>
              <input v-model="searchFilters.search" :placeholder="$t('marketplace.searchPlaceholder')" @input="onFiltersChanged" />
            </div>
            <select v-model="searchFilters.city" class="ie-select ie-search-filter" @change="loadProfiles">
              <option value="">{{ $t("marketplace.allCities") }}</option>
              <option v-for="c in CAMEROON_CITIES" :key="c.name" :value="c.name">{{ c.name }}</option>
            </select>
            <select v-model="searchFilters.neighborhood" class="ie-select ie-search-filter" @change="loadProfiles">
              <option value="">Tout quartier</option>
              <option v-for="n in neighborhoodOptions" :key="n" :value="n">{{ n }}</option>
            </select>
            <input
              v-model="searchFilters.available_on" type="date" class="ie-select ie-search-filter"
              title="Disponible le..." @change="loadProfiles"
            />
            <select v-model="searchFilters.min_rating" class="ie-select ie-search-filter" @change="loadProfiles">
              <option value="">{{ $t("marketplace.allRatings") }}</option>
              <option value="4">{{ $t("marketplace.ratingAndAbove", { stars: 4 }) }}</option>
              <option value="3">{{ $t("marketplace.ratingAndAbove", { stars: 3 }) }}</option>
            </select>
            <template v-if="activeType === 'interior_design'">
              <select v-model="searchFilters.client_type" class="ie-select ie-search-filter" @change="loadProfiles">
                <option value="">Tout type de client</option>
                <option v-for="c in CLIENT_TYPES" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
              <select v-model="searchFilters.price_range" class="ie-select ie-search-filter" @change="loadProfiles">
                <option value="">Toute gamme de prix</option>
                <option v-for="p in PRICE_RANGES" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </template>
            <label class="ie-search-checkbox">
              <input type="checkbox" v-model="searchFilters.is_verified" @change="loadProfiles" /> {{ $t("marketplace.verifiedOnly") }}
            </label>
            <select v-model="searchFilters.ordering" class="ie-select ie-search-filter" @change="loadProfiles">
              <option value="">{{ $t("marketplace.relevance") }}</option>
              <option value="top_rated">{{ $t("marketplace.topRated") }}</option>
              <option value="newest">{{ $t("marketplace.newest") }}</option>
              <option value="price_asc">{{ $t("marketplace.priceAsc") }}</option>
              <option value="price_desc">{{ $t("marketplace.priceDesc") }}</option>
              <option v-if="nearMe.active" value="nearest">{{ $t("marketplace.nearest") }}</option>
            </select>
            <button
              type="button" class="ie-btn ie-btn-outline ie-search-filter" :class="{ 'is-active': nearMe.active }"
              :disabled="nearMe.loading" @click="useNearMe"
            >
              <i class="fa-solid" :class="nearMe.loading ? 'fa-spinner fa-spin' : 'fa-location-crosshairs'"></i>
              {{ nearMe.active ? $t("marketplace.nearMeActive") : $t("marketplace.nearMe") }}
            </button>
            <select v-if="nearMe.active" v-model="nearMe.maxDistanceKm" class="ie-select ie-search-filter" @change="loadProfiles">
              <option value="">{{ $t("marketplace.allDistances") }}</option>
              <option value="10">{{ $t("marketplace.distanceUpTo", { km: 10 }) }}</option>
              <option value="25">{{ $t("marketplace.distanceUpTo", { km: 25 }) }}</option>
              <option value="50">{{ $t("marketplace.distanceUpTo", { km: 50 }) }}</option>
              <option value="100">{{ $t("marketplace.distanceUpTo", { km: 100 }) }}</option>
            </select>
          </div>
          <p v-if="nearMe.error" class="ie-alert ie-alert-danger" style="margin-bottom: 12px;">{{ nearMe.error }}</p>

          <div v-if="profilesLoading" class="ie-catalog-grid">
            <div v-for="i in 3" :key="i" class="ie-skeleton" style="height: 260px;"></div>
          </div>
          <div v-else-if="profiles.length" class="ie-catalog-grid">
            <router-link
              v-for="profile in profiles" :key="profile.id"
              :to="{ name: 'professional-profile-detail', params: { id: profile.id } }"
              class="ie-card ie-pro-card ie-pro-card-lg"
            >
              <div class="ie-pro-cover">
                <img v-if="profile.cover_photo" :src="profile.cover_photo" :alt="profile.business_name" />
                <i v-else class="fa-solid fa-image"></i>

                <div class="ie-pro-cover-actions">
                  <button
                    type="button" class="ie-pro-icon-btn" :class="{ 'is-favorited': profile.is_favorited }"
                    :disabled="favoriteBusy[profile.id]" @click.prevent.stop="toggleFavorite(profile)"
                    aria-label="Favori"
                  >
                    <i :class="profile.is_favorited ? 'fa-solid fa-heart' : 'fa-regular fa-heart'"></i>
                  </button>
                  <button type="button" class="ie-pro-icon-btn" @click.prevent.stop="shareProfile(profile)" aria-label="Partager">
                    <i class="fa-solid fa-share-nodes"></i>
                  </button>
                </div>

                <span v-if="profile.is_verified && isUsable('view_profile')" class="ie-badge ie-badge-success ie-pro-corner-badge">
                  <i class="fa-solid fa-circle-check"></i> {{ $t("marketplace.verified") }}
                </span>
                <span v-else-if="!isUsable('view_profile')" class="ie-badge ie-badge-neutral ie-pro-corner-badge ie-pro-locked">
                  <i class="fa-solid fa-lock"></i> {{ $t("marketplace.subscribersOnly") }}
                </span>
                <span v-else-if="profile.is_top" class="ie-badge ie-pro-corner-badge ie-badge-top"><i class="fa-solid fa-crown"></i> TOP</span>
                <span v-else-if="profile.is_recommended" class="ie-badge ie-pro-corner-badge ie-badge-recommended"><i class="fa-solid fa-star"></i> {{ $t("marketplace.recommended") }}</span>

                <span v-if="profile.category_display" class="ie-pro-category ie-pro-category-overlay">{{ profile.category_display }}</span>
              </div>

              <div class="ie-card-body ie-pro-card-body">
                <h3 class="ie-pro-name">{{ profile.business_name }}</h3>
                <div class="ie-pro-loc-rating">
                  <span v-if="profile.city || profile.service_area" class="ie-listing-provider">
                    <i class="fa-solid fa-location-dot"></i> {{ profile.service_area || profile.city }}
                    <span v-if="profile.distance_km != null" class="ie-pro-distance"> · {{ Number(profile.distance_km).toLocaleString($i18n.locale, { maximumFractionDigits: 1 }) }} km</span>
                  </span>
                  <span class="ie-pro-rating-inline">
                    <i class="fa-solid fa-star"></i> {{ profile.average_rating != null ? Number(profile.average_rating).toLocaleString($i18n.locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : "0.0" }}
                    <span class="ie-pro-review-count">({{ profile.review_count || 0 }})</span>
                  </span>
                </div>

                <hr class="ie-pro-divider" />

                <div class="ie-pro-bottom-row">
                  <span class="ie-pro-price-tag">
                    {{ profile.starting_price != null
                      ? $t("marketplace.startingFrom", { price: `${Number(profile.starting_price).toLocaleString($i18n.locale)} XAF` })
                      : $t("marketplace.onQuote") }}
                  </span>
                  <button type="button" class="ie-btn-contact" :disabled="contactBusy[profile.id]" @click.prevent.stop="contactProviderFromCard(profile)">
                    <i class="fa-solid fa-comment-dots"></i> {{ contactBusy[profile.id] ? "…" : "Contacter" }}
                  </button>
                </div>
              </div>
            </router-link>
          </div>
          <EmptyState v-else icon="fa-solid fa-people-group" :text="$t('marketplace.noProfiles', { label: activeMarketplace.marketplace_label })" />
        </template>
        </template>
      </template>
    </template>

    <div v-if="upsellPromptGroup" class="ie-upsell-backdrop" @click.self="upsellPromptGroup = null">
      <div class="ie-upsell-dialog">
        <button type="button" class="ie-upsell-close" aria-label="Fermer" @click="upsellPromptGroup = null">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <div class="ie-upsell-icon"><i class="fa-solid fa-lock"></i></div>
        <h3>Formule supérieure requise</h3>
        <p>{{ upsellPromptGroup.lockMessage || "Cette catégorie nécessite une formule d'abonnement supérieure." }}</p>
        <button type="button" class="ie-btn ie-btn-marketplace ie-upsell-cta" @click="confirmUpsell">
          <i class="fa-solid fa-lock-open"></i> Passer au plan supérieur
        </button>
      </div>
    </div>

    <SubscriptionCheckoutModal
      v-if="checkoutMarketplace"
      :marketplace-type="checkoutMarketplace.marketplace_type"
      :marketplace-label="checkoutMarketplace.marketplace_label"
      :plans="info.plans"
      :tiers="info.tiers"
      @close="checkoutMarketplace = null"
      @subscribed="handleSubscribed"
    />
  </div>
</template>

<style scoped>
.ie-mp-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
.ie-mp-card {
  background: #fff; border: 1px solid var(--ie-line); border-radius: 12px; padding: 4px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.ie-mp-card.is-active { border-color: var(--ie-navy); box-shadow: 0 8px 24px rgba(57, 73, 91, 0.12); }
.ie-mp-card-static { display: block; text-decoration: none; color: inherit; }
.ie-mp-card-static:hover { border-color: var(--ie-navy); box-shadow: 0 8px 24px rgba(57, 73, 91, 0.12); }
.ie-mp-card-select { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; width: 100%; padding: 20px 18px 14px; background: transparent; border: 0; text-align: left; cursor: pointer; }
.ie-mp-icon {
  width: 46px; height: 46px; border-radius: 12px; background: var(--ie-navy-soft); color: var(--ie-navy);
  display: flex; align-items: center; justify-content: center; font-size: 19px; margin-bottom: 4px;
}
.ie-mp-card.is-active .ie-mp-icon { background: var(--ie-navy); color: #fff; }
.ie-mp-title { font-size: 14.5px; font-weight: 700; color: var(--ie-navy); }
.ie-mp-tagline { font-size: 12px; color: var(--ie-muted); line-height: 1.5; }
.ie-mp-price-from { margin: 0 4px 8px; font-size: 12px; color: var(--ie-muted); }
.ie-mp-subscribe-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px; width: calc(100% - 8px); margin: 0 4px 4px;
  padding: 11px 14px; border-radius: 8px; border: 0; background: var(--ie-red); color: #fff;
  font-size: 12.5px; font-weight: 700; cursor: pointer; transition: background 0.2s ease;
}
.ie-mp-subscribe-btn:hover:not(:disabled) { background: #8a0e16; }
.ie-mp-subscribe-btn:disabled { opacity: 0.7; cursor: default; }

.ie-tier-strip {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 10px 14px; margin-bottom: 18px;
  background: #fff; border: 1px solid var(--ie-line); border-radius: 10px;
}
.ie-tier-strip-text { font-size: 12.5px; color: var(--ie-ink); display: inline-flex; align-items: center; gap: 6px; }
.ie-tier-strip-text i { color: var(--ie-red); }
.ie-tier-strip-cta { margin-left: auto; }

.ie-mp-upsell-banner {
  display: flex; align-items: center; gap: 12px; padding: 14px 18px; margin-bottom: 20px;
  background: var(--ie-red-soft); border: 1px solid var(--ie-red); border-radius: 10px; color: var(--ie-red);
}
.ie-mp-upsell-banner i { font-size: 16px; flex-shrink: 0; }
.ie-mp-upsell-banner span { font-size: 12.5px; color: var(--ie-ink); }

.ie-mp-section-title { font-size: 17px; color: var(--ie-navy); margin: 0 0 16px; }

.ie-mp-about { background: #fff; border: 1px solid var(--ie-line); border-radius: 14px; padding: 26px 28px; margin-bottom: 24px; }
.ie-mp-about-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; margin-bottom: 24px; }
.ie-mp-benefit { display: flex; align-items: flex-start; gap: 12px; }
.ie-mp-benefit i { font-size: 20px; color: var(--ie-red); flex-shrink: 0; margin-top: 2px; width: 22px; text-align: center; }
.ie-mp-benefit strong { display: block; font-size: 13.5px; color: var(--ie-navy); margin-bottom: 3px; }
.ie-mp-benefit p { margin: 0; font-size: 12px; color: var(--ie-muted); line-height: 1.5; }
.ie-mp-about-pricing-title { font-size: 14px; color: var(--ie-navy); margin: 0 0 12px; padding-top: 18px; border-top: 1px solid var(--ie-line); }
.ie-mp-pricing-table th { font-size: 11.5px; }
@media (max-width: 700px) { .ie-mp-about { padding: 20px; } }

.ie-category-groups { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.ie-category-group {
  background: #fff; border: 1px solid var(--ie-line); border-radius: 12px; padding: 18px;
}
.ie-category-group h3 {
  margin: 0 0 12px; font-size: 13.5px; color: var(--ie-navy); display: flex; align-items: center; gap: 8px;
  padding-bottom: 10px; border-bottom: 1px solid var(--ie-line);
}
.ie-category-group h3 i { color: var(--ie-red); font-size: 14px; }
.ie-category-chips { display: flex; flex-direction: column; gap: 4px; }
.ie-category-chip {
  text-align: left; background: transparent; border: 0; padding: 7px 8px; border-radius: 7px;
  font-size: 12.5px; color: var(--ie-ink); cursor: pointer; transition: background 0.15s ease;
}
.ie-category-chip:hover { background: var(--ie-navy-soft); color: var(--ie-navy); font-weight: 600; }
.ie-category-group.is-locked { background: var(--ie-navy-soft); }
.ie-category-chip.is-locked { color: var(--ie-muted); cursor: pointer; }
.ie-category-chip.is-locked:hover { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-category-chip.is-locked i { font-size: 10px; margin-right: 4px; }
.ie-category-lock-badge { font-size: 10px; padding: 2px 7px; margin-left: auto; }

@media (max-width: 700px) { .ie-category-groups { grid-template-columns: 1fr; } }

.ie-upsell-backdrop {
  position: fixed; inset: 0; background: rgba(23, 27, 38, 0.6); z-index: 200;
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.ie-upsell-dialog {
  position: relative; background: #fff; border-radius: 16px; max-width: 360px; width: 100%;
  padding: 28px 24px; text-align: center; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.3);
}
.ie-upsell-close {
  position: absolute; top: 12px; right: 12px; width: 30px; height: 30px; border-radius: 999px;
  border: 0; background: var(--ie-navy-soft); color: var(--ie-navy); cursor: pointer; font-size: 13px;
}
.ie-upsell-close:hover { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-upsell-icon {
  width: 52px; height: 52px; border-radius: 50%; margin: 0 auto 14px; background: var(--ie-red-soft);
  color: var(--ie-red); display: flex; align-items: center; justify-content: center; font-size: 20px;
}
.ie-upsell-dialog h3 { margin: 0 0 8px; font-size: 17px; color: var(--ie-navy); }
.ie-upsell-dialog p { margin: 0 0 20px; font-size: 13.5px; color: var(--ie-muted); line-height: 1.5; }
.ie-upsell-cta { width: 100%; padding: 12px; }

.ie-event-quiz { max-width: 720px; }
.ie-event-type-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.ie-event-type-card {
  display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center;
  background: #fff; border: 1px solid var(--ie-line); border-radius: 12px; padding: 22px 16px;
  cursor: pointer; transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  font-size: 13px; font-weight: 600; color: var(--ie-navy);
}
.ie-event-type-card i { font-size: 24px; color: var(--ie-red); }
.ie-event-type-card:hover { border-color: var(--ie-navy); box-shadow: 0 8px 20px rgba(57, 73, 91, 0.12); transform: translateY(-2px); }
@media (max-width: 700px) { .ie-event-type-grid { grid-template-columns: repeat(2, 1fr); } }

.ie-catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 18px; }
.ie-sale-explainer {
  display: flex; align-items: flex-start; gap: 10px; background: var(--ie-navy-soft); border-radius: 10px;
  padding: 12px 16px; margin-bottom: 16px; font-size: 12.5px; color: var(--ie-navy); line-height: 1.55;
}
.ie-sale-explainer i { color: var(--ie-navy); margin-top: 2px; flex-shrink: 0; }
.ie-sale-explainer p { margin: 0; }

.ie-venue-cta {
  display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px;
  background: #fff; border: 1px solid var(--ie-line); border-radius: 14px; padding: 40px 24px;
}
.ie-venue-cta i { font-size: 34px; color: var(--ie-red); }
.ie-venue-cta p { margin: 0; color: var(--ie-muted); max-width: 420px; }

.ie-listing-card { overflow: hidden; }
.ie-listing-photo { height: 150px; background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center; position: relative; }
.ie-listing-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-listing-photo i { font-size: 32px; color: var(--ie-navy); opacity: 0.35; }
.ie-listing-seller-badge { position: absolute; bottom: 8px; left: 8px; background: rgba(255,255,255,0.94); }
.ie-listing-card h3 { font-size: 14px; color: var(--ie-navy); margin: 0 0 4px; }
.ie-listing-desc { font-size: 12px; color: var(--ie-muted); margin: 0 0 10px; line-height: 1.5; min-height: 34px; }
.ie-listing-price { font-size: 17px; color: var(--ie-red); display: block; margin-bottom: 10px; }
.ie-listing-order-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ie-qty-stepper {
  display: flex; align-items: center; gap: 0; border: 1px solid var(--ie-line); border-radius: 8px; overflow: hidden; flex-shrink: 0;
}
.ie-qty-stepper button {
  width: 26px; height: 26px; border: 0; background: var(--ie-navy-soft); color: var(--ie-navy); cursor: pointer;
  font-size: 10px; display: flex; align-items: center; justify-content: center;
}
.ie-qty-stepper button:disabled { opacity: 0.4; cursor: not-allowed; }
.ie-qty-stepper span { min-width: 24px; text-align: center; font-size: 12.5px; font-weight: 700; color: var(--ie-navy); }

.ie-pro-card {
  display: flex; flex-direction: column; overflow: hidden; text-decoration: none; color: inherit; position: relative;
  border-color: #E8EAED; box-shadow: 0 1px 3px rgba(23, 27, 38, 0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
.ie-pro-card:hover { transform: translateY(-4px); box-shadow: 0 16px 32px rgba(23, 27, 38, 0.14); border-color: var(--ie-line); }
.ie-pro-cover {
  height: 128px; flex-shrink: 0; position: relative; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #E4E9EF 0%, #EEF1F4 100%); border-bottom: 1px solid var(--ie-line);
}
.ie-pro-cover img { width: 100%; height: 100%; object-fit: cover; }
.ie-pro-cover i { font-size: 26px; color: var(--ie-navy); opacity: 0.22; }
.ie-pro-verified {
  position: absolute; top: 9px; left: 9px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(2px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12); font-size: 10px; padding: 3px 9px 3px 7px; gap: 4px;
}
.ie-pro-verified i { font-size: 10px; }
.ie-badge-top { background: #fff3d6; color: #92650a; }
.ie-badge-recommended { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-pro-locked {
  position: absolute; top: 9px; left: 9px; background: rgba(23, 27, 38, 0.82); color: #fff;
  font-size: 10px; padding: 3px 9px 3px 7px; gap: 4px;
}
.ie-pro-locked i { font-size: 10px; }

.ie-pro-card-body { display: flex; flex-direction: column; flex: 1; padding-top: 12px; }
.ie-pro-badge-row { display: flex; gap: 6px; flex-wrap: wrap; }
.ie-pro-category {
  display: block; align-self: flex-start; max-width: 100%; font-size: 10.5px; font-weight: 700; letter-spacing: 0.02em;
  text-transform: uppercase; color: var(--ie-navy); background: var(--ie-navy-soft);
  padding: 3px 9px; border-radius: 999px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ie-pro-name {
  font-size: 14.5px; margin: 9px 0 4px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; line-height: 1.3;
}
.ie-listing-provider {
  display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--ie-muted); margin: 0;
}
.ie-listing-provider i { color: var(--ie-red); font-size: 11px; }
.ie-pro-rating { margin-top: auto; padding-top: 10px; }
.ie-pro-price { margin-top: auto; padding-top: 10px; }

.ie-search-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 18px; }
.ie-search-input {
  flex: 1; min-width: 220px; display: flex; align-items: center; gap: 8px;
  background: #fff; border: 1px solid var(--ie-line); border-radius: 8px; padding: 9px 12px;
}
.ie-search-input i { color: var(--ie-muted); }
.ie-search-input input { border: 0; outline: none; flex: 1; font-size: 13px; background: transparent; }
.ie-search-filter { max-width: 160px; }
.ie-search-checkbox { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ie-ink); white-space: nowrap; }
.ie-search-bar .ie-btn-outline.is-active { background: var(--ie-navy); color: #fff; border-color: var(--ie-navy); }
.ie-pro-distance { color: var(--ie-muted); font-weight: 500; }
.ie-recommended-rail { margin-bottom: 28px; }
.ie-recommended-scroll {
  display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px; scroll-snap-type: x proximity;
}
.ie-pro-card-sm { flex: 0 0 200px; scroll-snap-align: start; }

.ie-pro-favorite {
  position: absolute; top: 9px; right: 9px; z-index: 2; width: 30px; height: 30px; border-radius: 50%;
  background: rgba(255, 255, 255, 0.95); border: 0; display: flex; align-items: center; justify-content: center;
  color: var(--ie-navy); font-size: 13.5px; cursor: pointer; transition: transform 0.12s ease, color 0.12s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}
.ie-pro-favorite:hover { transform: scale(1.12); color: var(--ie-red); }
.ie-pro-favorite.is-favorited { color: var(--ie-red); }
.ie-pro-logo {
  width: 54px; height: 54px; border-radius: 50%; overflow: hidden; background: #fff; flex-shrink: 0;
  border: 3px solid #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  margin: -30px 0 0 16px; display: flex; align-items: center; justify-content: center; position: relative; z-index: 1;
}
.ie-pro-logo img { width: 100%; height: 100%; object-fit: cover; }
.ie-pro-logo i { font-size: 18px; color: var(--ie-navy); opacity: 0.4; }
.ie-pro-meta { display: flex; gap: 14px; font-size: 12px; color: var(--ie-muted); margin: 6px 0 10px; }

/* Carte prestataire « grand format » (catalogue principal) */
.ie-pro-card-lg .ie-pro-cover { height: 190px; }
.ie-pro-cover-actions { position: absolute; top: 9px; left: 9px; z-index: 2; display: flex; flex-direction: column; gap: 8px; }
.ie-pro-icon-btn {
  width: 30px; height: 30px; border-radius: 50%; border: 0; background: rgba(255, 255, 255, 0.95);
  display: flex; align-items: center; justify-content: center; color: var(--ie-navy); font-size: 13px;
  cursor: pointer; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15); transition: transform 0.12s ease, color 0.12s ease;
}
.ie-pro-icon-btn:hover { transform: scale(1.1); color: var(--ie-red); }
.ie-pro-icon-btn.is-favorited { color: var(--ie-red); }
.ie-pro-corner-badge { position: absolute; top: 9px; right: 9px; left: auto; }
.ie-pro-category-overlay {
  position: absolute; bottom: 9px; left: 9px; background: rgba(23, 27, 38, 0.72); color: #fff;
  backdrop-filter: blur(2px);
}
.ie-pro-loc-rating { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.ie-pro-rating-inline { display: flex; align-items: center; gap: 4px; font-size: 12.5px; font-weight: 700; color: var(--ie-navy); white-space: nowrap; }
.ie-pro-rating-inline i { color: #F5A623; font-size: 12px; }
.ie-pro-review-count { font-weight: 400; color: var(--ie-muted); }
.ie-pro-divider { border: 0; border-top: 1px solid var(--ie-line); margin: 12px 0 10px; }
.ie-pro-bottom-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: auto; }
.ie-pro-price-tag { font-size: 12.5px; color: var(--ie-muted); }
.ie-pro-price-tag b, .ie-pro-price-tag { color: var(--ie-ink); }
.ie-btn-contact {
  display: inline-flex; align-items: center; gap: 6px; background: var(--ie-red); color: #fff; border: 0;
  border-radius: 999px; padding: 8px 16px; font-size: 12.5px; font-weight: 700; cursor: pointer;
  white-space: nowrap; transition: filter 0.12s ease;
}
.ie-btn-contact:hover { filter: brightness(1.08); }
.ie-btn-contact:disabled { opacity: 0.6; cursor: not-allowed; }

@media (max-width: 860px) { .ie-mp-grid { grid-template-columns: 1fr; } }
</style>
