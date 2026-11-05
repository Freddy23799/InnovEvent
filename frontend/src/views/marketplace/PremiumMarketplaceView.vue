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
  sale: { icon: "fa-solid fa-bag-shopping", tagline: "Matériel événementiel à acheter ou à louer à la journée.", kind: "listing" },
  interior_design: { icon: "fa-solid fa-couch", tagline: "Décorateurs et designers d'intérieur pour vos espaces, au-delà de l'événement.", kind: "profile" },
  actors: { icon: "fa-solid fa-people-group", tagline: "Des prestataires de tous les domaines pour réaliser vos projets.", kind: "profile" },
  venues: { icon: "fa-solid fa-building-columns", tagline: "Plus de 50 salles de réception pour vos événements.", kind: "venue" },
};

const route = useRoute();
const router = useRouter();

// --- Accueil du Marketplace -------------------------------------------------
const HUB_ORDER = ["sale", "actors", "interior_design", "venues"];
const HUB_META = {
  // Chiffres de vitrine affichés en « plus de … » sur l'accueil.
  sale: { title: "Boutique", unit: "produits", tone: "tone-red", countLabel: "6 000+", points: ["Plus de 6 000 produits", "Achat ou location à la journée", "Total et facture automatiques"] },
  actors: { title: "Prestataires", unit: "prestataires", tone: "tone-navy", countLabel: "2 000+", points: ["Plus de 2 000 prestataires", "Tous les domaines : événementiel, maison, services…", "Profils vérifiés et devis en ligne"] },
  interior_design: { title: "Décoration & design", unit: "designs d'intérieur", tone: "tone-gold", countLabel: "300+", points: ["Plus de 300 designs d'intérieur", "Avant / après des réalisations", "Pour l'événement et la maison"] },
  // Salles : on affiche « Plus de 50 » plutôt que le nombre exact.
  venues: { title: "Salles de réception", unit: "salles", tone: "tone-teal", countLabel: "50+", points: ["Plus de 50 salles disponibles", "Filtre par ville et capacité", "Visite guidée sur demande"] },
};
const POPULAR_TRADES = [
  { value: "dj", label: "DJ" },
  { value: "caterer", label: "Traiteur" },
  { value: "photography", label: "Photographe" },
  { value: "decoration", label: "Décorateur" },
  { value: "wedding_planner", label: "Wedding planner" },
  { value: "mc", label: "MC" },
];
const BENEFITS = [
  { icon: "fa-solid fa-shield-halved", title: "Prestataires vérifiés", text: "Identité et réalisations contrôlées par notre équipe." },
  { icon: "fa-solid fa-user-shield", title: "Coordonnées protégées", text: "Tout passe par la messagerie de la plateforme." },
  { icon: "fa-solid fa-file-invoice", title: "Devis & factures en PDF", text: "Des prix clairs, vérifiables par QR code." },
  { icon: "fa-solid fa-rotate-left", title: "Sans engagement", text: "Vous ne payez que la période choisie." },
];
const heroQuery = ref("");

function heroSearch() {
  router.push({ name: "sale-shop", query: { q: heroQuery.value.trim() || undefined } });
}
const toast = useToastStore();

const loading = ref(true);
const info = reactive({ price: 0, currency: "XAF", duration_days: 30, plans: [], marketplaces: [], tiers: [], demo_mode: false });
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
  const subscribedType = checkoutMarketplace.value?.marketplace_type;
  checkoutMarketplace.value = null;
  if (subscribedType && subscribedType !== "venues") activeType.value = subscribedType;
  await loadInfo();
  if (activeType.value) await loadActiveContent();
  // La sidebar (layout persistant) lit ce store partagé plutôt que de
  // refaire son propre fetch — sans ça elle resterait figée sur l'état
  // d'avant paiement tant que la page n'est pas rechargée.
  await marketplaceAccess.refresh();
  // Les métiers débloqués s'affichent tout de suite dans la sidebar.
  if (CATEGORY_BROWSABLE_TYPES.has(subscribedType)) {
    marketplaceAccess.revealInSidebar(subscribedType);
    document.getElementById("mp-universe")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

const listings = ref([]);
const listingsLoading = ref(false);

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
    // Sans univers choisi (accueil), aucun contenu n'est ouvert sous les
    // cartes : le client choisit d'abord son univers.
    const { data } = await api.get("/marketplace/subscriptions/", { params: { marketplace_type: activeType.value || undefined } });
    Object.assign(info, data);
  } finally {
    loading.value = false;
  }
}

