<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { SALE_CATEGORIES, formatMoney } from "../../data/saleCategories";
import { useCartStore } from "../../stores/cart";
import CartDrawer from "./CartDrawer.vue";

// En-tête commun aux écrans de la boutique : recherche par rayon, accès aux
// commandes et au panier, menu des catégories et fil d'Ariane.
defineProps({
  crumbs: { type: Array, default: () => [] },
});

const route = useRoute();
const router = useRouter();
const cart = useCartStore();

const search = ref("");
const searchCategory = ref("");
const megaOpen = ref(false);
const megaRef = ref(null);

function syncFromRoute() {
  if (route.name !== "sale-shop") return;
  search.value = typeof route.query.q === "string" ? route.query.q : "";
  searchCategory.value = typeof route.query.category === "string" ? route.query.category : "";
}

function submitSearch() {
  router.push({
    name: "sale-shop",
    query: { q: search.value.trim() || undefined, category: searchCategory.value || undefined },
  });
}

function goCategory(category, subcategory) {
  megaOpen.value = false;
  router.push({ name: "sale-shop", query: { category, sub: subcategory || undefined } });
}

function isActive(category) {
  return route.name === "sale-shop" && route.query.category === category;
}

function onDocumentClick(event) {
  if (megaOpen.value && megaRef.value && !megaRef.value.contains(event.target)) megaOpen.value = false;
}
function onKeydown(event) {
  if (event.key === "Escape") megaOpen.value = false;
}

