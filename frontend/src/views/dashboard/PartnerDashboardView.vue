<script setup>
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import SubscriptionCheckoutModal from "../../components/SubscriptionCheckoutModal.vue";
import { ACTOR_CATEGORY_GROUPS, OTHER_CATEGORY_GROUP } from "../../data/actorCategories";
import { citiesForCountry, COUNTRIES, findCityCoords } from "../../data/countries";
import { CLIENT_TYPES, INTERIOR_DESIGN_CATEGORY_GROUPS, INTERIOR_DESIGN_OTHER_CATEGORY_GROUP, PRICE_RANGES } from "../../data/interiorDesignCategories";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";
import { useMarketplaceAccessStore } from "../../stores/marketplaceAccess";

const ACTOR_PROVIDER_CATEGORY_GROUPS = [...ACTOR_CATEGORY_GROUPS, OTHER_CATEGORY_GROUP];
const INTERIOR_PROVIDER_CATEGORY_GROUPS = [...INTERIOR_DESIGN_CATEGORY_GROUPS, INTERIOR_DESIGN_OTHER_CATEGORY_GROUP];

const MARKETPLACE_TYPES = [
  { value: "interior_design", label: "Décoration & design intérieur", icon: "fa-solid fa-couch", hint: "Vous proposez de la décoration ou du design d'intérieur.", kind: "profile" },
  { value: "actors", label: "Marketplace des acteurs", icon: "fa-solid fa-people-group", hint: "Vous êtes un professionnel de l'événementiel (DJ, traiteur, photographe...).", kind: "profile" },
];

const loading = ref(true);
const subscriptionInfo = reactive({ price: 0, currency: "XAF", duration_days: 30, plans: [], marketplaces: [], tiers: [] });
const myProfile = ref(null);
const myListing = ref(null);

const chosenType = ref("actors");
const chosenMeta = computed(() => MARKETPLACE_TYPES.find((t) => t.value === chosenType.value));
const chosenSubscription = computed(() => subscriptionInfo.marketplaces.find((m) => m.marketplace_type === chosenType.value));
// Le sélecteur « Type d'activité » doit proposer les métiers de la
// marketplace choisie — pas la liste des métiers événementiels pour un
// profil de décoration/design intérieur (et inversement).
const PROVIDER_CATEGORY_GROUPS = computed(() =>
  chosenType.value === "interior_design" ? INTERIOR_PROVIDER_CATEGORY_GROUPS : ACTOR_PROVIDER_CATEGORY_GROUPS
);

const checkoutType = ref(null);
const checkoutLabel = computed(() => MARKETPLACE_TYPES.find((t) => t.value === checkoutType.value)?.label || "");
async function loadPlansForMarketplace(type) {
  const { data } = await api.get("/marketplace/subscriptions/", { params: { marketplace_type: type } });
  subscriptionInfo.plans = data.plans || [];
  subscriptionInfo.tiers = data.tiers || [];
  subscriptionInfo.price = data.price || 0;
  subscriptionInfo.duration_days = data.duration_days || 30;
  subscriptionInfo.currency = data.currency || "XAF";
}
async function openCheckout(type) {
  try {
    await loadPlansForMarketplace(type);
    if (!subscriptionInfo.plans.length) return;
    checkoutType.value = type;
  } catch {
    // L'état actuel reste affiché ; le formulaire de souscription n'est ouvert
    // que si l'API a retourné une formule tarifaire utilisable.
  }
}
const marketplaceAccess = useMarketplaceAccessStore();

async function handleSubscribed() {
  checkoutType.value = null;
  await loadData();
  await marketplaceAccess.refresh();
}

// --- Profil professionnel (décoration/design intérieur, acteurs) -----------
const profileForm = reactive({
  marketplace_type: "actors", category: "decoration", business_name: "", description: "", team_presentation: "",
  specialties: "", country: "CM", city: "", neighborhood: "", service_area: "", client_type: "", price_range: "", conditions: "",
  contact_phone: "", contact_email: "", facebook_url: "", instagram_url: "", website_url: "",
  latitude: null, longitude: null, max_distance_km: 50,
});
const citiesForSelectedCountry = computed(() => citiesForCountry(profileForm.country));

function selectMarketplaceType(value) {
  chosenType.value = value;
  // Seulement à la création (pas de profil existant) : la catégorie par
  // défaut doit correspondre à la marketplace choisie, sinon le sélecteur
  // affiche une catégorie qui n'appartient pas à la liste visible.
  if (!myProfile.value) {
    profileForm.category = value === "interior_design" ? "interior_decorator" : "decoration";
  }
  loadPlansForMarketplace(value).catch(() => {});
}

function applyCityCoords() {
  const coords = findCityCoords(profileForm.country, profileForm.city);
  if (coords) {
    profileForm.latitude = coords.lat;
    profileForm.longitude = coords.lng;
  }
}
const logoFile = ref(null);
const coverFile = ref(null);
const idCardFile = ref(null);
const profileSubmitting = ref(false);
const profileError = ref("");
const showProfileForm = ref(false);

const serviceForm = reactive({ name: "", description: "", pricing_type: "quote", price_from: null, currency: "XAF", duration_label: "", capacity: null, conditions: "" });
const servicePhotoFile = ref(null);
const showServiceForm = ref(false);
const serviceSubmitting = ref(false);

