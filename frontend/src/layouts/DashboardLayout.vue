<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import logo from "../assets/images/logo-mark.png";
import InstallPwaButton from "../components/InstallPwaButton.vue";
import LanguageSwitcher from "../components/LanguageSwitcher.vue";
import NotificationBell from "../components/NotificationBell.vue";
import PushPrompt from "../components/PushPrompt.vue";
import { useFeatureFlags } from "../composables/useFeatureFlags";
import { ACTOR_CATEGORY_GROUPS } from "../data/actorCategories";
import { INTERIOR_DESIGN_CATEGORY_GROUPS } from "../data/interiorDesignCategories";
import api from "../services/api";
import { useAuthStore } from "../stores/auth";
import { useMarketplaceAccessStore } from "../stores/marketplaceAccess";

const auth = useAuthStore();
const marketplaceAccess = useMarketplaceAccessStore();
const router = useRouter();
const route = useRoute();
const sidebarOpen = ref(false);
const unreadMessages = ref(0);
const openGroups = reactive({});
const hasCarrierProfile = ref(false);
const hasDriverProfile = ref(false);
const hasCompanyProfile = ref(false);
const hasTalentProfile = ref(false);
let pollHandle = null;

async function checkCarrierProfile() {
  try {
    await api.get("/deliveries/carriers/me/");
    hasCarrierProfile.value = true;
  } catch (e) {
    hasCarrierProfile.value = false;
  }
}

async function checkDriverProfile() {
  try {
    await api.get("/deliveries/drivers/me/");
    hasDriverProfile.value = true;
  } catch (e) {
    hasDriverProfile.value = false;
  }
}

async function checkCompanyProfile() {
  try {
    await api.get("/companies/me/");
    hasCompanyProfile.value = true;
  } catch (e) {
    hasCompanyProfile.value = false;
  }
}

async function checkTalentProfile() {
  try {
    await api.get("/talents/me/");
    hasTalentProfile.value = true;
  } catch (e) {
    hasTalentProfile.value = false;
  }
}

// Le palier d'abonnement (configurable par l'admin depuis « Fonctionnalités
// & permissions ») décide quelles catégories de métiers de la Marketplace
// des acteurs sont visibles dans la sidebar : absentes tant que le compte
// n'a aucun abonnement actif, verrouillées (visibles mais grisées, avec
// incitation) si le palier actuel ne suffit pas. L'administrateur voit
// toujours tout (resolve_features le laisse toujours passer). Lu depuis le
// store partagé (et non un fetch local) : la sidebar est un layout persistant
// qui ne se remonte pas à la navigation, donc sans état partagé elle resterait
// figée sur le statut d'avant paiement après un abonnement effectué ailleurs.
const actorsFeaturesRef = computed(() => marketplaceAccess.actorsFeatures);
const { isVisible: isActorGroupVisible, isLocked: isActorGroupLocked } = useFeatureFlags(actorsFeaturesRef);
const hasProfileMarketplaceSubscription = computed(() => marketplaceAccess.hasProfileMarketplaceSubscription);
const hasVenueMarketplaceSubscription = computed(() => marketplaceAccess.activeProfileSubscriptionTypes.has("venues"));

// Un groupe dépliable par catégorie de métiers (10 au total), plutôt qu'un
// seul groupe « Marketplace des acteurs » avec les 42 métiers à plat — trop
// long à parcourir dans la sidebar. Filtré/verrouillé par catégorie selon le
// palier d'abonnement du compte (voir plus haut).
const actorsMarketplaceSections = computed(() =>
  ACTOR_CATEGORY_GROUPS.filter((group) => auth.role === "admin" || isActorGroupVisible(group.featureKey)).map((group) => ({
    type: "group",
    label: group.title,
    icon: group.icon,
    marketplace: "actors",
    locked: auth.role !== "admin" && isActorGroupLocked(group.featureKey),
    children: group.items.map((item) => ({
      label: item.label,
      to: { name: "premium-marketplace", query: { type: "actors", category: item.value } },
    })),
  }))
);

const interiorDesignSections = computed(() =>
  auth.role === "admin" || marketplaceAccess.activeProfileSubscriptionTypes.has("interior_design")
    ? INTERIOR_DESIGN_CATEGORY_GROUPS.map((group) => ({
        type: "group",
        label: `Déco · ${group.title}`,
        icon: group.icon,
        marketplace: "interior_design",
        children: group.items.map((item) => ({
          label: item.label,
          to: { name: "premium-marketplace", query: { type: "interior_design", category: item.value } },
        })),
      }))
    : []
);