watch(() => route.query, syncFromRoute);
onMounted(() => {
  cart.ensureLoaded();
  syncFromRoute();
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <div class="sh">
    <header class="sh-top">
      <router-link :to="{ name: 'sale-shop' }" class="sh-brand">
        <span class="sh-brand-mark"><i class="fa-solid fa-bag-shopping"></i></span>
        <span class="sh-brand-text"><strong>Boutique</strong><small>InnovEvent</small></span>
      </router-link>

      <form class="sh-search" role="search" @submit.prevent="submitSearch">
        <select v-model="searchCategory" class="sh-search-cat" aria-label="Rayon">
          <option value="">Tous les rayons</option>
          <option v-for="cat in SALE_CATEGORIES" :key="cat.value" :value="cat.value">{{ cat.label }}</option>
        </select>
        <input v-model="search" type="search" placeholder="Rechercher : verres, chaises, nappes…" aria-label="Rechercher un produit" />
        <button type="submit" aria-label="Rechercher"><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>

      <div class="sh-actions">
        <router-link :to="{ name: 'sale-orders' }" class="sh-action">
          <i class="fa-solid fa-file-invoice"></i>
          <span class="sh-action-text"><small>Factures</small><strong>Mes commandes</strong></span>
        </router-link>
        <button type="button" class="sh-action sh-cart" :aria-label="`Ouvrir le panier (${cart.count} pièces)`" @click="cart.openDrawer()">
          <span class="sh-cart-icon">
            <i class="fa-solid fa-cart-shopping"></i>
            <b v-if="cart.count">{{ cart.count > 99 ? "99+" : cart.count }}</b>
          </span>
          <span class="sh-action-text"><small>Panier</small><strong>{{ formatMoney(cart.total, cart.currency) }}</strong></span>
        </button>
      </div>
    </header>

    <nav ref="megaRef" class="sh-nav" aria-label="Rayons de la boutique">
      <button type="button" class="sh-all" :aria-expanded="megaOpen" @click.stop="megaOpen = !megaOpen">
        <i class="fa-solid fa-bars"></i> Toutes les catégories <i class="fa-solid fa-chevron-down sh-chev" :class="{ open: megaOpen }"></i>
      </button>
      <div class="sh-links">
        <button
          v-for="cat in SALE_CATEGORIES.filter((c) => c.value !== 'other')" :key="cat.value" type="button"
          :class="{ active: isActive(cat.value) }" @click="goCategory(cat.value)"
        >
          {{ cat.label }}
        </button>
      </div>

      <div v-if="megaOpen" class="sh-mega">
        <div v-for="cat in SALE_CATEGORIES" :key="cat.value" class="sh-mega-col">
          <button type="button" class="sh-mega-title" @click="goCategory(cat.value)">
            <span><i :class="cat.icon"></i></span> {{ cat.label }}
          </button>
          <button v-for="sub in cat.subcategories" :key="sub.value" type="button" class="sh-mega-sub" @click="goCategory(cat.value, sub.value)">
            {{ sub.label }}
          </button>
        </div>
      </div>
    </nav>

    <nav v-if="crumbs.length" class="sh-crumbs" aria-label="Fil d'Ariane">
      <router-link :to="{ name: 'sale-shop' }">Boutique</router-link>
      <template v-for="crumb in crumbs" :key="crumb.label">
        <i class="fa-solid fa-chevron-right"></i>
        <router-link v-if="crumb.to" :to="crumb.to">{{ crumb.label }}</router-link>
        <span v-else>{{ crumb.label }}</span>
      </template>
    </nav>
  </div>
  <CartDrawer />
</template>

<style scoped>
.sh { margin-bottom: 20px; }
.sh-top {
  display: flex; align-items: center; gap: 18px; padding: 12px 16px; border-radius: 14px 14px 0 0;
  background: #172638; color: #fff;
}
.sh-brand { display: flex; align-items: center; gap: 10px; color: #fff; text-decoration: none; flex-shrink: 0; }
.sh-brand-mark { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: var(--ie-red); font-size: 16px; }
.sh-brand-text { display: flex; flex-direction: column; line-height: 1.05; }
.sh-brand-text strong { font-size: 16px; letter-spacing: 0.01em; }
.sh-brand-text small { color: #9fb0c2; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }

.sh-search { flex: 1; display: flex; min-width: 0; height: 44px; overflow: hidden; border-radius: 10px; background: #fff; box-shadow: 0 0 0 2px transparent; transition: box-shadow 0.15s ease; }
.sh-search:focus-within { box-shadow: 0 0 0 3px #dd595c; }
.sh-search-cat { max-width: 160px; padding: 0 10px; border: 0; border-right: 1px solid #e4e7eb; background: #f3f4f6; color: #39495b; font-size: 12.5px; font-weight: 600; font-family: inherit; cursor: pointer; }
.sh-search input { flex: 1; min-width: 0; padding: 0 14px; border: 0; color: var(--ie-ink); font-size: 14px; font-family: inherit; }
.sh-search input:focus, .sh-search-cat:focus { outline: none; }
.sh-search button { width: 54px; border: 0; background: var(--ie-red); color: #fff; font-size: 16px; cursor: pointer; }
.sh-search button:hover { background: #a11f25; }

.sh-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.sh-action {
  display: flex; align-items: center; gap: 9px; padding: 6px 10px; border: 1px solid transparent; border-radius: 10px;
  background: none; color: #fff; text-decoration: none; cursor: pointer; font-family: inherit; text-align: left;
}
.sh-action:hover { border-color: #ffffff40; }
.sh-action > i { font-size: 18px; color: #c9d4df; }
.sh-action-text { display: flex; flex-direction: column; line-height: 1.15; }
.sh-action small { color: #9fb0c2; font-size: 11px; }
.sh-action strong { font-size: 13px; white-space: nowrap; }
.sh-cart-icon { position: relative; font-size: 20px; }
.sh-cart-icon b {
  position: absolute; top: -8px; right: -10px; display: grid; place-items: center; min-width: 18px; height: 18px; padding: 0 4px;
  border-radius: 999px; background: var(--ie-red); color: #fff; font-size: 10.5px; font-weight: 800;
}

.sh-nav { position: relative; display: flex; align-items: center; gap: 6px; padding: 0 10px; border-radius: 0 0 14px 14px; background: #24384f; }
.sh-all {
  display: inline-flex; align-items: center; gap: 8px; flex-shrink: 0; padding: 11px 12px; border: 0; background: none;
  color: #fff; font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit;
}
.sh-all:hover, .sh-links button:hover { background: #ffffff14; }
.sh-chev { font-size: 9px; transition: transform 0.15s ease; }
.sh-chev.open { transform: rotate(180deg); }
.sh-links { display: flex; gap: 2px; min-width: 0; overflow-x: auto; scrollbar-width: none; }
.sh-links::-webkit-scrollbar { display: none; }
.sh-links button {
  flex-shrink: 0; padding: 11px 12px; border: 0; border-bottom: 2px solid transparent; background: none;
  color: #dbe3ec; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.sh-links button.active { color: #fff; border-bottom-color: var(--ie-red); }

.sh-mega {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 40; display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 18px 20px; margin-top: 6px; padding: 20px 22px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff;
  box-shadow: 0 24px 50px #18283b2e;
}
.sh-mega-col { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; }
.sh-mega-title {
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px; padding: 0; border: 0; background: none;
  color: var(--ie-navy); font-size: 14px; font-weight: 800; cursor: pointer; font-family: inherit;
}
.sh-mega-title span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; background: var(--ie-red-soft); color: var(--ie-red); font-size: 12px; }
.sh-mega-title:hover { color: var(--ie-red); }
.sh-mega-sub { padding: 3px 0 3px 36px; border: 0; background: none; color: #5d6771; font-size: 13px; cursor: pointer; font-family: inherit; text-align: left; }
.sh-mega-sub:hover { color: var(--ie-red); text-decoration: underline; }

.sh-crumbs { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 14px; font-size: 13px; color: var(--ie-muted); }
.sh-crumbs a { color: var(--ie-navy); font-weight: 600; text-decoration: none; }
.sh-crumbs a:hover { color: var(--ie-red); text-decoration: underline; }
.sh-crumbs i { font-size: 8px; opacity: 0.6; }
.sh-crumbs span { color: var(--ie-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 60vw; }

@media (max-width: 980px) {
  .sh-top { flex-wrap: wrap; gap: 10px 12px; }
  .sh-search { order: 3; flex-basis: 100%; }
  .sh-actions { margin-left: auto; }
}
@media (max-width: 560px) {
  .sh-top { padding: 10px 12px; }
  .sh-action-text { display: none; }
  .sh-action { padding: 6px 8px; }
  .sh-search-cat { max-width: 96px; font-size: 11.5px; }
  .sh-all { padding: 10px 8px; }
  .sh-mega { grid-template-columns: 1fr 1fr; padding: 16px; max-height: 70vh; overflow-y: auto; }
}
</style>
