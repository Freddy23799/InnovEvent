<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import ShopBar from "../../components/shop/ShopBar.vue";
import { SALE_CATEGORIES, availableOf, findCategory, formatMoney, offerModes, productImages, stockLabel, subcategoryLabel } from "../../data/saleCategories";
import api from "../../services/api";
import { useCartStore } from "../../stores/cart";
import { useToastStore } from "../../stores/toast";

// Boutique InnovEvent (Marketplace vente) : entièrement gratuite, sans
// abonnement. Rayon, sous-catégorie et recherche vivent dans l'URL
// (?category=…&sub=…&q=…) pour que l'en-tête et les liens partagés s'accordent.
const route = useRoute();
const router = useRouter();
const cart = useCartStore();
const toast = useToastStore();

const products = ref([]);
const loading = ref(true);
const filters = reactive({ minPrice: "", maxPrice: "", inStockOnly: false, offer: "", sort: "" });
const filtersOpen = ref(false);
const justAdded = reactive({});

const query = computed(() => (typeof route.query.q === "string" ? route.query.q.trim() : ""));
const activeCategory = computed(() => (typeof route.query.category === "string" ? route.query.category : ""));
const activeSub = computed(() => (typeof route.query.sub === "string" ? route.query.sub : ""));
const activeCategoryMeta = computed(() => findCategory(activeCategory.value));
const isLanding = computed(() => !query.value && !activeCategory.value);

async function loadProducts() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/listings/", { params: { marketplace_type: "sale", is_active: true } });
    products.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function categoryOf(product) {
  return product.category || "other";
}

const counts = computed(() => {
  const byCategory = {};
  const bySub = {};
  products.value.forEach((p) => {
    const cat = categoryOf(p);
    byCategory[cat] = (byCategory[cat] || 0) + 1;
    if (p.subcategory) bySub[`${cat}:${p.subcategory}`] = (bySub[`${cat}:${p.subcategory}`] || 0) + 1;
  });
  return { byCategory, bySub };
});

function matchesSearch(product) {
  if (!query.value) return true;
  const needle = query.value.toLowerCase();
  const haystack = [
    product.title, product.description, product.category_display,
    subcategoryLabel(product.category, product.subcategory),
  ].join(" ").toLowerCase();
  return haystack.includes(needle);
}

const filteredProducts = computed(() => {
  const min = filters.minPrice === "" ? null : Number(filters.minPrice);
  const max = filters.maxPrice === "" ? null : Number(filters.maxPrice);
  let result = products.value.filter((p) => {
    if (activeCategory.value && categoryOf(p) !== activeCategory.value) return false;
    if (activeSub.value && p.subcategory !== activeSub.value) return false;
    if (min !== null && Number(p.price) < min) return false;
    if (max !== null && Number(p.price) > max) return false;
    if (filters.inStockOnly && availableOf(p) === 0) return false;
    if (filters.offer === "sale" && !offerModes(p).sale) return false;
    if (filters.offer === "rent" && !offerModes(p).rent) return false;
    return matchesSearch(p);
  });
  result = [...result];
  const shownPrice = (p) => Number(cart.isRental && p.rental_price ? p.rental_price : p.price);
  if (filters.sort === "price_asc") result.sort((a, b) => shownPrice(a) - shownPrice(b));
  else if (filters.sort === "price_desc") result.sort((a, b) => shownPrice(b) - shownPrice(a));
  else if (filters.sort === "newest") result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  // Les produits en rupture passent en fin de liste.
  return result.sort((a, b) => Number(availableOf(a) === 0) - Number(availableOf(b) === 0));
});

const newArrivals = computed(() =>
  [...products.value].filter((p) => availableOf(p) !== 0).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 4)
);
const activeFilterCount = computed(() =>
  [filters.minPrice !== "", filters.maxPrice !== "", filters.inStockOnly, filters.offer !== ""].filter(Boolean).length
);

function goTo(category, sub) {
  filtersOpen.value = false;
  router.push({ name: "sale-shop", query: { q: query.value || undefined, category: category || undefined, sub: sub || undefined } });
}

function resetFilters() {
  Object.assign(filters, { minPrice: "", maxPrice: "", inStockOnly: false, offer: "" });
}

function clearSearch() {
  router.push({ name: "sale-shop", query: { category: activeCategory.value || undefined, sub: activeSub.value || undefined } });
}

function productTag(product) {
  return subcategoryLabel(product.category, product.subcategory) || product.category_display || "Équipement";
}