const portfolioFiles = ref([]);
const portfolioBeforeFile = ref(null);
const portfolioCaption = ref("");
const portfolioSubmitting = ref(false);
const portfolioError = ref("");

// --- Marketplace vente (annonce simple, inchangé) ---------------------------
const listingForm = reactive({ marketplace_type: "sale", title: "", description: "", price: 0, currency: "XAF" });
const listingPhotoFile = ref(null);
const listingSubmitting = ref(false);
const listingError = ref("");

async function loadData() {
  loading.value = true;
  try {
    const [subRes, profilesRes, listingsRes] = await Promise.all([
      api.get("/marketplace/subscriptions/"),
      api.get("/marketplace/profiles/"),
      api.get("/marketplace/listings/"),
    ]);
    Object.assign(subscriptionInfo, subRes.data);
    const profiles = profilesRes.data.results || profilesRes.data;
    const ownProfileSummary = profiles.find((p) => p.is_owner) || null;
    const listings = listingsRes.data.results || listingsRes.data;
    myListing.value = listings.find((l) => l.is_owner) || null;
    if (ownProfileSummary) {
      const { data } = await api.get(`/marketplace/profiles/${ownProfileSummary.id}/`);
      myProfile.value = data;
      chosenType.value = myProfile.value.marketplace_type;
      Object.assign(profileForm, myProfile.value);
    } else if (myListing.value) {
      chosenType.value = myListing.value.marketplace_type;
    }
    await loadPlansForMarketplace(chosenType.value);
  } finally {
    loading.value = false;
  }
}


function onLogoChange(e) { logoFile.value = e.target.files[0] || null; }
function onCoverChange(e) { coverFile.value = e.target.files[0] || null; }
function onIdCardChange(e) { idCardFile.value = e.target.files[0] || null; }

function buildProfilePayload() {
  const base = { ...profileForm, marketplace_type: chosenType.value };
  if (!logoFile.value && !coverFile.value && !idCardFile.value) return base;
  const payload = new FormData();
  Object.entries(base).forEach(([key, value]) => { if (value != null) payload.append(key, value); });
  if (logoFile.value) payload.append("logo", logoFile.value);
  if (coverFile.value) payload.append("cover_photo", coverFile.value);
  if (idCardFile.value) payload.append("id_card_photo", idCardFile.value);
  return payload;
}

async function saveProfile() {
  profileError.value = "";
  profileSubmitting.value = true;
  try {
    const payload = buildProfilePayload();
    if (myProfile.value) {
      const { data } = await api.patch(`/marketplace/profiles/${myProfile.value.id}/`, payload);
      myProfile.value = data;
    } else {
      const { data } = await api.post("/marketplace/profiles/", payload);
      myProfile.value = data;
    }
    showProfileForm.value = false;
    logoFile.value = null;
    coverFile.value = null;
    idCardFile.value = null;
  } catch (e) {
    profileError.value = e?.response?.data?.marketplace_type?.[0] || e?.response?.data?.detail || "Impossible d'enregistrer votre profil.";
  } finally {
    profileSubmitting.value = false;
  }
}

function startCreateService() {
  Object.assign(serviceForm, { name: "", description: "", pricing_type: "quote", price_from: null, currency: "XAF", duration_label: "", capacity: null, conditions: "" });
  servicePhotoFile.value = null;
  showServiceForm.value = true;
}

function onServicePhotoChange(e) { servicePhotoFile.value = e.target.files[0] || null; }

async function addService() {
  serviceSubmitting.value = true;
  try {
    const base = { ...serviceForm, profile: myProfile.value.id };
    let payload = base;
    if (servicePhotoFile.value) {
      payload = new FormData();
      Object.entries(base).forEach(([key, value]) => { if (value != null) payload.append(key, value); });
      payload.append("photo", servicePhotoFile.value);
    }
    const { data } = await api.post("/marketplace/services/", payload);
    myProfile.value.services.push(data);
    showServiceForm.value = false;
  } finally {
    serviceSubmitting.value = false;
  }
}

async function removeService(service) {
  if (!confirm(`Supprimer le service « ${service.name} » ?`)) return;
  await api.delete(`/marketplace/services/${service.id}/`);
  myProfile.value.services = myProfile.value.services.filter((s) => s.id !== service.id);
}

function onPortfolioChange(e) { portfolioFiles.value = Array.from(e.target.files || []); }
function onPortfolioBeforeChange(e) { portfolioBeforeFile.value = e.target.files[0] || null; }

async function addPortfolioItems(event) {
  if (!portfolioFiles.value.length) return;
  portfolioSubmitting.value = true;
  let added = 0;
  try {
    // Un envoi par photo : une photo refusée n'empêche pas les autres. La
    // photo « avant » ne s'applique que lorsqu'une seule photo « après » est
    // choisie (une paire avant/après = une réalisation).
    const withBefore = portfolioBeforeFile.value && portfolioFiles.value.length === 1;
    for (const file of portfolioFiles.value) {
      const payload = new FormData();
      payload.append("profile", myProfile.value.id);
      payload.append("caption", portfolioCaption.value);
      payload.append("image", file);
      if (withBefore) payload.append("before_image", portfolioBeforeFile.value);
      try {
        const { data } = await api.post("/marketplace/portfolio-items/", payload);
        myProfile.value.portfolio_items.push(data);
        added += 1;
      } catch (e) {
        portfolioError.value = `« ${file.name} » n'a pas pu être ajoutée.`;
      }
    }
    if (added === portfolioFiles.value.length) portfolioError.value = "";
    portfolioFiles.value = [];
    portfolioBeforeFile.value = null;
    portfolioCaption.value = "";
    if (event?.target?.form) event.target.form.reset();
  } finally {
    portfolioSubmitting.value = false;
  }
}