// Une section titrée par marketplace souscrit : le client voit tout de suite
// les métiers auxquels son abonnement donne accès.
const marketplaceSections = computed(() => [
  ...(actorsMarketplaceSections.value.length
    ? [{ type: "heading", label: "Marketplace des acteurs", anchor: "nav-mp-actors", icon: "fa-solid fa-people-group" }, ...actorsMarketplaceSections.value]
    : []),
  ...(interiorDesignSections.value.length
    ? [{ type: "heading", label: "Décoration & design", anchor: "nav-mp-interior_design", icon: "fa-solid fa-couch" }, ...interiorDesignSections.value]
    : []),
]);

const ROLE_LABELS = {
  admin: "Administrateur", client: "Client", organizer: "Organisateur",
  participant: "Participant", employee: "Employé", partner: "Prestataire",
};
const roleLabel = computed(() => ROLE_LABELS[auth.role] || auth.role);

const navSections = computed(() => {
  if (auth.role === "admin") {
    return [
      { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
      { type: "link", label: "Calendrier", to: { name: "calendar" }, icon: "fa-solid fa-calendar-days" },
      { type: "link", label: "Événements", to: { name: "events" }, icon: "fa-solid fa-calendar-week" },
      { type: "link", label: "Pilotage", to: { name: "pilotage" }, icon: "fa-solid fa-compass" },
      {
        type: "group", label: "Billetterie", icon: "fa-solid fa-ticket", children: [
          { label: "Billetterie", to: { name: "tickets" } },
          { label: "Scan billets", to: { name: "tickets-scan" } },
        ],
      },
      { type: "link", label: "Consulter équipements", to: { name: "equipment-catalog" }, icon: "fa-solid fa-sliders" },
      { type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" },
      { type: "link", label: "Fournisseurs", to: { name: "providers-manage" }, icon: "fa-solid fa-handshake" },
      {
        type: "group", label: "Marketplaces Premium", icon: "fa-solid fa-crown", children: [
          { label: "Annonces", to: { name: "premium-marketplace-manage" } },
          { label: "Fonctionnalités & permissions", to: { name: "premium-marketplace-features-manage" } },
          { label: "Paliers d'abonnement", to: { name: "marketplace-tiers-manage" } },
          { label: "Demandes de réservation", to: { name: "premium-marketplace-booking-requests" } },
          { label: "Commandes boutique", to: { name: "sale-orders" } },
          { label: "Prestataires", to: { name: "marketplace-badges-manage" } },
          { label: "Entreprises", to: { name: "companies-manage" } },
          { label: "Talents", to: { name: "talents-manage" } },
          { label: "Analytics", to: { name: "marketplace-analytics" } },
          { label: "Commissions", to: { name: "marketplace-commissions-manage" } },
        ],
      },
      ...marketplaceSections.value,
      {
        type: "group", label: "Gestion de stock", icon: "fa-solid fa-toolbox", children: [
          { label: "Inventaire matériel", to: { name: "equipment-manage" } },
          { label: "Mouvements de stock", to: { name: "stock-movements" } },
          { label: "Locations boutique", to: { name: "sale-rentals" } },
          { label: "Dépenses", to: { name: "expenses" } },
        ],
      },
      {
        type: "group", label: "Transport & Livraison", icon: "fa-solid fa-truck", children: [
          { label: "Livraisons", to: { name: "deliveries" } },
          { label: "Planning", to: { name: "delivery-planning" } },
          { label: "Tableau de bord", to: { name: "deliveries-dashboard" } },
          { label: "Rapports", to: { name: "delivery-reports" } },
          { label: "Transporteurs", to: { name: "carriers-manage" } },
          { label: "Chauffeurs", to: { name: "drivers-manage" } },
          { label: "Véhicules", to: { name: "vehicles-manage" } },
          { label: "Zones & tarifs", to: { name: "delivery-zones-manage" } },
          { label: "Règles de tarification", to: { name: "pricing-rules-manage" } },
          { label: "Dépenses transport", to: { name: "delivery-expenses" } },
        ],
      },
      { type: "link", label: "Réservations", to: { name: "bookings" }, icon: "fa-solid fa-calendar-check" },
      {
        type: "group", label: "Paiements", icon: "fa-solid fa-credit-card", children: [
          { label: "Paiements", to: { name: "payments" } },
          { label: "Dashboard paiements", to: { name: "payments-dashboard" } },
        ],
      },
      {
        type: "group", label: "Formations", icon: "fa-solid fa-graduation-cap", children: [
          { label: "Formations", to: { name: "trainings" } },
          { label: "Attestations & badges", to: { name: "attestations" } },
        ],
      },
      {
        type: "group", label: "Ressources humaines", icon: "fa-solid fa-users-gear", children: [
          { label: "Employés", to: { name: "employees" } },
          { label: "Paie", to: { name: "payroll" } },
          { label: "Candidatures", to: { name: "job-applications-manage" } },
        ],
      },
      {
        type: "group", label: "Parrainage", icon: "fa-solid fa-user-plus", children: [
          { label: "Gestion des parrainages", to: { name: "referrals-manage" } },
          { label: "Configuration des campagnes", to: { name: "referral-campaigns-manage" } },
        ],
      },
      { type: "link", label: "Site vitrine", to: { name: "landing-media" }, icon: "fa-solid fa-images" },
      { type: "link", label: "Utilisateurs", to: { name: "users" }, icon: "fa-solid fa-users" },
      { type: "link", label: "Journal d'activité", to: { name: "audit-log" }, icon: "fa-solid fa-shield-halved" },
      { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
    ];
  }

  if (auth.role === "client") {
    return [
      { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
      { type: "link", label: "Mon événement", to: { name: "events" }, icon: "fa-solid fa-calendar-week" },
      { type: "link", label: "Réservations", to: { name: "bookings" }, icon: "fa-solid fa-calendar-check" },
      { type: "link", label: "Consulter équipements", to: { name: "equipment-catalog" }, icon: "fa-solid fa-sliders" },
      ...(hasVenueMarketplaceSubscription.value
        ? [{ type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" }]
        : []),
      { type: "link", label: "Marché des événements", to: { name: "marketplace" }, icon: "fa-solid fa-store" },
      { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-crown" },
      { type: "link", label: "Boutique", to: { name: "sale-shop" }, icon: "fa-solid fa-bag-shopping" },
      { type: "link", label: "Mes commandes", to: { name: "sale-orders" }, icon: "fa-solid fa-file-invoice" },
      ...marketplaceSections.value,
      ...(hasProfileMarketplaceSubscription.value
        ? [
            { type: "link", label: "Mes demandes prestataires", to: { name: "my-booking-requests" }, icon: "fa-solid fa-clipboard-list" },
            { type: "link", label: "Mes favoris", to: { name: "my-favorites" }, icon: "fa-solid fa-heart" },
          ]
        : []),
      { type: "link", label: "Paiements", to: { name: "payments" }, icon: "fa-solid fa-credit-card" },
      { type: "link", label: "Rejoindre l'équipe", to: { name: "my-job-applications" }, icon: "fa-solid fa-briefcase" },
      { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
      { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
    ];
  }

  if (auth.role === "organizer") {
    return [
      { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
      { type: "link", label: "Calendrier", to: { name: "calendar" }, icon: "fa-solid fa-calendar-days" },
      { type: "link", label: "Mes événements", to: { name: "events" }, icon: "fa-solid fa-calendar-week" },
      { type: "link", label: "Pilotage", to: { name: "pilotage" }, icon: "fa-solid fa-compass" },
      { type: "link", label: "Billetterie", to: { name: "tickets" }, icon: "fa-solid fa-ticket" },
      { type: "link", label: "Marché des événements", to: { name: "marketplace" }, icon: "fa-solid fa-store" },
      { type: "link", label: "Réservations", to: { name: "bookings" }, icon: "fa-solid fa-calendar-check" },
      { type: "link", label: "Consulter équipements", to: { name: "equipment-catalog" }, icon: "fa-solid fa-sliders" },
      ...(hasVenueMarketplaceSubscription.value
        ? [{ type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" }]
        : []),
      { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-crown" },
      { type: "link", label: "Boutique", to: { name: "sale-shop" }, icon: "fa-solid fa-bag-shopping" },
      { type: "link", label: "Mes commandes", to: { name: "sale-orders" }, icon: "fa-solid fa-file-invoice" },
      ...marketplaceSections.value,
      { type: "link", label: "Paiements", to: { name: "payments" }, icon: "fa-solid fa-credit-card" },
      { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
      { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
    ];
  }

  if (auth.role === "employee") {
    return [
      { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
      { type: "link", label: "Billets", to: { name: "marketplace" }, icon: "fa-solid fa-store" },
      { type: "link", label: "Mes billets", to: { name: "my-tickets" }, icon: "fa-solid fa-ticket" },
      ...(hasVenueMarketplaceSubscription.value
        ? [{ type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" }]
        : []),
      { type: "link", label: "Attestations & badges", to: { name: "attestations" }, icon: "fa-solid fa-certificate" },
      { type: "link", label: "Mes livraisons", to: { name: "my-deliveries" }, icon: "fa-solid fa-truck-fast" },
      ...(hasDriverProfile.value
        ? [{ type: "link", label: "Mon profil chauffeur", to: { name: "driver-profile" }, icon: "fa-solid fa-id-card" }]
        : []),
      ...marketplaceSections.value,
      { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
      { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
    ];
  }

  if (auth.role === "partner") {
    if (hasTalentProfile.value) {
      return [
        { type: "link", label: "Mon profil talent", to: { name: "talent-profile" }, icon: "fa-solid fa-star" },
        ...(hasVenueMarketplaceSubscription.value
          ? [{ type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" }]
          : []),
        { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-store" },
        { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
      ];
    }
    return [
      { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
      { type: "link", label: "Talents", to: { name: "talents-directory" }, icon: "fa-solid fa-users" },
      { type: "link", label: "Demandes de devis reçues", to: { name: "provider-quote-requests" }, icon: "fa-solid fa-file-invoice" },
      { type: "link", label: "Mes disponibilités", to: { name: "provider-availability" }, icon: "fa-solid fa-calendar-check" },
      { type: "link", label: "Mes livraisons", to: { name: "my-deliveries" }, icon: "fa-solid fa-truck-fast" },
      ...(hasVenueMarketplaceSubscription.value
        ? [{ type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" }]
        : []),
      ...(hasDriverProfile.value
        ? [{ type: "link", label: "Mon profil chauffeur", to: { name: "driver-profile" }, icon: "fa-solid fa-id-card" }]
        : []),
      ...(hasCarrierProfile.value
        ? [{
            type: "group", label: "Espace Transporteur", icon: "fa-solid fa-truck-fast", children: [
              { label: "Livraisons", to: { name: "deliveries" } },
              { label: "Véhicules", to: { name: "vehicles-manage" } },
              { label: "Chauffeurs", to: { name: "drivers-manage" } },
              { label: "Dépenses", to: { name: "delivery-expenses" } },
              { label: "Mon profil transporteur", to: { name: "transporter-profile" } },
            ],
          }]
        : []),
      ...(hasCompanyProfile.value
        ? [{ type: "link", label: "Mon profil entreprise", to: { name: "company-profile" }, icon: "fa-solid fa-building" }]
        : []),
      ...(hasTalentProfile.value
        ? [{ type: "link", label: "Mon profil talent", to: { name: "talent-profile" }, icon: "fa-solid fa-star" }]
        : []),
      { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-store" },
      { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
      { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
    ];
  }

  // participant
  return [
    { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
    { type: "link", label: "Billets", to: { name: "marketplace" }, icon: "fa-solid fa-store" },
    { type: "link", label: "Mes billets", to: { name: "my-tickets" }, icon: "fa-solid fa-ticket" },
    ...(hasVenueMarketplaceSubscription.value
      ? [{ type: "link", label: "Consulter les salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" }]
      : []),
    { type: "link", label: "Jeux", to: { name: "games" }, icon: "fa-solid fa-gamepad" },
    ...marketplaceSections.value,
    { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
    { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
  ];
});

// Barre d'onglets mobile : les 4 accès les plus fréquents de chaque compte,
// le reste du menu restant accessible via « Plus » (qui ouvre la sidebar).
// L'administrateur garde uniquement la sidebar : liste vide = pas de barre.
// Le Marketplace est l'onglet central, mis en avant pour tous les comptes
// (hors administration) : c'est lui que la plateforme veut faire découvrir.
const bottomTabs = computed(() => {
  const home = { label: "Accueil", to: { name: "dashboard" }, icon: "fa-solid fa-house" };
  const messages = { label: "Messages", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value };
  const marketplace = {
    label: "Marketplace", to: { name: "premium-marketplace" }, icon: "fa-solid fa-store", featured: true,
    // La boutique fait partie du Marketplace.
    alsoActive: ["/app/boutique"],
  };

  if (auth.role === "admin") return [];
  if (auth.role === "client") {
    return [
      home,
      { label: "Événement", to: { name: "events" }, icon: "fa-solid fa-calendar-week" },
      marketplace,
      { label: "Salles", to: { name: "venues" }, icon: "fa-solid fa-building-columns" },
    ];
  }
  if (auth.role === "organizer") {
    return [
      home,
      { label: "Événements", to: { name: "events" }, icon: "fa-solid fa-calendar-week" },
      marketplace,
      { label: "Billetterie", to: { name: "tickets" }, icon: "fa-solid fa-ticket" },
    ];
  }
  if (auth.role === "employee") {
    return [
      home,
      { label: "Livraisons", to: { name: "my-deliveries" }, icon: "fa-solid fa-truck-fast" },
      marketplace,
      { label: "Mes billets", to: { name: "my-tickets" }, icon: "fa-solid fa-ticket" },
    ];
  }
  if (auth.role === "partner") {
    if (hasTalentProfile.value) {
      return [
        { label: "Mon profil", to: { name: "talent-profile" }, icon: "fa-solid fa-star" },
        marketplace,
        messages,
      ];
    }
    return [
      home,
      { label: "Devis", to: { name: "provider-quote-requests" }, icon: "fa-solid fa-file-invoice" },
      marketplace,
      { label: "Talents", to: { name: "talents-directory" }, icon: "fa-solid fa-users" },
    ];
  }
  // participant
  return [
    home,
    { label: "Billets", to: { name: "marketplace" }, icon: "fa-solid fa-ticket" },
    marketplace,
    { label: "Mes billets", to: { name: "my-tickets" }, icon: "fa-solid fa-qrcode" },
  ];
});
const hasBottomTabs = computed(() => bottomTabs.value.length > 0);

function isTabActive(tab) {
  // Le dashboard est la route racine /app : sans comparaison exacte, il
  // serait « actif » sur toutes les pages de l'espace.
  const target = router.resolve(tab.to).path;
  if (tab.to.name === "dashboard") return route.path === target || route.path === `${target}/`;
  if (tab.alsoActive?.some((prefix) => route.path === prefix || route.path.startsWith(`${prefix}/`))) return true;
  return route.path === target || route.path.startsWith(`${target}/`);
}

const accountItems = [
  { label: "Profil", to: { name: "profile" }, icon: "fa-solid fa-user" },
  { label: "Paramètres", to: { name: "settings" }, icon: "fa-solid fa-gear" },
];

function isChildActive(child) {
  // Comme pour isGroupActive : Vue Router marque « actif » tout lien qui
  // partage la même route, sans regarder la query — il faudrait donc sinon
  // les 42 métiers en rouge à la fois dès qu'on est sur cette page.
  if (child.to.name !== route.name) return false;
  if (!child.to.query) return true;
  return Object.entries(child.to.query).every(([key, value]) => route.query[key] === value);
}

function isGroupActive(group) {
  return group.children.some(isChildActive);
}

// Après un abonnement (ou « Explorer »), on ouvre la sidebar directement sur
// la section du marketplace, première famille de métiers dépliée.
watch(
  () => marketplaceAccess.reveal.token,
  async () => {
    const type = marketplaceAccess.reveal.type;
    const firstGroup = navSections.value.find((item) => item.type === "group" && item.marketplace === type && !item.locked);
    if (!firstGroup) return;
    Object.keys(openGroups).forEach((key) => { openGroups[key] = false; });
    openGroups[firstGroup.label] = true;
    sidebarOpen.value = true;
    await nextTick();
    const heading = document.getElementById(`nav-mp-${type}`);
    heading?.scrollIntoView({ behavior: "smooth", block: "start" });
    heading?.classList.add("is-highlighted");
    setTimeout(() => heading?.classList.remove("is-highlighted"), 2200);
  },
);

function toggleGroup(label) {
  // Accordéon : ouvrir un groupe referme automatiquement les autres, sinon
  // la sidebar devient interminable quand plusieurs groupes (ex : les 10
  // catégories du Marketplace des acteurs) restent dépliés en même temps.
  const wasOpen = openGroups[label];
  Object.keys(openGroups).forEach((key) => { openGroups[key] = false; });
  openGroups[label] = !wasOpen;
}

async function loadUnreadMessages() {
  try {
    const { data } = await api.get("/messaging/conversations/");
    const conversations = data.results || data;
    unreadMessages.value = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0);
  } catch (e) {
    // messagerie non critique pour l'affichage du menu
  }
}

async function handleLogout() {
  await auth.logout();
  router.push({ name: "login" });
}

onMounted(() => {
  loadUnreadMessages();
  pollHandle = setInterval(loadUnreadMessages, 30000);
  marketplaceAccess.refresh();
  if (auth.role === "partner") {
    checkCarrierProfile();
    checkCompanyProfile();
    checkTalentProfile();
  }
  if (["employee", "partner"].includes(auth.role)) {
    checkDriverProfile();
  }
});

onBeforeUnmount(() => {
  if (pollHandle) clearInterval(pollHandle);
});
</script>

<template>
  <div class="ie-shell" :class="{ 'has-bottom-tabs': hasBottomTabs }">
    <button class="ie-mobile-toggle" :aria-expanded="sidebarOpen" aria-controls="dashboard-navigation" @click="sidebarOpen = !sidebarOpen" :aria-label="sidebarOpen ? 'Fermer le menu' : 'Ouvrir le menu'">
      <i :class="sidebarOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars'" aria-hidden="true"></i>
    </button>
    <button v-if="sidebarOpen" class="ie-sidebar-scrim" type="button" aria-label="Fermer le menu" @click="sidebarOpen = false"></button>

    <aside id="dashboard-navigation" class="ie-sidebar" :class="{ open: sidebarOpen }">
      <div class="ie-brand">
        <img :src="logo" alt="InnovEvent&amp;Home groupe" class="ie-brand-logo" />
        <div>
          <strong>InnovEvent&amp;Home groupe</strong>
          <span>Gestion événementielle</span>
        </div>
      </div>

      <nav class="ie-nav">
        <template v-for="item in navSections" :key="item.label">
          <p v-if="item.type === 'heading'" :id="item.anchor" class="ie-nav-heading">
            <i :class="item.icon"></i> {{ item.label }}
          </p>
          <router-link
            v-else-if="item.type === 'link'"
            :to="item.to"
            class="ie-nav-link"
            @click="sidebarOpen = false"
          >
            <i class="ie-nav-icon" :class="item.icon"></i>
            <span class="ie-nav-label">{{ item.label }}</span>
            <span v-if="item.badge" class="ie-nav-badge">{{ item.badge }}</span>
          </router-link>

          <div v-else class="ie-nav-group">
            <button
              type="button"
              class="ie-nav-link ie-nav-group-toggle"
              :class="{ 'router-link-active': isGroupActive(item) }"
              @click="toggleGroup(item.label)"
            >
              <i class="ie-nav-icon" :class="item.icon"></i>
              <span class="ie-nav-label">{{ item.label }}</span>
              <i v-if="item.locked" class="fa-solid fa-lock ie-nav-lock" title="Formule d'abonnement supérieure requise"></i>
              <span class="ie-nav-chevron" :class="{ open: openGroups[item.label] || isGroupActive(item) }">›</span>
            </button>
            <div class="ie-nav-children" v-show="openGroups[item.label] || isGroupActive(item)">
              <router-link
                v-for="child in item.children"
                :key="child.label"
                :to="child.to"
                class="ie-nav-sublink"
                :class="{ 'router-link-active': isChildActive(child), 'is-locked': item.locked }"
                active-class="" exact-active-class=""
                @click="sidebarOpen = false"
              >
                <i v-if="item.locked" class="fa-solid fa-lock"></i> {{ child.label }}
              </router-link>
            </div>
          </div>
        </template>
      </nav>

      <div class="ie-nav-footer">
        <InstallPwaButton compact />
        <router-link
          v-for="item in accountItems"
          :key="item.label"
          :to="item.to"
          class="ie-nav-link"
          @click="sidebarOpen = false"
        >
          <i class="ie-nav-icon" :class="item.icon"></i>
          <span class="ie-nav-label">{{ item.label }}</span>
        </router-link>
        <button type="button" class="ie-nav-link ie-nav-logout" @click="handleLogout">
          <i class="ie-nav-icon fa-solid fa-arrow-right-from-bracket"></i>
          <span class="ie-nav-label">Déconnexion</span>
        </button>
      </div>
    </aside>

    <div class="ie-main">
      <header class="ie-topbar">
        <div class="ie-topbar-title">Bienvenue{{ auth.user ? ", " + (auth.user.first_name || auth.user.username) : "" }}</div>
        <div class="ie-topbar-actions">
          <LanguageSwitcher />
          <NotificationBell />
          <span
            v-if="['client', 'organizer'].includes(auth.role)"
            class="ie-tier-badge"
            :class="{ 'is-subscribed': marketplaceAccess.isSubscribedToAny }"
            :title="marketplaceAccess.isSubscribedToAny ? 'Palier le plus élevé parmi vos abonnements actifs' : 'Aucun abonnement Marketplace actif'"
          >
            <i class="fa-solid" :class="marketplaceAccess.isSubscribedToAny ? 'fa-crown' : 'fa-circle-user'"></i>
            {{ marketplaceAccess.currentTierLabel }}
          </span>
          <span class="ie-role-badge">{{ roleLabel }}</span>
          <button class="ie-btn ie-btn-secondary ie-logout-btn" @click="handleLogout">
            <i class="fa-solid fa-arrow-right-from-bracket"></i> <span>Déconnexion</span>
          </button>
        </div>
      </header>
      <main class="ie-content">
        <PushPrompt />
        <!-- Clé par chemin : chaque écran entre en fondu, et un écran de détail
             (/talents/1 → /talents/2) est bien rechargé. -->
        <router-view v-slot="{ Component, route: current }">
          <div :key="current.path" class="ie-page-enter">
            <component :is="Component" />
          </div>
        </router-view>
      </main>
    </div>

    <nav v-if="hasBottomTabs" class="ie-bottom-tabs" aria-label="Navigation rapide">
      <router-link
        v-for="tab in bottomTabs"
        :key="tab.label"
        :to="tab.to"
        class="ie-bottom-tab"
        :class="{ 'is-active': isTabActive(tab), 'is-featured': tab.featured }"
        active-class="" exact-active-class=""
        @click="sidebarOpen = false"
      >
        <span class="ie-bottom-tab-icon">
          <i :class="tab.icon" aria-hidden="true"></i>
          <span v-if="tab.badge" class="ie-bottom-tab-badge">{{ tab.badge > 99 ? "99+" : tab.badge }}</span>
        </span>
        <span class="ie-bottom-tab-label">{{ tab.label }}</span>
      </router-link>
      <button
        type="button"
        class="ie-bottom-tab"
        :class="{ 'is-active': sidebarOpen }"
        :aria-expanded="sidebarOpen"
        aria-controls="dashboard-navigation"
        @click="sidebarOpen = !sidebarOpen"
      >
        <span class="ie-bottom-tab-icon"><i class="fa-solid fa-table-cells-large" aria-hidden="true"></i></span>
        <span class="ie-bottom-tab-label">Plus</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.ie-shell { display: flex; height: 100vh; height: 100dvh; min-height: 0; overflow: hidden; }
.ie-sidebar {
  width: 270px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid var(--ie-line);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
}
.ie-brand { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.ie-brand-logo {
  width: 38px; height: 38px;
  object-fit: contain;
}
.ie-brand strong { display: block; color: var(--ie-navy); font-size: 15px; }
.ie-brand span { font-size: 11px; color: var(--ie-muted); }

.ie-nav { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.ie-nav-link {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: 8px;
  color: var(--ie-navy); font-size: 13.5px; font-weight: 600;
  border: 0; background: transparent; width: 100%; text-align: left; cursor: pointer;
  font-family: inherit;
}
.ie-nav-link:hover, .ie-nav-link.router-link-active { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-nav-icon { width: 18px; text-align: center; flex-shrink: 0; font-size: 14px; color: var(--ie-muted); }
.ie-nav-link:hover .ie-nav-icon, .ie-nav-link.router-link-active .ie-nav-icon { color: var(--ie-red); }
.ie-nav-logout .ie-nav-icon { color: var(--ie-red); opacity: 0.85; }
.ie-nav-label { flex: 1; }
.ie-nav-badge {
  background: var(--ie-red); color: #fff; font-size: 11px; font-weight: 800;
  border-radius: 999px; min-width: 18px; height: 18px; display: inline-flex;
  align-items: center; justify-content: center; padding: 0 5px;
}

.ie-nav-group-toggle { justify-content: flex-start; }
.ie-nav-heading {
  display: flex; align-items: center; gap: 8px; margin: 14px 0 4px; padding: 8px 10px 6px; border-top: 1px solid var(--ie-line);
  color: var(--ie-muted); font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;
  scroll-margin-top: 8px; transition: background-color 0.3s ease, color 0.3s ease;
}
.ie-nav-heading i { color: var(--ie-red); font-size: 12px; }
.ie-nav-heading.is-highlighted { border-radius: 8px; background: var(--ie-red-soft); color: var(--ie-red); }
.ie-nav-chevron { transition: transform 0.15s ease; color: var(--ie-muted); font-size: 15px; }
.ie-nav-chevron.open { transform: rotate(90deg); }
.ie-nav-children { display: flex; flex-direction: column; padding-left: 30px; gap: 1px; margin: 2px 0 4px; }
.ie-nav-sublink {
  padding: 7px 10px; border-radius: 7px; font-size: 13px; color: #5d6771; font-weight: 500;
}
.ie-nav-sublink:hover, .ie-nav-sublink.router-link-active { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-nav-lock { font-size: 11px; color: var(--ie-muted); margin: 0 4px; }
.ie-nav-sublink.is-locked { color: var(--ie-muted); }
.ie-nav-sublink.is-locked i { font-size: 10px; }

.ie-nav-footer {
  border-top: 1px solid var(--ie-line);
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
.ie-nav-logout { color: var(--ie-red); }
.ie-nav-logout:hover { background: var(--ie-red-soft); }

.ie-main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.ie-topbar {
  height: 68px; background: #fff; border-bottom: 1px solid var(--ie-line);
  display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
  flex-shrink: 0;
}
.ie-topbar-title { font-weight: 700; color: var(--ie-navy); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ie-topbar-actions { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.ie-logout-btn { display: inline-flex; align-items: center; gap: 8px; }
.ie-role-badge {
  background: #eef0f2; color: var(--ie-navy); padding: 4px 10px;
  border-radius: 999px; font-size: 12px; font-weight: 700; text-transform: capitalize;
}
.ie-tier-badge {
  display: inline-flex; align-items: center; gap: 6px; background: #eef0f2; color: var(--ie-muted);
  padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 700;
}
.ie-tier-badge.is-subscribed { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-tier-badge i { font-size: 11px; }
.ie-content { padding: 24px; flex: 1; overflow-y: auto; }

.ie-mobile-toggle { display: none; }
.ie-sidebar-scrim { display: none; }

@media (max-width: 900px) {
  .ie-mobile-toggle {
    display: block; position: fixed; top: 14px; left: 14px; z-index: 30;
    background: var(--ie-navy); color: #fff; border: 0; border-radius: 8px;
    width: 40px; height: 40px; font-size: 18px;
  }
  .ie-sidebar {
    position: fixed; inset: 0 auto 0 0; z-index: 25; transform: translateX(-100%);
    transition: transform 0.2s ease; width: 270px;
  }
  .ie-sidebar.open { transform: translateX(0); }
  .ie-topbar { padding-left: 64px; }
  .ie-sidebar-scrim { display: block; position: fixed; inset: 0; z-index: 24; border: 0; background: rgba(20, 30, 40, .48); }
  .ie-sidebar { box-shadow: 8px 0 30px rgba(20, 30, 40, .16); }
}

@media (max-width: 560px) {
  .ie-content { padding: 16px 12px; }
  .ie-topbar { padding-left: 60px; padding-right: 14px; gap: 8px; }
  .ie-topbar-title { font-size: 13px; }
  .ie-role-badge, .ie-tier-badge { display: none; }
  .ie-logout-btn span { display: none; }
  .ie-logout-btn { padding: 9px 11px; }
  .ie-topbar-actions { gap: 8px; }
  .ie-content { padding: 14px 12px max(14px, env(safe-area-inset-bottom)); }
}

@media (max-width: 380px) {
  .ie-topbar { padding-right: 10px; }
  .ie-topbar-title { max-width: 38vw; }
  .ie-topbar-actions { gap: 5px; }
  .ie-mobile-toggle { left: 10px; width: 40px; height: 40px; }
}

.ie-bottom-tabs { display: none; }

@media (max-width: 900px) {
  /* « Plus » remplace le bouton hamburger quand la barre d'onglets existe. */
  .has-bottom-tabs .ie-mobile-toggle { display: none; }
  .has-bottom-tabs .ie-topbar { padding-left: 16px; }
  .has-bottom-tabs .ie-content { padding-bottom: calc(84px + env(safe-area-inset-bottom)); }
  /* La sidebar s'arrête au-dessus de la barre pour que « Plus » reste cliquable. */
  .has-bottom-tabs .ie-sidebar,
  .has-bottom-tabs .ie-sidebar-scrim { bottom: calc(64px + env(safe-area-inset-bottom)); }

  .ie-bottom-tabs {
    display: flex; position: fixed; left: 0; right: 0; bottom: 0; z-index: 30;
    height: calc(64px + env(safe-area-inset-bottom));
    padding: 0 4px env(safe-area-inset-bottom);
    background: #fff; border-top: 1px solid var(--ie-line);
    box-shadow: 0 -4px 18px rgba(20, 30, 40, .06);
  }
  .ie-bottom-tab {
    flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 4px; border: 0; background: transparent; cursor: pointer; font-family: inherit;
    color: var(--ie-muted); -webkit-tap-highlight-color: transparent;
  }
  .ie-bottom-tab-icon { position: relative; font-size: 19px; line-height: 1; }
  .ie-bottom-tab-label {
    font-size: 11px; font-weight: 600; max-width: 100%;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .ie-bottom-tab.is-active { color: var(--ie-red); }
  /* Onglet Marketplace : bouton central rouge, surélevé. */
  .ie-bottom-tab.is-featured { color: var(--ie-navy); }
  .ie-bottom-tab.is-featured .ie-bottom-tab-icon {
    display: grid; place-items: center; width: 52px; height: 52px; margin-top: -26px;
    border: 4px solid #fff; border-radius: 50%; background: var(--ie-red); color: #fff; font-size: 20px;
    box-shadow: 0 8px 18px rgba(192, 39, 45, 0.35); transition: transform 0.15s ease;
  }
  .ie-bottom-tab.is-featured:active .ie-bottom-tab-icon { transform: scale(0.94); }
  .ie-bottom-tab.is-featured .ie-bottom-tab-label { font-weight: 800; }
  .ie-bottom-tab.is-featured.is-active { color: var(--ie-red); }
  .ie-bottom-tab.is-featured.is-active .ie-bottom-tab-icon { box-shadow: 0 0 0 3px var(--ie-red-soft), 0 8px 18px rgba(192, 39, 45, 0.35); }
  .ie-bottom-tab.is-active .ie-bottom-tab-label { font-weight: 800; }
  .ie-bottom-tab-badge {
    position: absolute; top: -7px; right: -11px;
    background: var(--ie-red); color: #fff; font-size: 10px; font-weight: 800;
    border-radius: 999px; min-width: 16px; height: 16px; padding: 0 4px;
    display: inline-flex; align-items: center; justify-content: center;
  }
}

@media (max-width: 560px) {
  .has-bottom-tabs .ie-topbar { padding-left: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .ie-sidebar, .ie-nav-chevron { transition: none; }
}
</style>