const activeMarketplace = computed(() => info.marketplaces.find((m) => m.marketplace_type === activeType.value));
const hubMarketplaces = computed(() =>
  HUB_ORDER.map((type) => info.marketplaces.find((m) => m.marketplace_type === type)).filter(Boolean)
);

// Ouvre le contenu d'un univers sous l'accueil et y fait défiler la page.
async function openUniverse(marketplace) {
  if (marketplace.marketplace_type === "venues") {
    router.push({ name: "venues" });
    return;
  }
  await selectMarketplace(marketplace.marketplace_type);
  document.getElementById("mp-universe")?.scrollIntoView({ behavior: "smooth", block: "start" });
  if (marketplace.is_active && CATEGORY_BROWSABLE_TYPES.has(marketplace.marketplace_type)) {
    marketplaceAccess.revealInSidebar(marketplace.marketplace_type);
  }
}

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

// Filtres secondaires rangés dans un panneau « Filtres » (barre principale :
// recherche, ville, tri) — ouvert d'office sur grand écran.
const filtersOpen = ref(typeof window !== "undefined" && window.innerWidth > 900);
const advancedFilterCount = computed(() =>
  [searchFilters.neighborhood, searchFilters.available_on, searchFilters.min_rating, searchFilters.client_type,
    searchFilters.price_range, searchFilters.is_verified].filter(Boolean).length
);
function resetAdvancedFilters() {
  Object.assign(searchFilters, { neighborhood: "", available_on: "", min_rating: "", client_type: "", price_range: "", is_verified: false });
  loadProfiles();
}

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

onMounted(async () => {
  await loadInfo();
  if (activeType.value) await loadActiveContent();
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
    if (activeType.value) await loadActiveContent();
  }
);
</script>

