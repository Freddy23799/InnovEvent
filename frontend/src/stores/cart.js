import { defineStore } from "pinia";
import { availableOf, rentalDays } from "../data/saleCategories";
import api from "../services/api";
import { useAuthStore } from "./auth";

// Panier de la boutique (Marketplace vente). Conservé dans le navigateur, par
// compte, pour survivre à un rechargement ou à un détour par une autre page.
// Le client choisit pour toute la commande : achat, ou location sur une
// période. Les prix affichés ici sont indicatifs : le serveur recalcule tout
// à la commande à partir des produits, quantités, mode et dates.

function storageKey() {
  const auth = useAuthStore();
  return `ie-cart-${auth.user?.id || "guest"}`;
}

function readStorage(key) {
  try {
    const raw = localStorage.getItem(key);
    const data = raw ? JSON.parse(raw) : null;
    // Ancien format : simple liste de lignes.
    if (Array.isArray(data)) return { items: data };
    return data || {};
  } catch (e) {
    return {};
  }
}

// Copie serveur du panier (pour la relance « panier abandonné » de
// l'assistant), envoyée en différé pour regrouper les modifications.
let syncTimer = null;
function syncToServer(items, mode) {
  clearTimeout(syncTimer);
  syncTimer = setTimeout(() => {
    api.put("/marketplace/cart/", {
      mode,
      items: items.map((item) => ({ listing: item.id, quantity: item.quantity })),
    }).catch(() => {});
  }, 1500);
}

function maxQuantity(item) {
  return item.stock === null || item.stock === undefined ? 10000 : item.stock;
}

export const useCartStore = defineStore("cart", {
  state: () => ({
    items: [],
    mode: "purchase", // "purchase" | "rental"
    rentalStart: "",
    rentalEnd: "",
    loadedKey: null,
    drawerOpen: false,
  }),
  getters: {
    count: (state) => state.items.reduce((sum, item) => sum + item.quantity, 0),
    currency: (state) => state.items[0]?.currency || "XAF",
    isRental: (state) => state.mode === "rental",
    days: (state) => (state.mode === "rental" ? rentalDays(state.rentalStart, state.rentalEnd) : 1),
    // Lignes qui ne sont pas proposées dans le mode choisi.
    incompatibleItems(state) {
      return state.items.filter((item) => (state.mode === "rental" ? !item.forRent : !item.forSale));
    },
    canRentAll: (state) => state.items.length > 0 && state.items.every((item) => item.forRent),
    canBuyAll: (state) => state.items.length > 0 && state.items.every((item) => item.forSale),
    // Location : total par jour (affiché tant que les dates ne sont pas choisies).
    perDayTotal: (state) => state.items.reduce((sum, item) => sum + (item.rentalPrice || 0) * item.quantity, 0),
    total() {
      if (this.isRental) return this.perDayTotal * Math.max(this.days, 1);
      return this.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
    },
  },
  actions: {
    lineUnit(item) {
      return this.isRental ? item.rentalPrice || 0 : item.price;
    },
    lineTotal(item) {
      return this.lineUnit(item) * item.quantity * (this.isRental ? Math.max(this.days, 1) : 1);
    },
    // Appelé par chaque écran de la boutique : recharge le panier du compte
    // connecté (un autre compte sur le même navigateur a le sien).
    ensureLoaded() {
      const key = storageKey();
      if (this.loadedKey === key) return;
      const data = readStorage(key);
      this.items = (data.items || []).map((item) => ({ forSale: true, forRent: false, rentalPrice: null, ...item }));
      this.mode = data.mode === "rental" ? "rental" : "purchase";
      this.rentalStart = data.rentalStart || "";
      this.rentalEnd = data.rentalEnd || "";
      this.loadedKey = key;
    },
    persist() {
      try {
        localStorage.setItem(storageKey(), JSON.stringify({
          items: this.items, mode: this.mode, rentalStart: this.rentalStart, rentalEnd: this.rentalEnd,
        }));
      } catch (e) {
        // stockage indisponible (navigation privée) : panier gardé en mémoire
      }
      if (useAuthStore().user) syncToServer(this.items, this.mode);
    },
    // Retourne un message d'erreur, ou "" si l'ajout a réussi. `mode` permet
    // d'ajouter un produit « à louer » directement depuis sa fiche.
    add(listing, quantity = 1, mode = null) {
      this.ensureLoaded();
      if (this.items.length && this.items[0].currency !== listing.currency) {
        return "Ce produit est vendu dans une autre devise : passez d'abord commande pour votre panier actuel.";
      }
      const existing = this.items.find((item) => item.id === listing.id);
      const snapshot = {
        id: listing.id,
        title: listing.title,
        price: Number(listing.price),
        rentalPrice: listing.rental_price ? Number(listing.rental_price) : null,
        forSale: listing.is_for_sale !== false,
        forRent: Boolean(listing.is_for_rent && listing.rental_price),
        currency: listing.currency,
        photo: listing.photo || listing.photos?.[0]?.image || null,
        stock: availableOf(listing),
      };
      if (existing) {
        Object.assign(existing, snapshot);
        existing.quantity = Math.min(existing.quantity + quantity, maxQuantity(existing));
      } else {
        this.items.push({ ...snapshot, quantity: Math.min(quantity, maxQuantity(snapshot)) });
      }
      if (mode) this.mode = mode;
      else if (this.items.length === 1) this.mode = snapshot.forSale ? "purchase" : "rental";
      else if (!snapshot.forSale && snapshot.forRent && this.canRentAll) this.mode = "rental";
      this.persist();
      return "";
    },
    setQuantity(id, quantity) {
      const item = this.items.find((i) => i.id === id);
      if (!item) return;
      item.quantity = Math.max(1, Math.min(Math.floor(quantity) || 1, maxQuantity(item)));
      this.persist();
    },
    setMode(mode) {
      this.mode = mode === "rental" ? "rental" : "purchase";
      this.persist();
    },
    setRentalDates(start, end) {
      this.rentalStart = start || "";
      this.rentalEnd = end || "";
      this.persist();
    },
    remove(id) {
      this.items = this.items.filter((item) => item.id !== id);
      this.persist();
    },
    clear() {
      this.items = [];
      this.mode = "purchase";
      this.rentalStart = "";
      this.rentalEnd = "";
      this.persist();
    },
    openDrawer() {
      this.ensureLoaded();
      this.drawerOpen = true;
    },
    closeDrawer() {
      this.drawerOpen = false;
    },
  },
});