const lightbox = useLightboxStore();
function openPortfolio(index) {
  lightbox.openGallery(myProfile.value.portfolio_items.map((p) => ({ url: p.image, caption: p.caption })), index);
}

// --- Complétude du profil (accueil) ------------------------------------------
// Ce qui rend une fiche convaincante pour les clients, avec l'action qui
// permet de le compléter directement depuis l'accueil.
const MIN_PORTFOLIO = 3;
const profileChecklist = computed(() => {
  const p = myProfile.value;
  if (!p) return [];
  return [
    { key: "cover", label: "Photo de couverture", done: Boolean(p.cover_photo), action: "profile" },
    { key: "description", label: "Description de votre activité", done: Boolean(p.description?.trim()), action: "profile" },
    { key: "specialties", label: "Spécialités", done: Boolean(p.specialties?.trim()), action: "profile" },
    { key: "city", label: "Ville d'activité", done: Boolean(p.city), action: "profile" },
    { key: "contact", label: "Téléphone professionnel", done: Boolean(p.contact_phone), action: "profile" },
    { key: "services", label: "Au moins un service", done: p.services.length > 0, action: "service" },
    {
      key: "portfolio",
      label: `Au moins ${MIN_PORTFOLIO} réalisations (${Math.min(p.portfolio_items.length, MIN_PORTFOLIO)}/${MIN_PORTFOLIO})`,
      done: p.portfolio_items.length >= MIN_PORTFOLIO,
      action: "portfolio",
    },
  ];
});
const profileCompletion = computed(() => {
  const items = profileChecklist.value;
  return items.length ? Math.round((items.filter((i) => i.done).length / items.length) * 100) : 0;
});
const missingChecklist = computed(() => profileChecklist.value.filter((i) => !i.done));

// Certification : la CNI est facultative, mais c'est elle qui déclenche la
// demande de vérification examinée par l'administration.
const certification = computed(() => {
  const p = myProfile.value;
  if (!p) return null;
  if (p.verification_status !== "not_verified") {
    return { tone: "ok", icon: "fa-solid fa-circle-check", title: `Compte certifié · ${p.verification_status_display}`, text: "Ce badge est affiché sur votre fiche et inspire confiance aux clients." };
  }
  if (p.verification_requested_at) {
    return { tone: "pending", icon: "fa-solid fa-hourglass-half", title: "Vérification en cours", text: "Votre CNI a bien été reçue. L'équipe InnovEvent examine votre profil pour le certifier." };
  }
  if (p.id_card_photo) {
    return { tone: "idle", icon: "fa-solid fa-shield-halved", title: "Compte non certifié", text: "Votre demande n'a pas été validée. Envoyez une photo de CNI plus lisible pour relancer la vérification.", cta: "Renvoyer ma CNI" };
  }
  return { tone: "idle", icon: "fa-solid fa-shield-halved", title: "Faites certifier votre compte", text: "Facultatif : envoyez une photo de votre CNI. L'administration vérifie votre profil et vous attribue le badge « Vérifié ».", cta: "Ajouter ma CNI" };
});