<template>
  <div>
    <div v-if="!showFullHub" class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-store" style="color: var(--ie-red); margin-right: 8px;"></i>{{ $t("marketplace.title") }}</h1>
        <p class="ie-page-subtitle">{{ $t("marketplace.subtitle") }}</p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 320px; border-radius: 18px;"></div>

    <template v-else>
      <template v-if="showFullHub">
      <!-- Accueil du Marketplace -->
      <section class="mph-hero">
        <div class="mph-hero-text">
          <span class="mph-eyebrow"><i class="fa-solid fa-store"></i> Le Marketplace InnovEvent</span>
          <h1>Tout pour réussir votre événement, au même endroit</h1>
          <p>Plus de 6 000 produits à acheter ou louer, plus de 2 000 prestataires de tous les domaines, plus de 300 designs d'intérieur et plus de 50 salles de réception : comparez, demandez un devis et réservez sans quitter la plateforme.</p>
          <form class="mph-search" role="search" @submit.prevent="heroSearch">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="heroQuery" type="search" placeholder="Rechercher un produit : chaises, verres, nappes…" aria-label="Rechercher dans la boutique" />
            <button type="submit" aria-label="Rechercher"><span>Rechercher</span><i class="fa-solid fa-arrow-right"></i></button>
          </form>
          <div class="mph-popular">
            <span>Populaires :</span>
            <router-link v-for="p in POPULAR_TRADES" :key="p.value" :to="{ name: 'premium-marketplace', query: { type: 'actors', category: p.value } }">{{ p.label }}</router-link>
          </div>
        </div>
        <ul class="mph-hero-stats">
          <li v-for="m in hubMarketplaces" :key="m.marketplace_type">
            <strong>{{ HUB_META[m.marketplace_type].countLabel || (m.item_count ?? "—") }}</strong>
            <span>{{ HUB_META[m.marketplace_type].unit }}</span>
          </li>
        </ul>
      </section>

      <section class="mph-section">
        <div class="mph-section-head">
          <h2>Choisissez votre univers</h2>
          <p>Un abonnement par univers — la boutique est gratuite pour tous.</p>
        </div>
        <div class="mph-cards">
          <article
            v-for="m in hubMarketplaces" :key="m.marketplace_type" class="mph-card"
            :class="[HUB_META[m.marketplace_type].tone, { 'is-active': activeType === m.marketplace_type && m.marketplace_type !== 'sale' }]"
          >
            <div class="mph-card-top">
              <span class="mph-card-icon"><i :class="MARKETPLACE_META[m.marketplace_type].icon"></i></span>
              <span v-if="m.is_free" class="mph-status free"><i class="fa-solid fa-gift"></i> Gratuit</span>
              <span v-else-if="m.is_active" class="mph-status on"><i class="fa-solid fa-circle-check"></i> Abonné</span>
              <span v-else class="mph-status"><i class="fa-solid fa-lock"></i> Premium</span>
            </div>
            <h3>{{ HUB_META[m.marketplace_type].title }}</h3>
            <p class="mph-card-tagline">{{ MARKETPLACE_META[m.marketplace_type].tagline }}</p>
            <ul class="mph-card-points">
              <li v-for="point in HUB_META[m.marketplace_type].points" :key="point"><i class="fa-solid fa-check"></i> {{ point }}</li>
            </ul>
            <div class="mph-card-foot">
              <div class="mph-card-meta">
                <strong>{{ HUB_META[m.marketplace_type].countLabel || (m.item_count ?? 0) }}</strong> {{ HUB_META[m.marketplace_type].unit }}
                <small v-if="m.is_active && m.expires_at">jusqu'au {{ new Date(m.expires_at).toLocaleDateString("fr-FR") }}</small>
                <small v-else-if="!m.is_free">sur abonnement</small>
                <small v-else-if="m.is_free">achat & location</small>
              </div>
              <router-link v-if="m.is_free" :to="{ name: 'sale-shop' }" class="mph-cta">
                Accéder <i class="fa-solid fa-arrow-right"></i>
              </router-link>
              <button v-else-if="m.is_active || m.marketplace_type === 'venues'" type="button" class="mph-cta" @click="openUniverse(m)">
                Explorer <i class="fa-solid fa-arrow-right"></i>
              </button>
              <div v-else class="mph-cta-group">
                <button type="button" class="mph-cta ghost" @click="openUniverse(m)">Découvrir</button>
                <button type="button" class="mph-cta" @click="openCheckout(m)"><i class="fa-solid fa-lock-open"></i> S'abonner</button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="mph-section mph-steps">
        <div class="mph-section-head"><h2>Comment ça marche ?</h2></div>
        <ol>
          <li><span>1</span><i class="fa-solid fa-compass"></i><strong>Choisissez</strong><p>Parcourez la boutique ou les prestataires par type d'événement et par métier.</p></li>
          <li><span>2</span><i class="fa-solid fa-file-signature"></i><strong>Comparez & demandez</strong><p>Consultez les avis et réalisations, puis demandez un devis en un clic.</p></li>
          <li><span>3</span><i class="fa-solid fa-calendar-check"></i><strong>Réservez</strong><p>Validez, suivez tout depuis votre espace et échangez via la messagerie.</p></li>
        </ol>
      </section>

      <section class="mph-section mph-benefits">
        <div v-for="b in BENEFITS" :key="b.title" class="mph-benefit">
          <span><i :class="b.icon"></i></span>
          <div><strong>{{ b.title }}</strong><p>{{ b.text }}</p></div>
        </div>
      </section>

      </template>

      <div v-else-if="activeMarketplace" class="ie-tier-strip">
        <router-link :to="{ name: 'premium-marketplace' }" class="ie-btn ie-btn-ghost ie-btn-sm">
          <i class="fa-solid fa-arrow-left"></i> Marketplaces
        </router-link>
        <span v-if="activeMarketplace.is_free" class="ie-tier-strip-text"><i class="fa-solid fa-gift"></i> Accès gratuit, sans abonnement.</span>
        <template v-else-if="!activeMarketplace.is_active">
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
        <span id="mp-universe" class="mph-anchor"></span>
        <div v-if="!activeMarketplace.is_active && !activeMarketplace.is_free" class="ie-mp-upsell-banner">
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
                <img v-if="profile.cover_photo" v-img="profile.cover_photo" :alt="profile.business_name" />
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
          <div class="ie-shop-teaser">
            <div class="ie-shop-teaser-text">
              <span class="ie-shop-teaser-badge"><i class="fa-solid fa-gift"></i> Gratuit · sans abonnement</span>
              <h3>La boutique de l'événementiel</h3>
              <p>Choisissez vos équipements, le total se calcule automatiquement et votre facture est générée immédiatement. Paiement à la livraison.</p>
              <router-link :to="{ name: 'sale-shop' }" class="ie-btn ie-btn-primary">
                <i class="fa-solid fa-bag-shopping"></i> Ouvrir la boutique
              </router-link>
            </div>
            <div v-if="listings.length" class="ie-shop-teaser-products">
              <router-link
                v-for="listing in listings.slice(0, 4)" :key="listing.id"
                :to="{ name: 'sale-product', params: { id: listing.id } }" class="ie-shop-teaser-item"
              >
                <span class="ie-shop-teaser-media">
                  <img v-if="listing.photo" v-img="listing.photo" :alt="listing.title" />
                  <i v-else class="fa-solid fa-box-open"></i>
                </span>
                <strong>{{ listing.title }}</strong>
                <span>{{ Number(listing.price).toLocaleString('fr-FR') }} {{ listing.currency === "XAF" ? "FCFA" : listing.currency }}</span>
              </router-link>
            </div>
          </div>
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
          <div class="mpf">
            <div class="mpf-main">
              <div class="ie-search-input mpf-search">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input v-model="searchFilters.search" :placeholder="$t('marketplace.searchPlaceholder')" @input="onFiltersChanged" />
              </div>
              <select v-model="searchFilters.city" class="ie-select mpf-select" aria-label="Ville" @change="loadProfiles">
                <option value="">{{ $t("marketplace.allCities") }}</option>
                <option v-for="c in CAMEROON_CITIES" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
              <select v-model="searchFilters.ordering" class="ie-select mpf-select" aria-label="Trier" @change="loadProfiles">
                <option value="">{{ $t("marketplace.relevance") }}</option>
                <option value="top_rated">{{ $t("marketplace.topRated") }}</option>
                <option value="newest">{{ $t("marketplace.newest") }}</option>
                <option value="price_asc">{{ $t("marketplace.priceAsc") }}</option>
                <option value="price_desc">{{ $t("marketplace.priceDesc") }}</option>
                <option v-if="nearMe.active" value="nearest">{{ $t("marketplace.nearest") }}</option>
              </select>
              <button type="button" class="mpf-toggle" :class="{ active: filtersOpen || advancedFilterCount }" :aria-expanded="filtersOpen" @click="filtersOpen = !filtersOpen">
                <i class="fa-solid fa-sliders"></i> Filtres
                <span v-if="advancedFilterCount">{{ advancedFilterCount }}</span>
              </button>
            </div>

            <div v-show="filtersOpen" class="mpf-panel">
              <label class="mpf-field">
                <span>Quartier</span>
                <select v-model="searchFilters.neighborhood" class="ie-select" @change="loadProfiles">
                  <option value="">Tout quartier</option>
                  <option v-for="n in neighborhoodOptions" :key="n" :value="n">{{ n }}</option>
                </select>
              </label>
              <label class="mpf-field">
                <span>Disponible le</span>
                <input v-model="searchFilters.available_on" type="date" class="ie-input" @change="loadProfiles" />
              </label>
              <label class="mpf-field">
                <span>Note minimale</span>
                <select v-model="searchFilters.min_rating" class="ie-select" @change="loadProfiles">
                  <option value="">{{ $t("marketplace.allRatings") }}</option>
                  <option value="4">{{ $t("marketplace.ratingAndAbove", { stars: 4 }) }}</option>
                  <option value="3">{{ $t("marketplace.ratingAndAbove", { stars: 3 }) }}</option>
                </select>
              </label>
              <template v-if="activeType === 'interior_design'">
                <label class="mpf-field">
                  <span>Type de client</span>
                  <select v-model="searchFilters.client_type" class="ie-select" @change="loadProfiles">
                    <option value="">Tout type de client</option>
                    <option v-for="c in CLIENT_TYPES" :key="c.value" :value="c.value">{{ c.label }}</option>
                  </select>
                </label>
                <label class="mpf-field">
                  <span>Gamme de prix</span>
                  <select v-model="searchFilters.price_range" class="ie-select" @change="loadProfiles">
                    <option value="">Toute gamme de prix</option>
                    <option v-for="p in PRICE_RANGES" :key="p.value" :value="p.value">{{ p.label }}</option>
                  </select>
                </label>
              </template>
              <div class="mpf-field">
                <span>Proximité</span>
                <div class="mpf-near">
                  <button type="button" class="ie-btn ie-btn-outline" :class="{ 'is-active': nearMe.active }" :disabled="nearMe.loading" @click="useNearMe">
                    <i class="fa-solid" :class="nearMe.loading ? 'fa-spinner fa-spin' : 'fa-location-crosshairs'"></i>
                    {{ nearMe.active ? $t("marketplace.nearMeActive") : $t("marketplace.nearMe") }}
                  </button>
                  <select v-if="nearMe.active" v-model="nearMe.maxDistanceKm" class="ie-select" @change="loadProfiles">
                    <option value="">{{ $t("marketplace.allDistances") }}</option>
                    <option v-for="km in [10, 25, 50, 100]" :key="km" :value="String(km)">{{ $t("marketplace.distanceUpTo", { km }) }}</option>
                  </select>
                </div>
              </div>
              <label class="mpf-check">
                <input type="checkbox" v-model="searchFilters.is_verified" @change="loadProfiles" /> {{ $t("marketplace.verifiedOnly") }}
              </label>
              <button v-if="advancedFilterCount" type="button" class="mpf-reset" @click="resetAdvancedFilters">
                <i class="fa-solid fa-rotate-left"></i> Réinitialiser
              </button>
            </div>
          </div>
          <p v-if="nearMe.error" class="ie-alert ie-alert-danger" style="margin-bottom: 12px;">{{ nearMe.error }}</p>

          <p v-if="!profilesLoading" class="mpf-count"><strong>{{ profiles.length }}</strong> prestataire{{ profiles.length > 1 ? "s" : "" }}{{ selectedCategoryLabel ? ` · ${selectedCategoryLabel}` : "" }}</p>
          <div v-if="profilesLoading" class="ie-catalog-grid">
            <div v-for="i in 6" :key="i" class="ie-skeleton" style="height: 330px; border-radius: 16px;"></div>
          </div>
          <div v-else-if="profiles.length" class="ie-catalog-grid">
            <router-link
              v-for="profile in profiles" :key="profile.id"
              :to="{ name: 'professional-profile-detail', params: { id: profile.id } }"
              class="ie-card ie-pro-card ie-pro-card-lg"
            >
              <div class="ie-pro-cover">
                <img v-if="profile.cover_photo" v-img="profile.cover_photo" :alt="profile.business_name" />
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
      :demo-mode="info.demo_mode"
      @close="checkoutMarketplace = null"
      @subscribed="handleSubscribed"
    />
  </div>
