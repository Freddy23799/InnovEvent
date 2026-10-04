<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import logo from "../assets/images/logo-mark.png";
import InstallPwaButton from "../components/InstallPwaButton.vue";
import LanguageSwitcher from "../components/LanguageSwitcher.vue";
import NotificationBell from "../components/NotificationBell.vue";
import { useFeatureFlags } from "../composables/useFeatureFlags";
import { ACTOR_CATEGORY_GROUPS } from "../data/actorCategories";
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

// Un groupe dépliable par catégorie de métiers (10 au total), plutôt qu'un
// seul groupe « Marketplace des acteurs » avec les 42 métiers à plat — trop
// long à parcourir dans la sidebar. Filtré/verrouillé par catégorie selon le
// palier d'abonnement du compte (voir plus haut).
const actorsMarketplaceSections = computed(() =>
  ACTOR_CATEGORY_GROUPS.filter((group) => auth.role === "admin" || isActorGroupVisible(group.featureKey)).map((group) => ({
    type: "group",
    label: group.title,
    icon: group.icon,
    locked: auth.role !== "admin" && isActorGroupLocked(group.featureKey),
    children: group.items.map((item) => ({
      label: item.label,
      to: { name: "premium-marketplace", query: { type: "actors", category: item.value } },
    })),
  }))
);

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
      { type: "link", label: "Fournisseurs", to: { name: "providers-manage" }, icon: "fa-solid fa-handshake" },
      {
        type: "group", label: "Marketplaces Premium", icon: "fa-solid fa-crown", children: [
          { label: "Annonces", to: { name: "premium-marketplace-manage" } },
          { label: "Fonctionnalités & permissions", to: { name: "premium-marketplace-features-manage" } },
          { label: "Paliers d'abonnement", to: { name: "marketplace-tiers-manage" } },
          { label: "Demandes de réservation", to: { name: "premium-marketplace-booking-requests" } },
          { label: "Prestataires", to: { name: "marketplace-badges-manage" } },
          { label: "Entreprises", to: { name: "companies-manage" } },
          { label: "Talents", to: { name: "talents-manage" } },
          { label: "Analytics", to: { name: "marketplace-analytics" } },
          { label: "Commissions", to: { name: "marketplace-commissions-manage" } },
        ],
      },
      ...actorsMarketplaceSections.value,
      {
        type: "group", label: "Gestion de stock", icon: "fa-solid fa-toolbox", children: [
          { label: "Inventaire matériel", to: { name: "equipment-manage" } },
          { label: "Mouvements de stock", to: { name: "stock-movements" } },
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
      { type: "link", label: "Marché des événements", to: { name: "marketplace" }, icon: "fa-solid fa-store" },
      { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-crown" },
      ...actorsMarketplaceSections.value,
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
      { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-crown" },
      ...actorsMarketplaceSections.value,
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
      { type: "link", label: "Attestations & badges", to: { name: "attestations" }, icon: "fa-solid fa-certificate" },
      { type: "link", label: "Mes livraisons", to: { name: "my-deliveries" }, icon: "fa-solid fa-truck-fast" },
      ...(hasDriverProfile.value
        ? [{ type: "link", label: "Mon profil chauffeur", to: { name: "driver-profile" }, icon: "fa-solid fa-id-card" }]
        : []),
      { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
      { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
    ];
  }

  if (auth.role === "partner") {
    if (hasTalentProfile.value) {
      return [
        { type: "link", label: "Missions disponibles", to: { name: "talent-missions" }, icon: "fa-solid fa-briefcase" },
        { type: "link", label: "Marketplace InnovEvent", to: { name: "premium-marketplace" }, icon: "fa-solid fa-store" },
        { type: "link", label: "Mon profil talent", to: { name: "talent-profile" }, icon: "fa-solid fa-star" },
        { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
      ];
    }
    return [
      { type: "link", label: "Dashboard", to: { name: "dashboard" }, icon: "fa-solid fa-gauge-high" },
      { type: "link", label: "Mes missions", to: { name: "provider-missions" }, icon: "fa-solid fa-briefcase" },
      { type: "link", label: "Demandes de devis reçues", to: { name: "provider-quote-requests" }, icon: "fa-solid fa-file-invoice" },
      { type: "link", label: "Mes disponibilités", to: { name: "provider-availability" }, icon: "fa-solid fa-calendar-check" },
      { type: "link", label: "Mes livraisons", to: { name: "my-deliveries" }, icon: "fa-solid fa-truck-fast" },
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
    { type: "link", label: "Jeux", to: { name: "games" }, icon: "fa-solid fa-gamepad" },
    { type: "link", label: "Parrainage", to: { name: "referral" }, icon: "fa-solid fa-user-plus" },
    { type: "link", label: "Messagerie", to: { name: "messaging" }, icon: "fa-solid fa-comments", badge: unreadMessages.value },
  ];
});

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
  if (["admin", "client", "organizer"].includes(auth.role)) {
    marketplaceAccess.refresh();
  }
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
  <div class="ie-shell">
    <button class="ie-mobile-toggle" :aria-expanded="sidebarOpen" aria-controls="dashboard-navigation" @click="sidebarOpen = !sidebarOpen" :aria-label="sidebarOpen ? 'Fermer le menu' : 'Ouvrir le menu'">
      <i :class="sidebarOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars'" aria-hidden="true"></i>
    </button>
    <button v-if="sidebarOpen" class="ie-sidebar-scrim" type="button" aria-label="Fermer le menu" @click="sidebarOpen = false"></button>

    <aside id="dashboard-navigation" class="ie-sidebar" :class="{ open: sidebarOpen }">
      <div class="ie-brand">
        <img :src="logo" alt="InnovEvent" class="ie-brand-logo" />
        <div>
          <strong>InnovEvent</strong>
          <span>Gestion événementielle</span>
        </div>
      </div>

      <nav class="ie-nav">
        <template v-for="item in navSections" :key="item.label">
          <router-link
            v-if="item.type === 'link'"
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
        <router-view />
      </main>
    </div>
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

@media (prefers-reduced-motion: reduce) {
  .ie-sidebar, .ie-nav-chevron { transition: none; }
}
</style>