async function completeItem(item) {
  let target = "partner-profile-card";
  if (item.action === "profile") showProfileForm.value = true;
  if (item.action === "service") {
    if (!showServiceForm.value) startCreateService();
    target = "partner-services";
  }
  if (item.action === "portfolio") target = "partner-portfolio";
  await nextTick();
  document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function removePortfolioItem(item) {
  await api.delete(`/marketplace/portfolio-items/${item.id}/`);
  myProfile.value.portfolio_items = myProfile.value.portfolio_items.filter((i) => i.id !== item.id);
}

// --- Marketplace vente ---
function onListingPhotoChange(e) { listingPhotoFile.value = e.target.files[0] || null; }

function buildListingPayload() {
  const base = { ...listingForm, marketplace_type: "sale" };
  if (!listingPhotoFile.value) return base;
  const payload = new FormData();
  Object.entries(base).forEach(([key, value]) => payload.append(key, value));
  payload.append("photo", listingPhotoFile.value);
  return payload;
}

async function saveListing() {
  listingError.value = "";
  listingSubmitting.value = true;
  try {
    const payload = buildListingPayload();
    if (myListing.value) {
      const { data } = await api.patch(`/marketplace/listings/${myListing.value.id}/`, payload);
      myListing.value = data;
    } else {
      const { data } = await api.post("/marketplace/listings/", payload);
      myListing.value = data;
    }
  } catch (e) {
    listingError.value = e?.response?.data?.detail || "Impossible d'enregistrer votre annonce.";
  } finally {
    listingSubmitting.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <h1><i class="fa-solid fa-handshake" style="color: var(--ie-red); margin-right: 8px;"></i>Mon espace prestataire</h1>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <!-- Aucun profil ni annonce : choix du marketplace -->
    <div v-else-if="!myProfile && !myListing" class="ie-card ie-card-body">
      <h2 style="margin-bottom: 6px;">Rejoindre un marketplace InnovEvent</h2>
      <p class="ie-page-subtitle" style="margin-bottom: 18px;">
        Choisissez le marketplace correspondant à votre activité, puis abonnez-vous pour publier votre profil professionnel.
      </p>

      <div class="ie-mp-choice-grid">
        <div v-for="t in MARKETPLACE_TYPES" :key="t.value" class="ie-mp-choice-card" :class="{ 'is-active': chosenType === t.value }">
          <button type="button" class="ie-mp-choice-select" @click="selectMarketplaceType(t.value)">
            <span class="ie-mp-choice-icon"><i :class="t.icon"></i></span>
            <span class="ie-mp-choice-title">{{ t.label }}</span>
            <span class="ie-mp-choice-hint">{{ t.hint }}</span>
          </button>
        </div>
      </div>

      <template v-if="chosenSubscription">
        <div v-if="chosenSubscription.is_active" class="ie-alert ie-alert-success" style="margin-top: 16px;">
          <i class="fa-solid fa-circle-check"></i> Abonnement actif jusqu'au {{ new Date(chosenSubscription.expires_at).toLocaleDateString('fr-FR') }} —
          {{ chosenMeta.kind === 'profile' ? 'créez votre profil professionnel ci-dessous.' : 'publiez votre annonce ci-dessous.' }}
        </div>
        <template v-else>
          <p v-if="subscriptionInfo.plans.length" class="ie-field-hint" style="margin: 0 0 10px;">À partir de {{ Number(subscriptionInfo.plans[0].price).toLocaleString('fr-FR') }} {{ subscriptionInfo.currency }}.</p>
          <p v-else class="ie-field-hint" style="margin: 0 0 10px;">Aucune formule tarifaire n’est configurée pour ce Marketplace.</p>
          <button class="ie-btn ie-btn-marketplace" :disabled="!subscriptionInfo.plans.length" @click="openCheckout(chosenType)">
            <i class="fa-solid fa-lock-open"></i> S'abonner à « {{ chosenMeta.label }} »
          </button>
        </template>
      </template>

      <!-- Création du profil professionnel (décoration/design intérieur, acteurs) -->
      <form v-if="chosenSubscription?.is_active && chosenMeta.kind === 'profile'" @submit.prevent="saveProfile" style="margin-top: 20px; border-top: 1px solid var(--ie-line); padding-top: 20px;">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom de votre entreprise / activité</label>
            <input v-model="profileForm.business_name" class="ie-input" required placeholder="Ex : Aline Déco Events" />
          </div>
          <div>
            <label class="ie-label">Type d'activité</label>
            <select v-model="profileForm.category" class="ie-select">
              <optgroup v-for="g in PROVIDER_CATEGORY_GROUPS" :key="g.title" :label="g.title">
                <option v-for="c in g.items" :key="c.value" :value="c.value">{{ c.label }}</option>
              </optgroup>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="profileForm.description" class="ie-input" rows="3" placeholder="Présentez votre activité, votre expérience..."></textarea>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Photo de profil <span class="ie-optional">(facultatif)</span></label>
            <input type="file" accept="image/*" class="ie-input" @change="onLogoChange" />
            <p class="ie-field-hint">Le logo ou votre photo — affiché sur votre carte dans le marketplace.</p>
          </div>
          <div>
            <label class="ie-label">Photo de couverture</label>
            <input type="file" accept="image/*" class="ie-input" @change="onCoverChange" />
          </div>
        </div>
        <p v-if="profileError" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ profileError }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="profileSubmitting">
          {{ profileSubmitting ? "Publication…" : "Créer mon profil professionnel" }}
        </button>
      </form>

      <!-- Création de l'annonce vente (inchangé) -->
      <form v-if="chosenSubscription?.is_active && chosenMeta.kind === 'listing'" @submit.prevent="saveListing" style="margin-top: 20px; border-top: 1px solid var(--ie-line); padding-top: 20px;">
        <label class="ie-label">Titre de votre offre</label>
        <input v-model="listingForm.title" class="ie-input" required placeholder="Ex : Chaises Chiavari dorées (lot de 50)" />
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="listingForm.description" class="ie-input" rows="3"></textarea>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix</label>
            <input v-model.number="listingForm.price" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Devise</label>
            <select v-model="listingForm.currency" class="ie-select">
              <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onListingPhotoChange" />
        <p v-if="listingError" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ listingError }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="listingSubmitting">
          {{ listingSubmitting ? "Publication…" : "Publier mon annonce" }}
        </button>
      </form>
    </div>

    <!-- Annonce vente déjà publiée -->
    <div v-else-if="myListing" class="ie-card ie-card-body">
      <h2 style="margin-bottom: 16px;">Mon annonce — {{ myListing.marketplace_type === 'sale' ? 'Marketplace vente' : myListing.marketplace_type }}</h2>
      <form @submit.prevent="saveListing">
        <label class="ie-label">Titre</label>
        <input v-model="listingForm.title" class="ie-input" required />
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="listingForm.description" class="ie-input" rows="3"></textarea>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix</label>
            <input v-model.number="listingForm.price" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Devise</label>
            <select v-model="listingForm.currency" class="ie-select">
              <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onListingPhotoChange" />
        <p v-if="listingError" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ listingError }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="listingSubmitting">
          {{ listingSubmitting ? "Enregistrement…" : "Mettre à jour" }}
        </button>
      </form>
    </div>

    <!-- Profil professionnel déjà créé : édition + services + portfolio -->
    <template v-else-if="myProfile">
      <div v-if="certification" class="ie-certif" :class="certification.tone">
        <span class="ie-certif-icon"><i :class="certification.icon"></i></span>
        <div class="ie-certif-text">
          <strong>{{ certification.title }}</strong>
          <p>{{ certification.text }}</p>
        </div>
        <button v-if="certification.cta" type="button" class="ie-btn ie-btn-primary ie-btn-sm" @click="completeItem({ action: 'profile' })">
          <i class="fa-solid fa-id-card"></i> {{ certification.cta }}
        </button>
      </div>

      <div v-if="missingChecklist.length" class="ie-card ie-card-body ie-completion">
        <div class="ie-completion-head">
          <div class="ie-completion-ring" :style="{ '--pct': profileCompletion }"><span>{{ profileCompletion }}%</span></div>
          <div>
            <h2>Complétez votre profil</h2>
            <p>Une fiche complète inspire confiance et reçoit plus de demandes de devis. Il vous reste {{ missingChecklist.length }} élément{{ missingChecklist.length > 1 ? "s" : "" }} à ajouter.</p>
          </div>
        </div>
        <ul class="ie-completion-list">
          <li v-for="item in profileChecklist" :key="item.key" :class="{ done: item.done }">
            <i class="fa-solid" :class="item.done ? 'fa-circle-check' : 'fa-circle-plus'"></i>
            <span>{{ item.label }}</span>
            <button v-if="!item.done" type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="completeItem(item)">Ajouter</button>
          </li>
        </ul>
      </div>

      <div id="partner-profile-card" class="ie-card" style="overflow: hidden;">
        <div v-if="!showProfileForm">
          <div class="ie-partner-cover" :class="{ 'has-photo': myProfile.cover_photo }">
            <img v-if="myProfile.cover_photo" v-img="myProfile.cover_photo" :alt="myProfile.business_name" />
            <div class="ie-partner-cover-actions">
              <span v-if="myProfile.is_verified" class="ie-badge ie-badge-success"><i class="fa-solid fa-circle-check"></i> Vérifié</span>
              <router-link
                :to="{ name: 'professional-profile-detail', params: { id: myProfile.id } }" target="_blank"
                class="ie-btn ie-btn-ghost ie-btn-sm"
              >
                <i class="fa-solid fa-eye"></i> Voir ma fiche publique
              </router-link>
              <button class="ie-btn ie-btn-primary ie-btn-sm" @click="showProfileForm = true">
                <i class="fa-solid fa-pen"></i> Modifier
              </button>
            </div>
          </div>
          <div class="ie-partner-identity">
            <div class="ie-partner-avatar">
              <img v-if="myProfile.logo" v-img="myProfile.logo" :alt="myProfile.business_name" />
              <i v-else class="fa-solid fa-handshake"></i>
            </div>
            <div class="ie-card-body" style="flex: 1; padding-top: 10px;">
              <span class="ie-badge ie-badge-neutral">{{ myProfile.category_display }} · {{ myProfile.marketplace_label }}</span>
              <h2 style="margin: 8px 0 6px;">{{ myProfile.business_name }}</h2>
              <p style="color: var(--ie-muted); font-size: 13px; margin: 0 0 8px; max-width: 620px;">{{ myProfile.description || "Aucune description." }}</p>
              <p v-if="myProfile.city" style="font-size: 12.5px; color: var(--ie-ink); margin: 0 0 8px;"><i class="fa-solid fa-location-dot" style="color: var(--ie-red);"></i> {{ [myProfile.neighborhood, myProfile.city].filter(Boolean).join(', ') }}</p>
              <span class="ie-badge" :class="myProfile.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ myProfile.is_active ? "Visible dans le marketplace" : "Masqué par l'administration" }}</span>
              <template v-if="!chosenSubscription?.is_active">
                <button class="ie-btn ie-btn-marketplace ie-btn-sm" style="margin-top: 10px; display: block;" @click="openCheckout(myProfile.marketplace_type)">
                  <i class="fa-solid fa-arrows-rotate"></i> Renouveler mon abonnement
                </button>
              </template>
            </div>
          </div>
        </div>

        <form v-else @submit.prevent="saveProfile" class="ie-card-body">
          <div class="ie-page-header-actions" style="justify-content: space-between; margin-bottom: 16px;">
            <h2 style="margin: 0;">Modifier mon profil professionnel</h2>
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="showProfileForm = false"><i class="fa-solid fa-xmark"></i> Fermer</button>
          </div>
          <div class="ie-form-row">
            <div>
              <label class="ie-label">Nom de votre entreprise / activité</label>
              <input v-model="profileForm.business_name" class="ie-input" required />
            </div>
            <div>
              <label class="ie-label">Type d'activité</label>
              <select v-model="profileForm.category" class="ie-select">
                <optgroup v-for="g in PROVIDER_CATEGORY_GROUPS" :key="g.title" :label="g.title">
                <option v-for="c in g.items" :key="c.value" :value="c.value">{{ c.label }}</option>
              </optgroup>
              </select>
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Description</label>
          <textarea v-model="profileForm.description" class="ie-input" rows="3"></textarea>
          <label class="ie-label" style="margin-top: 14px;">Présentation de l'équipe</label>
          <textarea v-model="profileForm.team_presentation" class="ie-input" rows="2"></textarea>
          <label class="ie-label" style="margin-top: 14px;">Spécialités (séparées par des virgules)</label>
          <input v-model="profileForm.specialties" class="ie-input" placeholder="Ex : Mariages, Galas, Anniversaires" />
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Pays</label>
              <select v-model="profileForm.country" class="ie-select" @change="profileForm.city = ''">
                <option v-for="c in COUNTRIES" :key="c.code" :value="c.code">{{ c.name }}</option>
              </select>
            </div>
            <div>
              <label class="ie-label">Ville</label>
              <input v-model="profileForm.city" list="ie-city-list" class="ie-input" @change="applyCityCoords" />
              <datalist id="ie-city-list">
                <option v-for="c in citiesForSelectedCountry" :key="c.name" :value="c.name" />
              </datalist>
              <p v-if="profileForm.latitude" class="ie-field-hint"><i class="fa-solid fa-location-dot"></i> Position enregistrée pour la recherche « près de moi ».</p>
            </div>
            <div>
              <label class="ie-label">Quartier</label>
              <input v-model="profileForm.neighborhood" class="ie-input" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Zone d'intervention</label>
          <input v-model="profileForm.service_area" class="ie-input" placeholder="Ex : Yaoundé, Douala et environs" />
          <label class="ie-label" style="margin-top: 14px;">Distance maximale d'intervention (km)</label>
          <input v-model.number="profileForm.max_distance_km" type="number" min="0" class="ie-input" placeholder="Ex : 50" />
          <div v-if="profileForm.marketplace_type === 'interior_design'" class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Type de client</label>
              <select v-model="profileForm.client_type" class="ie-select">
                <option value="">—</option>
                <option v-for="c in CLIENT_TYPES" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
            </div>
            <div>
              <label class="ie-label">Gamme de prix</label>
              <select v-model="profileForm.price_range" class="ie-select">
                <option value="">—</option>
                <option v-for="p in PRICE_RANGES" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Conditions de prestation</label>
          <textarea v-model="profileForm.conditions" class="ie-input" rows="2"></textarea>
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Téléphone professionnel</label>
              <input v-model="profileForm.contact_phone" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Email professionnel</label>
              <input v-model="profileForm.contact_email" type="email" class="ie-input" />
            </div>
          </div>
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Logo / photo de profil <span class="ie-optional">(facultatif)</span></label>
              <input type="file" accept="image/*" class="ie-input" @change="onLogoChange" />
            </div>
            <div>
              <label class="ie-label">Photo de couverture</label>
              <input type="file" accept="image/*" class="ie-input" @change="onCoverChange" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">
            Photo de votre CNI <span class="ie-optional">(facultatif — pour certifier votre compte)</span>
          </label>
          <input type="file" accept="image/*" class="ie-input" style="max-width: 320px;" @change="onIdCardChange" />
          <p class="ie-field-hint">
            Envoyée à l'administration pour vérifier votre identité et certifier votre compte — jamais affichée publiquement sur votre fiche.
          </p>
          <img v-if="myProfile.id_card_photo && !idCardFile" :src="myProfile.id_card_photo" alt="CNI actuelle" class="ie-doc-thumb" />
          <p v-if="profileError" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ profileError }}</p>
          <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="profileSubmitting">
            {{ profileSubmitting ? "Enregistrement…" : "Mettre à jour" }}
          </button>
        </form>
      </div>

      <!-- Mes services -->
      <div id="partner-services" class="ie-card ie-card-body" style="margin-top: 20px;">
        <div class="ie-page-header-actions" style="justify-content: space-between; margin-bottom: 16px;">
          <h2 style="margin: 0;">Mes services ({{ myProfile.services.length }})</h2>
          <button class="ie-btn ie-btn-primary ie-btn-sm" @click="showServiceForm ? (showServiceForm = false) : startCreateService()">
            <i class="fa-solid" :class="showServiceForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showServiceForm ? "Annuler" : "Ajouter un service" }}
          </button>
        </div>

        <form v-if="showServiceForm" @submit.prevent="addService" style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid var(--ie-line);">
          <label class="ie-label">Nom du service</label>
          <input v-model="serviceForm.name" class="ie-input" required placeholder="Ex : Décoration complète de mariage" />
          <label class="ie-label" style="margin-top: 14px;">Description</label>
          <textarea v-model="serviceForm.description" class="ie-input" rows="2"></textarea>
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Tarification</label>
              <select v-model="serviceForm.pricing_type" class="ie-select">
                <option value="fixed">Prix fixe</option>
                <option value="quote">Sur devis</option>
              </select>
            </div>
            <div v-if="serviceForm.pricing_type === 'fixed'">
              <label class="ie-label">Prix à partir de</label>
              <input v-model.number="serviceForm.price_from" type="number" min="0" class="ie-input" />
            </div>
            <div v-if="serviceForm.pricing_type === 'fixed'">
              <label class="ie-label">Devise</label>
              <select v-model="serviceForm.currency" class="ie-select">
                <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
              </select>
            </div>
          </div>
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Durée</label>
              <input v-model="serviceForm.duration_label" class="ie-input" placeholder="Ex : 1 journée" />
            </div>
            <div>
              <label class="ie-label">Personnes incluses</label>
              <input v-model.number="serviceForm.capacity" type="number" min="0" class="ie-input" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Photo</label>
          <input type="file" accept="image/*" class="ie-input" @change="onServicePhotoChange" />
          <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 14px;" :disabled="serviceSubmitting">
            {{ serviceSubmitting ? "Ajout…" : "Ajouter ce service" }}
          </button>
        </form>

        <div v-if="myProfile.services.length" class="ie-service-list">
          <div v-for="s in myProfile.services" :key="s.id" class="ie-service-row">
            <div class="ie-service-photo">
              <img v-if="s.photo" v-img="s.photo" :alt="s.name" />
              <i v-else class="fa-solid fa-concierge-bell"></i>
            </div>
            <div class="ie-service-info">
              <strong>{{ s.name }}</strong>
              <span>{{ s.pricing_type === 'fixed' ? `À partir de ${Number(s.price_from).toLocaleString('fr-FR')} ${s.currency}` : "Sur devis" }}<template v-if="s.duration_label"> · {{ s.duration_label }}</template></span>
            </div>
            <button class="ie-btn ie-btn-danger ie-btn-sm" @click="removeService(s)"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>
        <p v-else class="ie-field-hint">Aucun service ajouté pour le moment.</p>
      </div>

      <!-- Mon portfolio -->
      <div id="partner-portfolio" class="ie-card ie-card-body" style="margin-top: 20px;">
        <h2 style="margin-bottom: 16px;">Mon portfolio ({{ myProfile.portfolio_items.length }})</h2>
        <p v-if="profileForm.marketplace_type === 'interior_design'" class="ie-field-hint" style="margin: 0 0 12px;">
          Ajoutez une photo « avant » pour afficher un avant/après — très efficace pour valoriser vos réalisations.
        </p>
        <div class="ie-portfolio-grid">
          <div v-for="(p, index) in myProfile.portfolio_items" :key="p.id" class="ie-portfolio-item" @click="openPortfolio(index)">
            <div v-if="p.before_image" class="ie-portfolio-before-after">
              <img v-img="p.before_image" alt="Avant" />
              <img v-img="p.image" :alt="p.caption" />
              <span class="ie-badge ie-badge-neutral ie-portfolio-ba-label ie-portfolio-ba-before">Avant</span>
              <span class="ie-badge ie-badge-neutral ie-portfolio-ba-label ie-portfolio-ba-after">Après</span>
            </div>
            <img v-else v-img="p.image" :alt="p.caption" />
            <button class="ie-portfolio-remove" @click.stop="removePortfolioItem(p)"><i class="fa-solid fa-xmark"></i></button>
          </div>
        </div>
        <form class="ie-form-row" style="margin-top: 14px; align-items: flex-end;" @submit.prevent>
          <div v-if="profileForm.marketplace_type === 'interior_design'">
            <label class="ie-label">Photo « avant » (optionnel)</label>
            <input type="file" accept="image/*" class="ie-input" @change="onPortfolioBeforeChange" />
          </div>
          <div>
            <label class="ie-label">{{ portfolioBeforeFile ? "Photo « après »" : "Ajouter des photos" }}</label>
            <input type="file" accept="image/*" :multiple="!portfolioBeforeFile" class="ie-input" @change="onPortfolioChange" />
            <p v-if="!portfolioBeforeFile" class="ie-field-hint">Vous pouvez sélectionner plusieurs photos à la fois.</p>
          </div>
          <div>
            <label class="ie-label">Légende (optionnel)</label>
            <input v-model="portfolioCaption" class="ie-input" />
          </div>
          <button type="button" class="ie-btn ie-btn-primary ie-btn-sm" :disabled="!portfolioFiles.length || portfolioSubmitting" @click="addPortfolioItems">
            {{ portfolioSubmitting ? "Ajout…" : portfolioFiles.length > 1 ? `Ajouter ${portfolioFiles.length} photos` : "Ajouter" }}
          </button>
        </form>
        <p v-if="portfolioError" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ portfolioError }}</p>
      </div>
    </template>

    <SubscriptionCheckoutModal
      v-if="checkoutType"
      :marketplace-type="checkoutType"
      :marketplace-label="checkoutLabel"
      :plans="subscriptionInfo.plans"
      :tiers="subscriptionInfo.tiers"
      @close="checkoutType = null"
      @subscribed="handleSubscribed"
    />
  </div>
