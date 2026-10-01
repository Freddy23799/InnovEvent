import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../services/api";

const routes = [
  {
    path: "/",
    name: "landing",
    component: () => import("../views/marketing/LandingView.vue"),
    meta: { public: true, guestOnly: true },
  },
  {
    path: "/login",
    name: "login",
    component: () => import("../views/auth/LoginView.vue"),
    meta: { public: true, guestOnly: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../views/auth/RegisterView.vue"),
    meta: { public: true, guestOnly: true },
  },
  {
    path: "/register/:profile(client|professionnel|entreprise|talent|participant)",
    name: "register-profile",
    component: () => import("../views/auth/RegisterView.vue"),
    meta: { public: true, guestOnly: true },
  },
  {
    path: "/forgot-password",
    name: "forgot-password",
    component: () => import("../views/auth/ForgotPasswordView.vue"),
    meta: { public: true, guestOnly: true },
  },
  {
    path: "/reset-password",
    name: "reset-password",
    component: () => import("../views/auth/ResetPasswordView.vue"),
    meta: { public: true, guestOnly: true },
  },
  {
    path: "/services",
    component: () => import("../layouts/PublicCatalogLayout.vue"),
    meta: { public: true },
    children: [
      {
        path: "salles",
        name: "public-venues",
        component: () => import("../views/resources/VenuesView.vue"),
      },
      {
        path: "decoration",
        name: "public-providers-decoration",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "decoration", title: "Consulter décoration", icon: "fa-solid fa-palette" },
      },
      {
        path: "dj",
        name: "public-providers-dj",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "dj", title: "Consulter DJ", icon: "fa-solid fa-headphones" },
      },
      {
        path: "equipement",
        name: "public-equipment",
        component: () => import("../views/resources/EquipmentCatalogView.vue"),
      },
      {
        path: "packs/:packId",
        name: "public-pack-detail",
        component: () => import("../views/marketing/PackDetailView.vue"),
        props: true,
      },
    ],
  },
  {
    path: "/billets",
    component: () => import("../layouts/PublicCatalogLayout.vue"),
    meta: { public: true },
    children: [
      {
        path: ":eventId",
        name: "public-event-tickets",
        component: () => import("../views/events/PublicEventTicketsView.vue"),
        props: true,
      },
    ],
  },
  {
    path: "/suivi",
    component: () => import("../layouts/PublicCatalogLayout.vue"),
    meta: { public: true },
    children: [
      {
        path: "",
        name: "delivery-tracking",
        component: () => import("../views/deliveries/DeliveryTrackingView.vue"),
      },
    ],
  },
  {
    path: "/app",
    component: () => import("../layouts/DashboardLayout.vue"),
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("../views/dashboard/DashboardRouterView.vue"),
      },
      {
        path: "calendar",
        name: "calendar",
        component: () => import("../views/planning/CalendarView.vue"),
      },
      {
        path: "pilotage",
        name: "pilotage",
        component: () => import("../views/planning/PilotageView.vue"),
      },
      {
        path: "events",
        name: "events",
        component: () => import("../views/events/EventListView.vue"),
      },
      {
        path: "events/:id",
        name: "event-detail",
        component: () => import("../views/events/EventDetailView.vue"),
        props: true,
      },
      {
        path: "tickets",
        name: "tickets",
        component: () => import("../views/tickets/TicketTypesView.vue"),
        meta: { roles: ["admin", "organizer"] },
      },
      {
        path: "tickets/scan",
        name: "tickets-scan",
        component: () => import("../views/tickets/ScanTicketView.vue"),
      },
      {
        path: "marketplace",
        name: "marketplace",
        component: () => import("../views/events/MarketplaceView.vue"),
      },
      {
        path: "my-tickets",
        name: "my-tickets",
        component: () => import("../views/tickets/MyTicketsView.vue"),
      },
      {
        path: "games",
        name: "games",
        component: () => import("../views/games/GamesView.vue"),
      },
      {
        path: "premium-marketplace",
        name: "premium-marketplace",
        component: () => import("../views/marketplace/PremiumMarketplaceView.vue"),
      },
      {
        path: "premium-marketplace/manage",
        name: "premium-marketplace-manage",
        component: () => import("../views/marketplace/MarketplaceManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "premium-marketplace/professionals/:id",
        name: "professional-profile-detail",
        component: () => import("../views/marketplace/ProfessionalProfileDetailView.vue"),
        props: true,
      },
      {
        path: "premium-marketplace/booking-requests",
        name: "premium-marketplace-booking-requests",
        component: () => import("../views/marketplace/BookingRequestsManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "my-booking-requests",
        name: "my-booking-requests",
        component: () => import("../views/marketplace/MyBookingRequestsView.vue"),
      },
      {
        path: "my-favorites",
        name: "my-favorites",
        component: () => import("../views/marketplace/MyFavoritesView.vue"),
      },
      {
        path: "provider-quote-requests",
        name: "provider-quote-requests",
        component: () => import("../views/marketplace/ProviderQuoteRequestsView.vue"),
        meta: { roles: ["partner"] },
      },
      {
        path: "provider-availability",
        name: "provider-availability",
        component: () => import("../views/marketplace/ProviderAvailabilityView.vue"),
        meta: { roles: ["partner"] },
      },
      {
        path: "premium-marketplace/features",
        name: "premium-marketplace-features-manage",
        component: () => import("../views/marketplace/MarketplaceFeaturesManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "premium-marketplace/tiers",
        name: "marketplace-tiers-manage",
        component: () => import("../views/marketplace/SubscriptionTiersManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "premium-marketplace/badges",
        name: "marketplace-badges-manage",
        component: () => import("../views/marketplace/AdminProfessionalProfilesView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "premium-marketplace/analytics",
        name: "marketplace-analytics",
        component: () => import("../views/marketplace/MarketplaceAnalyticsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "companies-manage",
        name: "companies-manage",
        component: () => import("../views/admin/AdminCompaniesView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "talents-manage",
        name: "talents-manage",
        component: () => import("../views/admin/AdminTalentsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "premium-marketplace/commissions",
        name: "marketplace-commissions-manage",
        component: () => import("../views/marketplace/CommissionSettingsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "venues",
        name: "venues",
        component: () => import("../views/resources/VenuesView.vue"),
      },
      {
        path: "providers/dj",
        name: "providers-dj",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "dj", title: "Consulter DJ", icon: "fa-solid fa-headphones" },
      },
      {
        path: "providers/traiteur",
        name: "providers-caterer",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "caterer", title: "Consulter traiteur", icon: "fa-solid fa-utensils" },
      },
      {
        path: "providers/decoration",
        name: "providers-decoration",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "decoration", title: "Consulter décoration", icon: "fa-solid fa-palette" },
      },
      {
        path: "providers/photographie",
        name: "providers-photography",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "photography", title: "Consulter photographie", icon: "fa-solid fa-camera-retro" },
      },
      {
        path: "providers/video",
        name: "providers-video",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "video", title: "Consulter vidéo", icon: "fa-solid fa-video" },
      },
      {
        path: "providers/patisserie",
        name: "providers-pastry",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "pastry", title: "Consulter pâtisserie", icon: "fa-solid fa-cake-candles" },
      },
      {
        path: "providers/animation",
        name: "providers-animation",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "animation", title: "Consulter animation", icon: "fa-solid fa-microphone-lines" },
      },
      {
        path: "providers/impresario",
        name: "providers-impresario",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "impresario", title: "Consulter impresario", icon: "fa-solid fa-star" },
      },
      {
        path: "providers/graphisme",
        name: "providers-graphic-design",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "graphic_design", title: "Consulter graphisme & infographie", icon: "fa-solid fa-pen-nib" },
      },
      {
        path: "providers/impression",
        name: "providers-printing",
        component: () => import("../views/resources/ProvidersCategoryView.vue"),
        props: { category: "printing", title: "Consulter impression", icon: "fa-solid fa-print" },
      },
      {
        path: "equipment/catalog",
        name: "equipment-catalog",
        component: () => import("../views/resources/EquipmentCatalogView.vue"),
      },
      {
        path: "providers",
        name: "providers-manage",
        component: () => import("../views/resources/ProvidersManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "equipment",
        name: "equipment-manage",
        component: () => import("../views/resources/EquipmentManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "stock-movements",
        name: "stock-movements",
        component: () => import("../views/resources/StockMovementsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "expenses",
        name: "expenses",
        component: () => import("../views/resources/ExpensesView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "deliveries",
        name: "deliveries",
        component: () => import("../views/deliveries/DeliveriesManageView.vue"),
        meta: { roles: ["admin", "partner"] },
      },
      {
        path: "deliveries/:id",
        name: "delivery-detail",
        component: () => import("../views/deliveries/DeliveryDetailView.vue"),
        props: true,
      },
      {
        path: "deliveries-dashboard",
        name: "deliveries-dashboard",
        component: () => import("../views/deliveries/TransportDashboardView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "carriers-manage",
        name: "carriers-manage",
        component: () => import("../views/deliveries/CarriersManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "drivers-manage",
        name: "drivers-manage",
        component: () => import("../views/deliveries/DriversManageView.vue"),
        meta: { roles: ["admin", "partner"] },
      },
      {
        path: "vehicles-manage",
        name: "vehicles-manage",
        component: () => import("../views/deliveries/VehiclesManageView.vue"),
        meta: { roles: ["admin", "partner"] },
      },
      {
        path: "delivery-zones-manage",
        name: "delivery-zones-manage",
        component: () => import("../views/deliveries/DeliveryZonesManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "pricing-rules-manage",
        name: "pricing-rules-manage",
        component: () => import("../views/deliveries/PricingRulesManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "delivery-expenses",
        name: "delivery-expenses",
        component: () => import("../views/deliveries/DeliveryExpensesManageView.vue"),
        meta: { roles: ["admin", "partner"] },
      },
      {
        path: "delivery-reports",
        name: "delivery-reports",
        component: () => import("../views/deliveries/DeliveryReportsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "transporter-profile",
        name: "transporter-profile",
        component: () => import("../views/deliveries/TransporterProfileView.vue"),
        meta: { roles: ["partner"] },
      },
      {
        path: "driver-profile",
        name: "driver-profile",
        component: () => import("../views/deliveries/DriverProfileView.vue"),
        meta: { roles: ["employee", "partner"] },
      },
      {
        path: "company-profile",
        name: "company-profile",
        component: () => import("../views/companies/CompanyProfileView.vue"),
        meta: { roles: ["partner"] },
      },
      {
        path: "provider-missions",
        name: "provider-missions",
        component: () => import("../views/talents/ProviderMissionsManageView.vue"),
        meta: { roles: ["partner"], providerOnly: true },
      },
      {
        path: "talent-missions",
        name: "talent-missions",
        component: () => import("../views/talents/TalentMissionsView.vue"),
        meta: { roles: ["partner"], talentOnly: true },
      },
      {
        path: "talent-profile",
        name: "talent-profile",
        component: () => import("../views/talents/TalentProfileView.vue"),
        meta: { roles: ["partner"], talentOnly: true },
      },
      {
        path: "delivery-planning",
        name: "delivery-planning",
        component: () => import("../views/deliveries/DeliveryPlanningView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "my-deliveries",
        name: "my-deliveries",
        component: () => import("../views/deliveries/MyDeliveriesView.vue"),
      },
      {
        path: "bookings",
        name: "bookings",
        component: () => import("../views/resources/BookingsView.vue"),
      },
      {
        path: "payments",
        name: "payments",
        component: () => import("../views/payments/PaymentsView.vue"),
      },
      {
        path: "payments/dashboard",
        name: "payments-dashboard",
        component: () => import("../views/payments/PaymentsDashboardView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "users",
        name: "users",
        component: () => import("../views/admin/UsersView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "audit-log",
        name: "audit-log",
        component: () => import("../views/admin/AuditLogView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "employees",
        name: "employees",
        component: () => import("../views/admin/EmployeesView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "payroll",
        name: "payroll",
        component: () => import("../views/admin/PayrollView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "job-applications-manage",
        name: "job-applications-manage",
        component: () => import("../views/employees/JobApplicationsManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "my-job-applications",
        name: "my-job-applications",
        component: () => import("../views/employees/MyJobApplicationsView.vue"),
        meta: { roles: ["client"] },
      },
      {
        path: "referral",
        name: "referral",
        component: () => import("../views/referrals/MyReferralView.vue"),
      },
      {
        path: "referrals-manage",
        name: "referrals-manage",
        component: () => import("../views/referrals/ReferralsManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "referral-campaigns-manage",
        name: "referral-campaigns-manage",
        component: () => import("../views/referrals/ReferralCampaignsManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "trainings",
        name: "trainings",
        component: () => import("../views/training/TrainingsView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "landing-media",
        name: "landing-media",
        component: () => import("../views/admin/LandingMediaManageView.vue"),
        meta: { roles: ["admin"] },
      },
      {
        path: "landing-media/packs/:packId",
        name: "admin-pack-manage",
        component: () => import("../views/admin/PackManageView.vue"),
        meta: { roles: ["admin"] },
        props: true,
      },
      {
        path: "attestations",
        name: "attestations",
        component: () => import("../views/training/AttestationsView.vue"),
      },
      {
        path: "messaging",
        name: "messaging",
        component: () => import("../views/messaging/MessagingView.vue"),
      },
      {
        path: "profile",
        name: "profile",
        component: () => import("../views/account/ProfileView.vue"),
      },
      {
        path: "settings",
        name: "settings",
        component: () => import("../views/account/SettingsView.vue"),
      },
    ],
  },
  // Anciens liens/favoris pointant directement sous "/" (avant le passage de
  // l'espace connecté sous "/app" pour laisser la place à la page publique) :
  // redirigés plutôt que cassés.
  ...[
    "calendar", "pilotage", "events", "tickets", "tickets/scan", "marketplace", "my-tickets", "games",
    "venues", "providers/dj", "providers/traiteur", "providers/decoration", "equipment/catalog",
    "providers", "equipment", "stock-movements", "expenses", "deliveries", "deliveries-dashboard",
    "carriers-manage", "drivers-manage", "vehicles-manage", "delivery-zones-manage",
    "pricing-rules-manage", "delivery-expenses", "delivery-reports", "delivery-planning", "my-deliveries",
    "bookings", "payments", "payments/dashboard",
    "users", "audit-log", "employees", "payroll", "trainings", "attestations", "messaging", "profile", "settings",
  ].map((p) => ({ path: `/${p}`, redirect: `/app/${p}` })),
  { path: "/events/:id", redirect: (to) => `/app/events/${to.params.id}` },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("../views/NotFoundView.vue"),
    meta: { public: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.hash) return { el: to.hash, behavior: "smooth" };
    return { top: 0 };
  },
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: "login", query: { next: to.fullPath } };
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: "dashboard" };
  }
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    return { name: "dashboard" };
  }
  if (to.meta.talentOnly) {
    try {
      await api.get("/talents/me/");
    } catch {
      return { name: "dashboard" };
    }
  }
  if (to.meta.providerOnly) {
    try {
      await api.get("/talents/me/");
      return { name: "dashboard" };
    } catch {
      // Un compte partenaire sans profil talent peut gérer ses offres.
    }
  }
  return true;
});

export default router;