function cartQuantity(product) {
  return cart.items.find((i) => i.id === product.id)?.quantity || 0;
}

function canAdd(product) {
  const stock = availableOf(product);
  return stock === null || stock > cartQuantity(product);
}

function addToCart(product) {
  const error = cart.add(product, 1, cart.isRental && offerModes(product).rent ? "rental" : !offerModes(product).sale ? "rental" : null);
  if (error) {
    toast.error(error);
    return;
  }
  justAdded[product.id] = true;
  setTimeout(() => { justAdded[product.id] = false; }, 1600);
}

function scrollToCatalog() {
  document.getElementById("shop-catalog")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

const crumbs = computed(() => {
  const list = [];
  if (activeCategoryMeta.value) {
    list.push({ label: activeCategoryMeta.value.label, to: activeSub.value ? { name: "sale-shop", query: { category: activeCategory.value } } : null });
    if (activeSub.value) list.push({ label: subcategoryLabel(activeCategory.value, activeSub.value) });
  }
  if (query.value) list.push({ label: `Recherche « ${query.value} »` });
  return list;
});

watch(() => route.query, () => { filtersOpen.value = false; });
onMounted(loadProducts);
</script>

<template>
  <div class="shop">
    <ShopBar :crumbs="crumbs" />

    <!-- Accueil de la boutique -->
    <template v-if="isLanding">
      <section class="shop-hero">
        <div class="shop-hero-main">
          <span class="shop-eyebrow"><i class="fa-solid fa-gift"></i> Accès gratuit · sans abonnement</span>
          <h1>Tout le matériel pour réussir vos événements</h1>
          <p>Mobilier, art de la table, décoration, éclairage, son… Achetez ou louez pour la durée de votre événement : le total se calcule automatiquement et votre facture est prête en un clic.</p>
          <div class="shop-hero-ctas">
            <button type="button" class="ie-btn ie-btn-primary" @click="scrollToCatalog">Voir tous les produits</button>
            <button type="button" class="shop-hero-ghost" @click="goTo('tableware')">Art de la table <i class="fa-solid fa-arrow-right"></i></button>
          </div>
        </div>
        <div class="shop-hero-side">
          <button type="button" class="shop-promo promo-a" @click="goTo('furniture', 'chairs')">
            <span><small>Mobilier</small><strong>Chaises & tables</strong><em>Découvrir <i class="fa-solid fa-arrow-right"></i></em></span>
            <i class="fa-solid fa-chair"></i>
          </button>
          <button type="button" class="shop-promo promo-b" @click="goTo('tableware', 'glasses')">
            <span><small>Art de la table</small><strong>Verres & vaisselle</strong><em>Découvrir <i class="fa-solid fa-arrow-right"></i></em></span>
            <i class="fa-solid fa-wine-glass"></i>
          </button>
        </div>
      </section>

      <ul class="shop-trust">
        <li><i class="fa-solid fa-calendar-days"></i><span><strong>Achat ou location</strong><small>Louez à la journée</small></span></li>
        <li><i class="fa-solid fa-file-invoice"></i><span><strong>Facture immédiate</strong><small>PDF prêt à télécharger</small></span></li>
        <li><i class="fa-solid fa-hand-holding-dollar"></i><span><strong>Paiement à la livraison</strong><small>Aucune carte demandée</small></span></li>
        <li><i class="fa-solid fa-shield-halved"></i><span><strong>Produits vérifiés</strong><small>Sélectionnés par InnovEvent</small></span></li>
      </ul>

      <section class="shop-section">
        <div class="shop-section-head">
          <h2>Acheter par rayon</h2>
        </div>
        <div class="shop-depts">
          <article v-for="cat in SALE_CATEGORIES.filter((c) => c.value !== 'other')" :key="cat.value" class="shop-dept">
            <button type="button" class="shop-dept-head" @click="goTo(cat.value)">
              <span class="shop-dept-icon"><i :class="cat.icon"></i></span>
              <span>
                <strong>{{ cat.label }}</strong>
                <small>{{ counts.byCategory[cat.value] || 0 }} produit{{ (counts.byCategory[cat.value] || 0) > 1 ? "s" : "" }}</small>
              </span>
            </button>
            <div class="shop-dept-subs">
              <button v-for="sub in cat.subcategories.slice(0, 4)" :key="sub.value" type="button" @click="goTo(cat.value, sub.value)">{{ sub.label }}</button>
            </div>
            <button type="button" class="shop-dept-more" @click="goTo(cat.value)">Tout le rayon <i class="fa-solid fa-arrow-right"></i></button>
          </article>
        </div>
      </section>

      <section v-if="newArrivals.length" class="shop-section">
        <div class="shop-section-head">
          <h2>Nouveautés</h2>
          <button type="button" class="shop-link" @click="filters.sort = 'newest'; scrollToCatalog()">Tout voir <i class="fa-solid fa-arrow-right"></i></button>
        </div>
        <div class="shop-grid shop-grid-4">
          <article v-for="product in newArrivals" :key="product.id" class="card">
            <router-link :to="{ name: 'sale-product', params: { id: product.id } }" class="card-media">
              <img v-if="productImages(product)[0]" v-img="productImages(product)[0]" :alt="product.title" />
              <i v-else class="fa-solid fa-box-open"></i>
              <span class="card-badge">Nouveau</span>
            </router-link>
            <div class="card-body">
              <span class="card-tag">{{ productTag(product) }}</span>
              <router-link :to="{ name: 'sale-product', params: { id: product.id } }" class="card-title">{{ product.title }}</router-link>
              <div class="card-price">
                <template v-if="offerModes(product).sale">{{ formatMoney(product.price, product.currency) }}</template>
                <template v-else>{{ formatMoney(product.rental_price, product.currency) }} <small>/ jour</small></template>
              </div>
            </div>
          </article>
        </div>
      </section>
    </template>

    <!-- En-tête d'un rayon / d'une recherche -->
    <section v-else class="shop-dept-banner">
      <div class="shop-dept-banner-text">
        <span v-if="activeCategoryMeta" class="shop-dept-banner-icon"><i :class="activeCategoryMeta.icon"></i></span>
        <div>
          <h1>
            <template v-if="activeSub">{{ subcategoryLabel(activeCategory, activeSub) }}</template>
            <template v-else-if="activeCategoryMeta">{{ activeCategoryMeta.label }}</template>
            <template v-else>Résultats de recherche</template>
          </h1>
          <p>
            <template v-if="query">Pour « {{ query }} » <button type="button" class="shop-link" @click="clearSearch">effacer</button></template>
            <template v-else-if="activeCategoryMeta">{{ activeCategoryMeta.tagline }}</template>
          </p>
        </div>
      </div>
      <div v-if="activeCategoryMeta && activeCategoryMeta.subcategories.length" class="shop-subchips">
        <button type="button" :class="{ active: !activeSub }" @click="goTo(activeCategory)">Tout</button>
        <button
          v-for="sub in activeCategoryMeta.subcategories" :key="sub.value" type="button"
          :class="{ active: activeSub === sub.value }" @click="goTo(activeCategory, sub.value)"
        >
          {{ sub.label }} <span v-if="counts.bySub[`${activeCategory}:${sub.value}`]">{{ counts.bySub[`${activeCategory}:${sub.value}`] }}</span>
        </button>
      </div>
    </section>

    <!-- Catalogue : filtres + produits -->
    <section id="shop-catalog" class="shop-catalog">
      <aside class="shop-filters" :class="{ open: filtersOpen }">
        <div class="shop-filters-head">
          <strong>Filtres</strong>
          <button type="button" class="shop-filters-close" aria-label="Fermer les filtres" @click="filtersOpen = false"><i class="fa-solid fa-xmark"></i></button>
        </div>

        <div class="shop-filter">
          <h3>Rayons</h3>
          <button type="button" class="shop-tree-item" :class="{ active: !activeCategory }" @click="goTo('')">
            Tous les produits <span>{{ products.length }}</span>
          </button>
          <template v-for="cat in SALE_CATEGORIES" :key="cat.value">
            <button
              v-if="counts.byCategory[cat.value] || activeCategory === cat.value" type="button"
              class="shop-tree-item" :class="{ active: activeCategory === cat.value && !activeSub }" @click="goTo(cat.value)"
            >
              <i :class="cat.icon"></i> {{ cat.label }} <span>{{ counts.byCategory[cat.value] || 0 }}</span>
            </button>
            <div v-if="activeCategory === cat.value && cat.subcategories.length" class="shop-tree-subs">
              <button
                v-for="sub in cat.subcategories" :key="sub.value" type="button"
                :class="{ active: activeSub === sub.value }" @click="goTo(cat.value, sub.value)"
              >
                {{ sub.label }} <span>{{ counts.bySub[`${cat.value}:${sub.value}`] || 0 }}</span>
              </button>
            </div>
          </template>
        </div>

        <div class="shop-filter">
          <h3>Prix (FCFA)</h3>
          <div class="shop-price">
            <input v-model="filters.minPrice" type="number" min="0" class="ie-input" placeholder="Min" aria-label="Prix minimum" />
            <span>—</span>
            <input v-model="filters.maxPrice" type="number" min="0" class="ie-input" placeholder="Max" aria-label="Prix maximum" />
          </div>
        </div>

        <div class="shop-filter">
          <h3>Disponibilité</h3>
          <label class="shop-check"><input v-model="filters.inStockOnly" type="checkbox" /> En stock uniquement</label>
        </div>

        <div class="shop-filter">
          <h3>Type d'offre</h3>
          <label class="shop-check"><input v-model="filters.offer" type="radio" value="" /> Achat et location</label>
          <label class="shop-check"><input v-model="filters.offer" type="radio" value="sale" /> À acheter</label>
          <label class="shop-check"><input v-model="filters.offer" type="radio" value="rent" /> À louer</label>
        </div>

        <button v-if="activeFilterCount" type="button" class="ie-btn ie-btn-ghost ie-btn-sm shop-reset" @click="resetFilters">
          <i class="fa-solid fa-rotate-left"></i> Réinitialiser les filtres
        </button>
      </aside>
      <button v-if="filtersOpen" type="button" class="shop-filters-scrim" aria-label="Fermer les filtres" @click="filtersOpen = false"></button>

      <div class="shop-results">
        <div class="shop-toolbar">
          <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm shop-filters-toggle" @click="filtersOpen = true">
            <i class="fa-solid fa-sliders"></i> Filtres <span v-if="activeFilterCount">({{ activeFilterCount }})</span>
          </button>
          <div class="shop-mode" role="radiogroup" aria-label="Acheter ou louer">
            <button type="button" role="radio" :aria-checked="!cart.isRental" :class="{ active: !cart.isRental }" @click="cart.setMode('purchase')">
              <i class="fa-solid fa-bag-shopping"></i> Acheter
            </button>
            <button type="button" role="radio" :aria-checked="cart.isRental" :class="{ active: cart.isRental }" @click="cart.setMode('rental')">
              <i class="fa-solid fa-calendar-days"></i> Louer
            </button>
          </div>
          <p class="shop-count"><strong>{{ filteredProducts.length }}</strong> produit{{ filteredProducts.length > 1 ? "s" : "" }}</p>
          <label class="shop-sort">
            <span>Trier par</span>
            <select v-model="filters.sort" class="ie-select">
              <option value="">Pertinence</option>
              <option value="newest">Nouveautés</option>
              <option value="price_asc">Prix croissant</option>
              <option value="price_desc">Prix décroissant</option>
            </select>
          </label>
        </div>

        <div v-if="loading" class="shop-grid" aria-busy="true">
          <div v-for="i in 6" :key="i" class="ie-skeleton" style="height: 340px; border-radius: 12px;"></div>
        </div>
        <div v-else-if="filteredProducts.length" class="shop-grid">
          <article v-for="product in filteredProducts" :key="product.id" class="card" :class="{ 'is-out': availableOf(product) === 0 }">
            <router-link :to="{ name: 'sale-product', params: { id: product.id } }" class="card-media">
              <img v-if="productImages(product)[0]" v-img="productImages(product)[0]" :alt="product.title" />
              <i v-else class="fa-solid fa-box-open"></i>
              <span v-if="productImages(product).length > 1" class="card-photos"><i class="fa-regular fa-images"></i> {{ productImages(product).length }}</span>
              <span v-if="availableOf(product) === 0" class="card-out">Rupture de stock</span>
              <span class="card-offers">
                <em v-if="offerModes(product).sale">Achat</em>
                <em v-if="offerModes(product).rent" class="rent">Location</em>
              </span>
            </router-link>
            <div class="card-body">
              <span class="card-tag">{{ productTag(product) }}</span>
              <router-link :to="{ name: 'sale-product', params: { id: product.id } }" class="card-title">{{ product.title }}</router-link>
              <!-- Le prix principal suit le mode choisi (Acheter / Louer). -->
              <template v-if="cart.isRental && offerModes(product).rent">
                <div class="card-price">{{ formatMoney(product.rental_price, product.currency) }} <small>/ jour</small></div>
                <div v-if="offerModes(product).sale" class="card-rent">Achat : {{ formatMoney(product.price, product.currency) }}</div>
              </template>
              <template v-else-if="offerModes(product).sale">
                <div class="card-price">{{ formatMoney(product.price, product.currency) }} <small>/ pièce</small></div>
                <div v-if="offerModes(product).rent" class="card-rent">ou location {{ formatMoney(product.rental_price, product.currency) }} / jour</div>
                <div v-else-if="cart.isRental" class="card-rent card-rent-off">Achat uniquement</div>
              </template>
              <template v-else>
                <div class="card-price">{{ formatMoney(product.rental_price, product.currency) }} <small>/ jour</small></div>
                <div class="card-rent card-rent-off">Location uniquement</div>
              </template>
              <span class="card-stock" :class="stockLabel(product).tone"><i class="fa-solid fa-circle"></i> {{ stockLabel(product).text }}</span>
              <button
                type="button" class="card-add" :class="{ added: justAdded[product.id] }"
                :disabled="!canAdd(product)" @click="addToCart(product)"
              >
                <template v-if="justAdded[product.id]"><i class="fa-solid fa-check"></i> Ajouté</template>
                <template v-else-if="availableOf(product) === 0">Indisponible</template>
                <template v-else-if="!canAdd(product)">Stock max. au panier</template>
                <template v-else><i class="fa-solid fa-cart-plus"></i> Ajouter au panier</template>
              </button>
              <span v-if="cartQuantity(product)" class="card-incart">{{ cartQuantity(product) }} dans votre panier</span>
            </div>
          </article>
        </div>
        <EmptyState
          v-else icon="fa-solid fa-box-open"
          :text="products.length ? 'Aucun produit ne correspond à ces critères.' : 'La boutique sera bientôt remplie de nouveaux équipements.'"
        >
          <button v-if="products.length" type="button" class="ie-btn ie-btn-ghost" @click="resetFilters(); goTo('')">Voir tous les produits</button>
        </EmptyState>
      </div>
    </section>
  </div>
</template>

<style scoped>
.shop { max-width: 1280px; margin: 0 auto; min-width: 0; }

/* Accueil */
.shop-hero { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 14px; }
.shop-hero-main {
  display: flex; flex-direction: column; justify-content: center; min-height: 280px; padding: 36px 40px; border-radius: 16px; color: #fff;
  background: var(--ie-hero-gradient);
}
.shop-eyebrow { display: inline-flex; align-items: center; gap: 7px; align-self: flex-start; padding: 5px 11px; border-radius: 999px; background: #ffffff1f; color: #ffe1e1; font-size: 11px; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; }
.shop-hero h1 { margin: 14px 0 10px; max-width: 560px; color: #fff; font-size: clamp(26px, 3.4vw, 38px); line-height: 1.1; }
.shop-hero p { margin: 0; max-width: 540px; color: #d9e2eb; font-size: 14.5px; line-height: 1.6; }
.shop-hero-ctas { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
.shop-hero-ctas .ie-btn { padding: 12px 20px; }
.shop-hero-ghost { display: inline-flex; align-items: center; gap: 8px; padding: 12px 18px; border: 1px solid #ffffff55; border-radius: 8px; background: none; color: #fff; font-weight: 700; font-size: 14px; cursor: pointer; font-family: inherit; }
.shop-hero-ghost:hover { background: #ffffff14; }
.shop-hero-side { display: grid; gap: 14px; }
.shop-promo {
  position: relative; display: flex; align-items: flex-end; overflow: hidden; padding: 20px; border: 0; border-radius: 16px;
  text-align: left; cursor: pointer; font-family: inherit;
}
.shop-promo > i { position: absolute; right: -8px; bottom: -14px; font-size: 96px; opacity: 0.16; transition: transform 0.3s ease; }
.shop-promo:hover > i { transform: scale(1.08) rotate(-4deg); }
.shop-promo span { position: relative; display: flex; flex-direction: column; gap: 3px; }
.shop-promo small { font-size: 11px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.8; }
.shop-promo strong { font-size: 19px; }
.shop-promo em { margin-top: 6px; font-size: 12.5px; font-style: normal; font-weight: 700; }
.promo-a { background: #f6e2e3; color: #8d1c21; }
.promo-b { background: #e7edf3; color: #24384f; }

.shop-trust {
  display: grid; grid-template-columns: repeat(4, 1fr); margin: 14px 0 0; padding: 0; overflow: hidden; list-style: none;
  border: 1px solid var(--ie-line); border-radius: 14px; background: #fff;
}
.shop-trust li { display: flex; align-items: center; gap: 12px; padding: 16px 18px; }
.shop-trust li + li { border-left: 1px solid var(--ie-line); }
.shop-trust i { display: grid; place-items: center; width: 40px; height: 40px; flex: 0 0 40px; border-radius: 10px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 16px; }
.shop-trust span { display: flex; flex-direction: column; min-width: 0; }
.shop-trust strong { color: var(--ie-navy); font-size: 13.5px; }
.shop-trust small { color: var(--ie-muted); font-size: 12px; }

.shop-section { margin-top: 30px; }
.shop-section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.shop-section-head h2 { margin: 0; color: var(--ie-navy); font-size: 20px; }
.shop-link { padding: 0; border: 0; background: none; color: var(--ie-red); font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit; }
.shop-link:hover { text-decoration: underline; }

.shop-depts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.shop-dept { display: flex; flex-direction: column; gap: 12px; padding: 18px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; transition: box-shadow 0.2s ease, border-color 0.2s ease; }
.shop-dept:hover { border-color: #cfd5dc; box-shadow: 0 12px 28px #18283b12; }
.shop-dept-head { display: flex; align-items: center; gap: 12px; padding: 0; border: 0; background: none; text-align: left; cursor: pointer; font-family: inherit; }
.shop-dept-icon { display: grid; place-items: center; width: 48px; height: 48px; flex: 0 0 48px; border-radius: 12px; background: var(--ie-red-soft); color: var(--ie-red); font-size: 20px; }
.shop-dept-head span:last-child { display: flex; flex-direction: column; }
.shop-dept-head strong { color: var(--ie-navy); font-size: 15px; }
.shop-dept-head small { color: var(--ie-muted); font-size: 12px; }
.shop-dept-subs { display: flex; flex-wrap: wrap; gap: 6px; }
.shop-dept-subs button { padding: 5px 10px; border: 1px solid var(--ie-line); border-radius: 999px; background: #fafbfc; color: #4b5a6a; font-size: 12px; cursor: pointer; font-family: inherit; }
.shop-dept-subs button:hover { border-color: var(--ie-navy); color: var(--ie-navy); }
.shop-dept-more { margin-top: auto; align-self: flex-start; padding: 0; border: 0; background: none; color: var(--ie-red); font-size: 12.5px; font-weight: 700; cursor: pointer; font-family: inherit; }

/* Bandeau rayon / recherche */
.shop-dept-banner { padding: 20px 22px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; }
.shop-dept-banner-text { display: flex; align-items: center; gap: 14px; }
.shop-dept-banner-icon { display: grid; place-items: center; width: 52px; height: 52px; flex: 0 0 52px; border-radius: 14px; background: var(--ie-red-soft); color: var(--ie-red); font-size: 22px; }
.shop-dept-banner h1 { margin: 0; color: var(--ie-navy); font-size: 24px; }
.shop-dept-banner p { margin: 2px 0 0; color: var(--ie-muted); font-size: 13.5px; }
.shop-subchips { display: flex; gap: 8px; margin-top: 16px; overflow-x: auto; padding-bottom: 2px; }
.shop-subchips button {
  display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; padding: 8px 14px; border: 1px solid var(--ie-line); border-radius: 999px;
  background: #fff; color: var(--ie-navy); font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.shop-subchips button span { padding: 0 6px; border-radius: 999px; background: #f0f3f7; color: var(--ie-muted); font-size: 11px; }
.shop-subchips button.active { background: var(--ie-navy); border-color: var(--ie-navy); color: #fff; }
.shop-subchips button.active span { background: #ffffff26; color: #fff; }

/* Catalogue */
.shop-catalog { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 22px; align-items: start; margin-top: 26px; scroll-margin-top: 10px; }
.shop-filters { position: sticky; top: 0; padding: 18px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; }
.shop-filters-head { display: none; }
.shop-filter + .shop-filter { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--ie-line); }
.shop-filter h3 { margin: 0 0 10px; color: var(--ie-navy); font-size: 12px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }
.shop-tree-item {
  display: flex; align-items: center; gap: 9px; width: 100%; padding: 7px 8px; border: 0; border-radius: 8px; background: none;
  color: #3c4b5b; font-size: 13.5px; text-align: left; cursor: pointer; font-family: inherit;
}
.shop-tree-item i { width: 16px; color: var(--ie-muted); font-size: 12px; }
.shop-tree-item span, .shop-tree-subs span { margin-left: auto; color: var(--ie-muted); font-size: 11.5px; }
.shop-tree-item:hover { background: #f4f6f8; }
.shop-tree-item.active { background: var(--ie-red-soft); color: var(--ie-red); font-weight: 700; }
.shop-tree-item.active i { color: var(--ie-red); }
.shop-tree-subs { display: flex; flex-direction: column; margin: 2px 0 6px 18px; padding-left: 10px; border-left: 2px solid var(--ie-line); }
.shop-tree-subs button { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border: 0; border-radius: 6px; background: none; color: #5d6771; font-size: 13px; text-align: left; cursor: pointer; font-family: inherit; }
.shop-tree-subs button:hover { color: var(--ie-navy); background: #f4f6f8; }
.shop-tree-subs button.active { color: var(--ie-red); font-weight: 700; }
.shop-price { display: flex; align-items: center; gap: 6px; }
.shop-price .ie-input { min-width: 0; padding: 8px 10px; font-size: 13px; }
.shop-price span { color: var(--ie-muted); }
.shop-check + .shop-check { margin-top: 8px; }
.shop-check { display: flex; align-items: center; gap: 8px; color: #3c4b5b; font-size: 13.5px; cursor: pointer; }
.shop-check input { width: 16px; height: 16px; accent-color: var(--ie-red); }
.shop-reset { width: 100%; justify-content: center; margin-top: 16px; }
.shop-filters-scrim { display: none; }

.shop-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; padding: 10px 14px; border: 1px solid var(--ie-line); border-radius: 12px; background: #fff; }
.shop-toolbar p { margin: 0; color: var(--ie-muted); font-size: 13px; }
.shop-toolbar strong { color: var(--ie-navy); }
.shop-filters-toggle { display: none; }
.shop-sort { display: flex; align-items: center; gap: 8px; margin-left: auto; color: var(--ie-muted); font-size: 13px; }
.shop-sort .ie-select { width: auto; min-width: 160px; padding-top: 7px; padding-bottom: 7px; }

.shop-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 210px), 1fr)); gap: 16px; }
.shop-grid-4 { grid-template-columns: repeat(4, 1fr); }
.card { display: flex; flex-direction: column; overflow: hidden; border: 1px solid var(--ie-line); border-radius: 12px; background: #fff; transition: box-shadow 0.2s ease, border-color 0.2s ease; }
.card:hover { border-color: #cfd5dc; box-shadow: 0 14px 32px #18283b17; }
.card-media { position: relative; display: grid; place-items: center; aspect-ratio: 1; overflow: hidden; border-bottom: 1px solid var(--ie-line); background: #f6f7f9; color: #b4bcc4; font-size: 40px; }
.card-media img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.35s ease; }
.card:hover .card-media img { transform: scale(1.04); }
.card-badge { position: absolute; top: 10px; left: 10px; padding: 4px 9px; border-radius: 6px; background: var(--ie-red); color: #fff; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; }
.card-photos { position: absolute; right: 10px; bottom: 10px; padding: 3px 8px; border-radius: 999px; background: #000000a0; color: #fff; font-size: 11px; font-weight: 700; }
.card-out { position: absolute; inset: auto 0 0; padding: 7px; background: #39495be6; color: #fff; font-size: 12px; font-weight: 700; text-align: center; }
.card.is-out .card-media img { filter: grayscale(0.7); opacity: 0.75; }
.card-body { display: flex; flex: 1; flex-direction: column; gap: 5px; padding: 12px 14px 14px; }
.card-tag { color: var(--ie-muted); font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }
.card-title { color: var(--ie-ink); font-size: 14.5px; font-weight: 600; line-height: 1.35; text-decoration: none; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.7em; }
.card-title:hover { color: var(--ie-red); text-decoration: underline; }
.card-price { margin-top: 2px; color: var(--ie-navy); font-size: 19px; font-weight: 800; }
.card-price small { color: var(--ie-muted); font-size: 12px; font-weight: 600; }
.card-offers { position: absolute; top: 10px; right: 10px; display: flex; gap: 4px; }
.card-offers em { padding: 3px 8px; border-radius: 6px; background: #ffffffeb; color: var(--ie-navy); font-size: 10.5px; font-weight: 800; font-style: normal; text-transform: uppercase; letter-spacing: 0.03em; box-shadow: 0 1px 4px #0002; }
.card-offers em.rent { background: var(--ie-navy); color: #fff; }
.card-rent { color: #4b5a6a; font-size: 12.5px; font-weight: 700; }
.card-rent-off { color: var(--ie-muted); font-weight: 600; }
.shop-mode { display: inline-flex; gap: 2px; padding: 3px; border-radius: 10px; background: #eef0f2; }
.shop-mode button { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border: 0; border-radius: 8px; background: none; color: #5d6771; font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit; }
.shop-mode button.active { background: #fff; color: var(--ie-navy); box-shadow: 0 2px 6px #0000001a; }
.shop-mode button.active i { color: var(--ie-red); }
.card-rent small { color: var(--ie-muted); font-weight: 600; }
.card-stock { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 8px; font-size: 12px; font-weight: 600; }
.card-stock i { font-size: 7px; }
.card-stock.ok { color: var(--ie-success); }
.card-stock.low { color: var(--ie-warning); }
.card-stock.out { color: var(--ie-muted); }
.card-add {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; margin-top: auto; width: 100%; padding: 10px; border: 1px solid var(--ie-navy);
  border-radius: 8px; background: #fff; color: var(--ie-navy); font-size: 13px; font-weight: 700; cursor: pointer; font-family: inherit; transition: all 0.15s ease;
}
.card-add:hover:not(:disabled) { background: var(--ie-navy); color: #fff; }
.card-add.added { background: var(--ie-success); border-color: var(--ie-success); color: #fff; }
.card-add:disabled:not(.added) { border-color: var(--ie-line); color: var(--ie-muted); cursor: default; }
.card-incart { color: var(--ie-muted); font-size: 11.5px; text-align: center; }

@media (max-width: 1080px) {
  .shop-depts { grid-template-columns: repeat(2, 1fr); }
  .shop-trust { grid-template-columns: repeat(2, 1fr); }
  .shop-trust li:nth-child(3) { border-left: 0; }
  .shop-trust li:nth-child(n + 3) { border-top: 1px solid var(--ie-line); }
}
@media (max-width: 900px) {
  .shop-hero { grid-template-columns: 1fr; }
  .shop-hero-main { min-height: 0; padding: 26px 22px; }
  .shop-hero-side { grid-template-columns: 1fr 1fr; }
  .shop-grid-4 { grid-template-columns: repeat(2, 1fr); }
  .shop-catalog { grid-template-columns: 1fr; }
  .shop-filters {
    position: fixed; top: 0; bottom: 0; left: 0; z-index: 920; width: min(320px, 88vw); overflow-y: auto; border-radius: 0;
    transform: translateX(-100%); transition: transform 0.25s ease;
  }
  .shop-filters.open { transform: translateX(0); }
  .shop-filters-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; color: var(--ie-navy); font-size: 16px; }
  .shop-filters-close { width: 34px; height: 34px; border: 0; border-radius: 50%; background: #f2f4f6; color: var(--ie-navy); cursor: pointer; }
  .shop-filters-scrim { display: block; position: fixed; inset: 0; z-index: 919; border: 0; background: rgba(20, 30, 40, 0.45); }
  .shop-filters-toggle { display: inline-flex; }
}
@media (max-width: 560px) {
  .shop-hero-side { grid-template-columns: 1fr; }
  .shop-promo { padding: 16px; }
  .shop-trust { grid-template-columns: 1fr; }
  .shop-trust li { border-left: 0 !important; }
  .shop-trust li + li { border-top: 1px solid var(--ie-line); }
  /* Rayons en tuiles compactes sur mobile : 2 colonnes, sans sous-catégories. */
  .shop-depts { grid-template-columns: 1fr 1fr; gap: 10px; }
  .shop-dept { gap: 0; padding: 14px 12px; }
  .shop-dept-head { flex-direction: column; align-items: flex-start; gap: 8px; }
  .shop-dept-icon { width: 40px; height: 40px; flex-basis: 40px; font-size: 17px; }
  .shop-dept-head strong { font-size: 14px; }
  .shop-dept-subs, .shop-dept-more { display: none; }
  .shop-toolbar { flex-wrap: wrap; }
  .shop-mode { order: -1; display: flex; width: 100%; }
  .shop-mode button { flex: 1; justify-content: center; }
  .shop-sort span { display: none; }
  .shop-sort .ie-select { min-width: 0; }
  .shop-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
  .card-body { padding: 10px 11px 12px; }
  .card-title { font-size: 13px; }
  .card-price { font-size: 15.5px; }
  .card-add { font-size: 12px; padding: 8px 4px; }
}
@media (prefers-reduced-motion: reduce) {
  .card, .card-media img, .shop-promo > i, .shop-filters { transition: none; }
}
</style>
