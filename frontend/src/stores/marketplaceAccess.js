import { defineStore } from "pinia";
import { fetchMarketplaceFeatures } from "../composables/useFeatureFlags";
import api from "../services/api";

// État partagé de l'accès aux marketplaces premium (fonctionnalités résolues
// pour « actors » + abonnements/paliers actifs), lu par la sidebar
// (DashboardLayout) et rafraîchi par TOUTE vue qui fait aboutir un abonnement
// (PremiumMarketplaceView, PartnerDashboardView, VenuesView...). Nécessaire
// car la sidebar est un layout persistant qui ne se remonte pas à chaque
// navigation interne : sans état partagé, elle resterait figée sur l'état
// d'avant paiement tant que la page n'est pas rechargée.
export const useMarketplaceAccessStore = defineStore("marketplaceAccess", {
  state: () => ({
    actorsFeatures: [],
    marketplaces: [],
    loaded: false,
  }),
  getters: {
    activeProfileSubscriptionTypes(state) {
      return new Set(state.marketplaces.filter((m) => m.is_active).map((m) => m.marketplace_type));
    },
    hasProfileMarketplaceSubscription() {
      return this.activeProfileSubscriptionTypes.has("actors") || this.activeProfileSubscriptionTypes.has("interior_design");
    },
    // Palier le plus élevé parmi les abonnements actifs du compte, tous
    // marketplaces confondus — sert de statut global affiché dans l'en-tête
    // (« Basic », « Premium »...). Aucun abonnement actif : "Basic" par
    // défaut, palier d'entrée avant toute souscription.
    currentTierLabel(state) {
      const active = state.marketplaces.filter((m) => m.is_active && m.tier_label);
      if (!active.length) return "Basic";
      return active.reduce((best, m) => (m.tier_level ?? 0) > (best.tier_level ?? 0) ? m : best, active[0]).tier_label;
    },
    isSubscribedToAny(state) {
      return state.marketplaces.some((m) => m.is_active);
    },
  },
  actions: {
    async refresh() {
      try {
        this.actorsFeatures = await fetchMarketplaceFeatures("actors");
      } catch (e) {
        this.actorsFeatures = [];
      }
      try {
        const { data } = await api.get("/marketplace/subscriptions/");
        this.marketplaces = data.marketplaces || [];
      } catch (e) {
        this.marketplaces = [];
      }
      this.loaded = true;
    },
  },
});