</template>

<style scoped>
.ie-doc-thumb { width: 90px; height: 60px; object-fit: cover; border-radius: 6px; border: 1px solid var(--ie-border); margin-top: 6px; }
.ie-required { color: var(--ie-red); }
.ie-optional { color: var(--ie-muted); font-weight: 500; font-size: 11.5px; }
.ie-certif { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; padding: 16px 18px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; }
.ie-certif-icon { display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px; border-radius: 12px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 18px; }
.ie-certif.ok { border-color: #cfe7d9; background: var(--ie-success-soft); }
.ie-certif.ok .ie-certif-icon { background: var(--ie-success); color: #fff; }
.ie-certif.pending { border-color: #f0dcb0; background: var(--ie-warning-soft); }
.ie-certif.pending .ie-certif-icon { background: var(--ie-warning); color: #fff; }
.ie-certif-text { flex: 1; min-width: 0; }
.ie-certif-text strong { color: var(--ie-navy); font-size: 14.5px; }
.ie-certif-text p { margin: 3px 0 0; color: #4b5a6a; font-size: 13px; line-height: 1.45; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
.ie-mp-choice-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.ie-mp-choice-card { border: 1px solid var(--ie-line); border-radius: 12px; overflow: hidden; transition: border-color 0.2s ease; }
.ie-mp-choice-card.is-active { border-color: var(--ie-red); box-shadow: 0 6px 18px rgba(192, 39, 45, 0.12); }
.ie-mp-choice-select { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; width: 100%; padding: 18px; background: transparent; border: 0; text-align: left; cursor: pointer; }
.ie-mp-choice-icon { width: 42px; height: 42px; border-radius: 10px; background: var(--ie-navy-soft); color: var(--ie-navy); display: flex; align-items: center; justify-content: center; font-size: 17px; }
.ie-mp-choice-card.is-active .ie-mp-choice-icon { background: var(--ie-red); color: #fff; }
.ie-mp-choice-title { font-size: 13.5px; font-weight: 700; color: var(--ie-navy); }
.ie-mp-choice-hint { font-size: 11.5px; color: var(--ie-muted); line-height: 1.4; }

.ie-btn-marketplace {
  display: inline-flex; align-items: center; gap: 8px;
  background: linear-gradient(120deg, var(--ie-red), #8a0e16); color: #fff; border: 0;
}
.ie-btn-marketplace:hover:not(:disabled) { background: linear-gradient(120deg, #8a0e16, #6b0a10); }
.ie-btn-marketplace:disabled { opacity: 0.7; }

.ie-partner-cover {
  position: relative; height: 70px; background: linear-gradient(120deg, var(--ie-navy), #1f2a3d);
  display: flex; align-items: flex-end;
}
.ie-partner-cover.has-photo { height: 170px; }
.ie-partner-cover > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.ie-partner-cover-actions {
  position: relative; z-index: 1; margin-left: auto; display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
}
.ie-partner-cover-actions .ie-btn-ghost { background: rgba(255,255,255,0.92); }
.ie-partner-identity { display: flex; align-items: flex-start; gap: 18px; padding: 0 20px; }
.ie-partner-avatar {
  width: 96px; height: 96px; border-radius: 16px; overflow: hidden; background: #fff; flex-shrink: 0;
  border: 4px solid #fff; box-shadow: 0 4px 14px rgba(0,0,0,0.16); margin-top: -40px;
  display: flex; align-items: center; justify-content: center; position: relative; z-index: 1;
}
.ie-partner-avatar img { width: 100%; height: 100%; object-fit: cover; }
.ie-partner-avatar i { font-size: 28px; color: var(--ie-navy); opacity: 0.35; }

.ie-service-list { display: flex; flex-direction: column; gap: 10px; }
.ie-service-row { display: flex; align-items: center; gap: 12px; padding: 10px; border: 1px solid var(--ie-line); border-radius: 8px; }
.ie-service-photo { width: 48px; height: 48px; border-radius: 8px; overflow: hidden; background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ie-service-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-service-photo i { color: var(--ie-navy); opacity: 0.4; }
.ie-service-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.ie-service-info strong { font-size: 13.5px; color: var(--ie-navy); }
.ie-service-info span { font-size: 12px; color: var(--ie-muted); }

.ie-portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
.ie-portfolio-item { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; cursor: zoom-in; }

.ie-completion { margin-bottom: 20px; border-left: 4px solid var(--ie-red); }
.ie-completion-head { display: flex; align-items: center; gap: 16px; }
.ie-completion-head h2 { margin: 0 0 4px; }
.ie-completion-head p { margin: 0; color: var(--ie-muted); font-size: 13px; }
.ie-completion-ring {
  --pct: 0; flex: 0 0 64px; width: 64px; height: 64px; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--ie-red) calc(var(--pct) * 1%), #eef0f2 0);
}
.ie-completion-ring span {
  width: 50px; height: 50px; border-radius: 50%; background: #fff; display: grid; place-items: center;
  font-size: 13px; font-weight: 800; color: var(--ie-navy);
}
.ie-completion-list { list-style: none; margin: 16px 0 0; padding: 0; display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.ie-completion-list li {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid var(--ie-line); border-radius: 8px;
  font-size: 13px; color: var(--ie-navy); min-height: 44px;
}
.ie-completion-list li > i { color: var(--ie-red); }
.ie-completion-list li span { flex: 1; min-width: 0; }
.ie-completion-list li.done { color: var(--ie-muted); background: #fafbfc; }
.ie-completion-list li.done > i { color: #28734f; }
.ie-portfolio-item img { width: 100%; height: 100%; object-fit: cover; }
.ie-portfolio-remove { position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; border-radius: 50%; background: rgba(23,27,38,0.7); color: #fff; border: 0; cursor: pointer; font-size: 11px; z-index: 2; }
.ie-portfolio-before-after { position: relative; width: 100%; height: 100%; display: flex; }
.ie-portfolio-before-after img { width: 50%; height: 100%; object-fit: cover; }
.ie-portfolio-ba-label { position: absolute; bottom: 4px; font-size: 9px; padding: 1px 5px; }
.ie-portfolio-ba-before { left: 4px; }
.ie-portfolio-ba-after { right: 4px; }

@media (max-width: 700px) {
  .ie-mp-choice-grid { grid-template-columns: 1fr; }
  .ie-completion-list { grid-template-columns: 1fr; }
  .ie-certif { flex-wrap: wrap; }
  .ie-certif .ie-btn { width: 100%; justify-content: center; }
  .ie-partner-identity { flex-direction: column; }
  .ie-partner-cover-actions { flex-wrap: wrap; }
}
</style>