</template>

<style scoped>
/* --- Accueil du Marketplace --- */
.mph-hero {
  display: grid; grid-template-columns: minmax(0, 1fr) 230px; gap: 26px; align-items: center; padding: 38px 40px; border-radius: 20px; color: #fff;
  background: var(--ie-hero-gradient);
  box-shadow: 0 18px 44px #18283b26;
}
.mph-eyebrow { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 999px; background: #ffffff1c; color: #ffe1e1; font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.mph-hero h1 { margin: 14px 0 10px; max-width: 640px; color: #fff; font-size: clamp(26px, 3.6vw, 40px); line-height: 1.1; }
.mph-hero-text > p { margin: 0; max-width: 620px; color: #d6dfe8; font-size: 15px; line-height: 1.6; }
.mph-search { display: flex; align-items: center; max-width: 620px; height: 54px; margin-top: 22px; padding-left: 18px; overflow: hidden; border-radius: 14px; background: #fff; box-shadow: 0 12px 30px #0003; }
.mph-search i { color: var(--ie-muted); }
.mph-search input { flex: 1; min-width: 0; height: 100%; padding: 0 12px; border: 0; color: var(--ie-ink); font-size: 15px; font-family: inherit; }
.mph-search input:focus { outline: none; }
.mph-search button i { display: none; }
.mph-search button { height: 100%; padding: 0 22px; border: 0; background: var(--ie-red); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; font-family: inherit; }
.mph-search button:hover { background: #a11f25; }
.mph-popular { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 14px; font-size: 12.5px; }
.mph-popular span { color: #b9c6d3; }
.mph-popular a { padding: 5px 12px; border: 1px solid #ffffff38; border-radius: 999px; color: #fff; text-decoration: none; font-weight: 600; }
.mph-popular a:hover { background: #ffffff1a; }
.mph-hero-stats { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
.mph-hero-text { min-width: 0; }
.mph-hero-stats li { min-width: 0; display: flex; align-items: baseline; gap: 10px; padding: 12px 16px; border: 1px solid #ffffff22; border-radius: 12px; background: #ffffff10; backdrop-filter: blur(4px); }
.mph-hero-stats strong { font-size: 24px; white-space: nowrap; }
.mph-hero-stats span { color: #c9d4df; font-size: 13px; }

.mph-section { margin-top: 34px; }
.mph-section-head { margin-bottom: 16px; }
.mph-section-head h2 { margin: 0; color: var(--ie-navy); font-size: 22px; }
.mph-section-head p { margin: 4px 0 0; color: var(--ie-muted); font-size: 13.5px; }

.mph-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.mph-card {
  --tone: var(--ie-navy); --tone-soft: var(--ie-navy-soft);
  position: relative; display: flex; flex-direction: column; overflow: hidden; padding: 20px; border: 1px solid var(--ie-line); border-radius: 18px; background: #fff;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.mph-card::before { content: ""; position: absolute; inset: 0 0 auto; height: 5px; background: var(--tone); }
@media (hover: hover) { .mph-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px #18283b1c; } }
.mph-card.is-active { border-color: var(--tone); box-shadow: 0 0 0 2px var(--tone-soft); }
.mph-card.tone-red { --tone: #c0272d; --tone-soft: #f6e2e3; }
.mph-card.tone-navy { --tone: #24384f; --tone-soft: #e3e9f0; }
.mph-card.tone-gold { --tone: #b07a19; --tone-soft: #f7ecd6; }
.mph-card.tone-teal { --tone: #1f7a73; --tone-soft: #dcf0ee; }
.mph-card-top { display: flex; align-items: center; justify-content: space-between; }
.mph-card-icon { display: grid; place-items: center; width: 52px; height: 52px; border-radius: 14px; background: var(--tone-soft); color: var(--tone); font-size: 21px; }
.mph-status { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: #f0f2f5; color: #5d6771; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; }
.mph-status.free { background: var(--ie-success-soft); color: var(--ie-success); }
.mph-status.on { background: var(--tone-soft); color: var(--tone); }
.mph-card h3 { margin: 16px 0 4px; color: var(--ie-ink); font-size: 18px; }
.mph-card-tagline { margin: 0; color: var(--ie-muted); font-size: 13px; line-height: 1.5; }
.mph-card-points { display: grid; gap: 6px; margin: 14px 0 16px; padding: 0; list-style: none; font-size: 13px; color: #3c4b5b; }
.mph-card-points i { width: 16px; color: var(--tone); font-size: 11px; }
.mph-card-foot { display: flex; flex-direction: column; gap: 12px; margin-top: auto; padding-top: 14px; border-top: 1px solid var(--ie-line); }
.mph-card-meta { color: #4b5a6a; font-size: 13px; }
.mph-card-meta strong { color: var(--ie-navy); font-size: 18px; }
.mph-card-meta small { display: block; color: var(--ie-muted); font-size: 12px; }
.mph-cta {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 11px 14px; border: 1px solid var(--tone);
  border-radius: 10px; background: var(--tone); color: #fff; font-size: 13.5px; font-weight: 700; text-decoration: none; cursor: pointer; font-family: inherit;
}
.mph-cta:hover { filter: brightness(1.1); }
.mph-cta.ghost { background: #fff; color: var(--tone); }
.mph-cta-group { display: grid; grid-template-columns: 1fr 1.3fr; gap: 8px; }

.mph-steps ol { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 0; padding: 0; list-style: none; counter-reset: none; }
.mph-steps li { position: relative; display: flex; flex-direction: column; gap: 6px; padding: 22px; border: 1px solid var(--ie-line); border-radius: 16px; background: #fff; }
.mph-steps li > span { position: absolute; top: 16px; right: 18px; color: #e9ecf0; font-size: 42px; font-weight: 900; line-height: 1; }
.mph-steps li > i { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 12px; background: var(--ie-red-soft); color: var(--ie-red); font-size: 18px; }
.mph-steps strong { margin-top: 6px; color: var(--ie-navy); font-size: 16px; }
.mph-steps p { margin: 0; color: var(--ie-muted); font-size: 13px; line-height: 1.5; }

.mph-benefits { display: grid; grid-template-columns: repeat(4, 1fr); overflow: hidden; border: 1px solid var(--ie-line); border-radius: 16px; background: #fff; }
.mph-benefit { display: flex; gap: 12px; padding: 18px; }
.mph-benefit + .mph-benefit { border-left: 1px solid var(--ie-line); }
.mph-benefit > span { display: grid; place-items: center; width: 40px; height: 40px; flex: 0 0 40px; border-radius: 10px; background: var(--ie-navy-soft); color: var(--ie-navy); }
.mph-benefit strong { color: var(--ie-navy); font-size: 13.5px; }
.mph-benefit p { margin: 3px 0 0; color: var(--ie-muted); font-size: 12.5px; line-height: 1.45; }

.mph-anchor { display: block; scroll-margin-top: 12px; height: 1px; margin-top: 30px; }

@media (max-width: 1100px) {
  .mph-cards { grid-template-columns: repeat(2, 1fr); }
  .mph-benefits { grid-template-columns: repeat(2, 1fr); }
  .mph-benefit:nth-child(3) { border-left: 0; }
  .mph-benefit:nth-child(n + 3) { border-top: 1px solid var(--ie-line); }
}
@media (max-width: 860px) {
  .mph-hero { grid-template-columns: minmax(0, 1fr); padding: 24px 18px; border-radius: 16px; }
  .mph-hero-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .mph-hero-stats li { flex-direction: column; align-items: flex-start; gap: 0; padding: 10px 12px; }
  .mph-hero-stats strong { font-size: 20px; white-space: nowrap; }
  .mph-steps ol { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .mph-cards, .mph-benefits { grid-template-columns: 1fr; }
  .mph-benefit { border-left: 0 !important; }
  .mph-benefit + .mph-benefit { border-top: 1px solid var(--ie-line); }
  .mph-search { height: 48px; padding-left: 14px; }
  .mph-search button { width: 50px; padding: 0; }
  .mph-search button span { display: none; }
  .mph-search button i { display: inline; }
  .mph-hero h1 { font-size: 24px; }
  .mph-hero-text > p { font-size: 14px; }
  .mph-cta-group { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) { .mph-card { transition: none; } }

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
.ie-mp-access-btn { background: var(--ie-navy); text-decoration: none; justify-content: center; }
.ie-mp-access-btn:hover { background: #2b394a !important; }
.ie-mp-free { color: var(--ie-success) !important; font-weight: 700; }
.ie-shop-teaser {
  display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: 24px; align-items: center; padding: 26px;
  border-radius: 18px; color: #fff; background: var(--ie-hero-gradient);
}
.ie-shop-teaser-badge { display: inline-flex; align-items: center; gap: 7px; padding: 5px 11px; border-radius: 999px; background: #ffffff1c; color: #ffe1e1; font-size: 11px; font-weight: 800; text-transform: uppercase; }
.ie-shop-teaser h3 { margin: 12px 0 8px; font-size: 24px; color: #fff; }
.ie-shop-teaser p { margin: 0 0 16px; color: #dfe6ee; font-size: 13.5px; line-height: 1.55; }
.ie-shop-teaser-products { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.ie-shop-teaser-item { display: flex; flex-direction: column; gap: 4px; padding: 8px; border-radius: 12px; background: #fff; color: var(--ie-ink); text-decoration: none; min-width: 0; }
.ie-shop-teaser-media { display: grid; place-items: center; aspect-ratio: 1; overflow: hidden; border-radius: 8px; background: #f2f4f6; color: #b4bcc4; font-size: 22px; }
.ie-shop-teaser-media img { width: 100%; height: 100%; object-fit: cover; }
.ie-shop-teaser-item strong { font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ie-shop-teaser-item > span:last-child { color: var(--ie-navy); font-size: 12px; font-weight: 800; }
@media (max-width: 860px) {
  .ie-shop-teaser { grid-template-columns: 1fr; padding: 20px; }
  .ie-shop-teaser-products { grid-template-columns: repeat(2, 1fr); }
}

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

.ie-category-groups { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 16px; }
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
.ie-event-type-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr)); gap: 12px; }
.ie-event-type-card {
  display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center;
  background: #fff; border: 1px solid var(--ie-line); border-radius: 12px; padding: 22px 16px;
  cursor: pointer; transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  font-size: 13px; font-weight: 600; color: var(--ie-navy);
}
.ie-event-type-card i { font-size: 24px; color: var(--ie-red); }
@media (hover: hover) { .ie-event-type-card:hover { border-color: var(--ie-navy); box-shadow: 0 8px 20px rgba(57, 73, 91, 0.12); transform: translateY(-2px); } }
@media (max-width: 700px) { .ie-event-type-grid { grid-template-columns: repeat(2, 1fr); } }

.ie-catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)); gap: 18px; }

/* Barre de recherche des prestataires */
.mpf { margin-bottom: 14px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; box-shadow: var(--ie-shadow-sm); }
.mpf-main { display: grid; grid-template-columns: minmax(0, 1fr) 180px 180px auto; gap: 10px; padding: 12px; }
.mpf-search { min-width: 0 !important; }
.mpf-select { width: 100%; }
.mpf-toggle {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 0 16px; border: 1px solid var(--ie-line); border-radius: 8px;
  background: #fff; color: var(--ie-navy); font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit; white-space: nowrap;
}
.mpf-toggle.active { border-color: var(--ie-navy); background: var(--ie-navy-soft); }
.mpf-toggle span { display: grid; place-items: center; min-width: 20px; height: 20px; padding: 0 5px; border-radius: 999px; background: var(--ie-red); color: #fff; font-size: 11px; }
.mpf-panel { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px 14px; align-items: end; padding: 14px 12px; border-top: 1px solid var(--ie-line); background: #fafbfc; border-radius: 0 0 14px 14px; }
.mpf-field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.mpf-field > span { color: var(--ie-muted); font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }
.mpf-near { display: flex; gap: 6px; }
.mpf-near .ie-btn { flex: 1; justify-content: center; white-space: nowrap; }
.mpf-near .ie-btn.is-active { background: var(--ie-navy); color: #fff; border-color: var(--ie-navy); }
.mpf-near .ie-select { flex: 1; min-width: 0; }
.mpf-check { display: flex; align-items: center; gap: 8px; min-height: 40px; color: var(--ie-ink); font-size: 13px; cursor: pointer; }
.mpf-check input { width: 16px; height: 16px; accent-color: var(--ie-red); }
.mpf-reset { justify-self: start; min-height: 40px; padding: 0; border: 0; background: none; color: var(--ie-red); font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit; }
.mpf-count { margin: 0 0 12px; color: var(--ie-muted); font-size: 13px; }
.mpf-count strong { color: var(--ie-navy); }
@media (max-width: 900px) {
  .mpf-main { grid-template-columns: 1fr 1fr; }
  .mpf-search { grid-column: 1 / -1; }
  .mpf-toggle { grid-column: 1 / -1; min-height: 40px; }
}
@media (max-width: 560px) {
  .mpf-main { padding: 10px; gap: 8px; }
  .mpf-panel { grid-template-columns: 1fr; padding: 12px 10px; }
}
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
@media (hover: hover) {
  .ie-pro-card:hover { transform: translateY(-4px); box-shadow: 0 16px 32px rgba(23, 27, 38, 0.14); border-color: var(--ie-line); }
}
.ie-pro-card { border-radius: 16px; }
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
.ie-pro-card-lg .ie-pro-cover { height: auto; aspect-ratio: 16 / 10; overflow: hidden; }
.ie-pro-card-lg .ie-pro-cover img { position: absolute; inset: 0; }
.ie-pro-card-lg .ie-pro-card-body { padding: 14px 16px 16px; }
.ie-pro-card-lg .ie-pro-name { margin-top: 0; font-size: 15.5px; }
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
.ie-pro-bottom-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px 10px; margin-top: auto; }
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
