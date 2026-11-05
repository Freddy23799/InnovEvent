<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import ShopBar from "../../components/shop/ShopBar.vue";
import { SALE_CATEGORIES, availableOf, formatMoney, offerModes, productImages, stockLabel, subcategoryLabel } from "../../data/saleCategories";
import api from "../../services/api";
import { useCartStore } from "../../stores/cart";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const route = useRoute();
const router = useRouter();
const cart = useCartStore();
const lightbox = useLightboxStore();
const toast = useToastStore();

const product = ref(null);
const related = ref([]);
const loading = ref(true);
const notFound = ref(false);
const activeImage = ref(0);
const quantity = ref(1);
const added = ref(false);
// Achat ou location : proposé uniquement quand le produit offre les deux.
const offerMode = ref("purchase");
const modes = computed(() => (product.value ? offerModes(product.value) : { sale: true, rent: false }));
const isRentMode = computed(() => offerMode.value === "rental");

const images = computed(() => (product.value ? productImages(product.value) : []));
const stock = computed(() => (product.value ? stockLabel(product.value) : null));
const inCart = computed(() => cart.items.find((i) => i.id === product.value?.id)?.quantity || 0);
// Pièces encore ajoutables, compte tenu de ce qui est déjà dans le panier.
const maxQuantity = computed(() => {
  if (!product.value) return 1;
  const stock = availableOf(product.value);
  if (stock === null) return 10000;
  return Math.max(stock - inCart.value, 0);
});
const unitPrice = computed(() => (product.value ? Number(isRentMode.value ? product.value.rental_price : product.value.price) : 0));
const subtotal = computed(() => unitPrice.value * quantity.value);
const categoryIcon = computed(() => SALE_CATEGORIES.find((c) => c.value === product.value?.category)?.icon || "fa-solid fa-box-open");
const sellerName = computed(() => product.value?.provider_name || "InnovEvent");
const subLabel = computed(() => (product.value ? subcategoryLabel(product.value.category, product.value.subcategory) : ""));
const crumbs = computed(() => {
  if (!product.value) return [];
  const list = [];
  if (product.value.category) list.push({ label: product.value.category_display, to: { name: "sale-shop", query: { category: product.value.category } } });
  if (subLabel.value) list.push({ label: subLabel.value, to: { name: "sale-shop", query: { category: product.value.category, sub: product.value.subcategory } } });
  list.push({ label: product.value.title });
  return list;
});

async function loadProduct() {
  loading.value = true;
  notFound.value = false;
  activeImage.value = 0;
  quantity.value = 1;
  try {
    const { data } = await api.get(`/marketplace/listings/${route.params.id}/`);
    if (data.marketplace_type !== "sale") {
      notFound.value = true;
      return;
    }
    product.value = data;
    // Le mode choisi dans la boutique (Acheter / Louer) est conservé ici.
    const modesOffered = offerModes(data);
    offerMode.value = !modesOffered.sale || (cart.isRental && modesOffered.rent) ? "rental" : "purchase";
    loadRelated();
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
    else throw e;
  } finally {
    loading.value = false;
  }
}

async function loadRelated() {
  try {
    const { data } = await api.get("/marketplace/listings/", { params: { marketplace_type: "sale", is_active: true } });
    const all = (data.results || data).filter((p) => p.id !== product.value.id);
    const rank = (p) => (p.subcategory && p.subcategory === product.value.subcategory ? 0 : p.category === product.value.category ? 1 : 2);
    related.value = [...all].sort((a, b) => rank(a) - rank(b)).slice(0, 4);
  } catch (e) {
    related.value = [];
  }
}

function setQuantity(value) {
  quantity.value = Math.max(1, Math.min(Math.floor(Number(value)) || 1, Math.max(maxQuantity.value, 1)));
}

function addToCart() {
  // Le mode choisi ici devient celui du panier (il reste modifiable avant la commande).
  const error = cart.add(product.value, quantity.value, offerMode.value);
  if (error) {
    toast.error(error);
    return false;
  }
  added.value = true;
  setTimeout(() => { added.value = false; }, 1800);
  quantity.value = 1;
  return true;
}

function buyNow() {
  if (addToCart()) router.push({ name: "sale-checkout" });
}

function openGallery(index) {
  lightbox.openGallery(images.value.map((url) => ({ url, caption: product.value.title })), index);
}

watch(() => route.params.id, (id) => { if (id) loadProduct(); }, { immediate: true });
</script>

<template>
  <div class="ie-pdp">
    <ShopBar :crumbs="crumbs" />

    <div v-if="loading" class="ie-pdp-main" aria-busy="true">
      <div class="ie-skeleton" style="aspect-ratio: 1; border-radius: 18px;"></div>
      <div class="ie-skeleton" style="height: 420px; border-radius: 18px;"></div>
    </div>
    <EmptyState v-else-if="notFound" icon="fa-solid fa-box-open" text="Ce produit n'est plus disponible.">
      <router-link :to="{ name: 'sale-shop' }" class="ie-btn ie-btn-primary">Retour à la boutique</router-link>
    </EmptyState>

    <template v-else-if="product">
      <section class="ie-pdp-main">
        <div class="ie-pdp-gallery">
          <button type="button" class="ie-pdp-stage" :disabled="!images.length" @click="openGallery(activeImage)">
            <img v-if="images.length" :key="images[activeImage]" v-img.eager="images[activeImage]" :alt="product.title" />
            <i v-else :class="categoryIcon"></i>
            <span v-if="images.length" class="ie-pdp-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i> Agrandir</span>
            <span v-if="images.length > 1" class="ie-pdp-counter">{{ activeImage + 1 }} / {{ images.length }}</span>
          </button>
          <div v-if="images.length > 1" class="ie-pdp-thumbs">
            <button
              v-for="(url, index) in images" :key="url" type="button" class="ie-pdp-thumb"
              :class="{ active: index === activeImage }" :aria-label="`Photo ${index + 1}`"
              @click="activeImage = index" @mouseenter="activeImage = index"
            >
              <img v-img="url" :alt="`${product.title} — photo ${index + 1}`" />
            </button>
          </div>
        </div>

        <div class="ie-pdp-buy">
          <span class="ie-pdp-cat"><i :class="categoryIcon"></i> {{ subLabel || product.category_display || "Équipement" }}</span>
          <h1>{{ product.title }}</h1>
          <p class="ie-pdp-seller">Vendu par <strong>{{ sellerName }}</strong> <i class="fa-solid fa-circle-check"></i></p>

          <div v-if="modes.sale && modes.rent" class="ie-pdp-modes" role="radiogroup" aria-label="Acheter ou louer">
            <button type="button" role="radio" :aria-checked="!isRentMode" :class="{ active: !isRentMode }" @click="offerMode = 'purchase'">
              <span>Acheter</span>
              <strong>{{ formatMoney(product.price, product.currency) }}</strong>
              <small>par pièce</small>
            </button>
            <button type="button" role="radio" :aria-checked="isRentMode" :class="{ active: isRentMode }" @click="offerMode = 'rental'">
              <span>Louer</span>
              <strong>{{ formatMoney(product.rental_price, product.currency) }}</strong>
              <small>par pièce et par jour</small>
            </button>
          </div>
          <div v-else class="ie-pdp-price">
            {{ formatMoney(unitPrice, product.currency) }} <small>{{ isRentMode ? "/ pièce / jour" : "/ pièce" }}</small>
            <span v-if="isRentMode" class="ie-pdp-rent-badge"><i class="fa-solid fa-calendar-days"></i> À la location</span>
          </div>
          <span class="ie-stock" :class="stock.tone"><i class="fa-solid fa-circle"></i> {{ stock.text }}</span>

          <div class="ie-pdp-order">
            <label class="ie-label" for="pdp-qty">Nombre de pièces</label>
            <div class="ie-pdp-qty-row">
              <div class="ie-qty">
                <button type="button" aria-label="Retirer une pièce" :disabled="quantity <= 1" @click="setQuantity(quantity - 1)"><i class="fa-solid fa-minus"></i></button>
                <input id="pdp-qty" :value="quantity" type="number" min="1" :max="maxQuantity" @change="setQuantity($event.target.value)" />
                <button type="button" aria-label="Ajouter une pièce" :disabled="quantity >= maxQuantity" @click="setQuantity(quantity + 1)"><i class="fa-solid fa-plus"></i></button>
              </div>
              <div class="ie-pdp-subtotal">
                <span>{{ isRentMode ? "Sous-total par jour" : "Sous-total" }}</span>
                <strong>{{ formatMoney(subtotal, product.currency) }}</strong>
              </div>
            </div>

            <button type="button" class="ie-btn ie-pdp-add" :class="added ? 'is-added' : 'ie-btn-primary'" :disabled="maxQuantity < 1" @click="addToCart">
              <template v-if="added"><i class="fa-solid fa-check"></i> Ajouté au panier</template>
              <template v-else-if="availableOf(product) === 0">Rupture de stock</template>
              <template v-else-if="maxQuantity < 1">Tout le stock est dans votre panier</template>
              <template v-else><i class="fa-solid fa-cart-plus"></i> {{ isRentMode ? "Ajouter à ma location" : "Ajouter au panier" }}</template>
            </button>
            <button type="button" class="ie-btn ie-btn-secondary ie-pdp-buynow" :disabled="maxQuantity < 1" @click="buyNow">
              <i class="fa-solid" :class="isRentMode ? 'fa-calendar-check' : 'fa-bolt'"></i> {{ isRentMode ? "Louer maintenant" : "Commander maintenant" }}
            </button>
            <p v-if="isRentMode" class="ie-pdp-rent-hint">Vous choisirez les dates de location à l'étape suivante. La disponibilité est vérifiée pour votre période.</p>
            <button v-if="inCart" type="button" class="ie-pdp-incart" @click="cart.openDrawer()">
              <i class="fa-solid fa-cart-shopping"></i> {{ inCart }} pièce{{ inCart > 1 ? "s" : "" }} déjà dans votre panier — voir le panier
            </button>
          </div>

          <ul class="ie-pdp-assurances">
            <li><i class="fa-solid fa-file-invoice"></i> Facture générée automatiquement</li>
            <li><i class="fa-solid fa-hand-holding-dollar"></i> Paiement à la livraison ou ultérieurement</li>
            <li><i class="fa-solid fa-shield-halved"></i> Produit vérifié par InnovEvent</li>
          </ul>
        </div>
      </section>

      <section class="ie-pdp-details">
        <div class="ie-card ie-card-body ie-pdp-desc">
          <h2>Description du produit</h2>
          <p v-if="product.description">{{ product.description }}</p>
          <p v-else class="ie-pdp-muted">Aucune description détaillée pour ce produit.</p>
        </div>
        <div class="ie-card ie-card-body">
          <h2>Caractéristiques</h2>
          <dl class="ie-pdp-specs">
            <div><dt>Rayon</dt><dd>{{ product.category_display || "—" }}</dd></div>
            <div v-if="subLabel"><dt>Catégorie</dt><dd>{{ subLabel }}</dd></div>
            <div v-if="modes.sale"><dt>Prix d'achat</dt><dd>{{ formatMoney(product.price, product.currency) }}</dd></div>
            <div v-if="modes.rent"><dt>Location</dt><dd>{{ formatMoney(product.rental_price, product.currency) }} / jour</dd></div>
            <div><dt>Disponibilité</dt><dd>{{ stock.text }}</dd></div>
            <div><dt>Vendeur</dt><dd>{{ sellerName }}</dd></div>
            <div><dt>Référence</dt><dd>IE-{{ String(product.id).padStart(5, "0") }}</dd></div>
          </dl>
        </div>
      </section>

      <section v-if="related.length" class="ie-pdp-related">
        <h2>Vous aimerez aussi</h2>
        <div class="ie-pdp-related-grid">
          <router-link v-for="item in related" :key="item.id" :to="{ name: 'sale-product', params: { id: item.id } }" class="ie-pdp-related-card">
            <span class="ie-pdp-related-media">
              <img v-if="productImages(item)[0]" v-img="productImages(item)[0]" :alt="item.title" />
              <i v-else class="fa-solid fa-box-open"></i>
            </span>
            <strong>{{ item.title }}</strong>
            <span>{{ formatMoney(item.price, item.currency) }}</span>
          </router-link>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.ie-pdp { max-width: 1180px; margin: 0 auto; min-width: 0; }
.ie-pdp-main { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 28px; align-items: start; }
.ie-pdp-gallery { display: flex; flex-direction: column; gap: 12px; position: sticky; top: 0; }
.ie-pdp-stage {
  position: relative; display: grid; place-items: center; aspect-ratio: 1; padding: 0; overflow: hidden; border: 1px solid var(--ie-line);
  border-radius: 18px; background: #f4f6f8; color: #b4bcc4; font-size: 64px; cursor: zoom-in;
}
.ie-pdp-stage:disabled { cursor: default; }
.ie-pdp-stage img { width: 100%; height: 100%; object-fit: cover; }
.ie-pdp-zoom, .ie-pdp-counter { position: absolute; bottom: 12px; padding: 5px 10px; border-radius: 999px; background: #000000a0; color: #fff; font-size: 12px; font-weight: 700; }
.ie-pdp-zoom { left: 12px; opacity: 0; transition: opacity 0.2s ease; }
.ie-pdp-stage:hover .ie-pdp-zoom { opacity: 1; }
.ie-pdp-counter { right: 12px; }
.ie-pdp-thumbs { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px; }
.ie-pdp-thumb { flex: 0 0 76px; height: 76px; padding: 0; overflow: hidden; border: 2px solid transparent; border-radius: 12px; background: #f4f6f8; cursor: pointer; opacity: 0.7; transition: all 0.15s ease; }
.ie-pdp-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-pdp-thumb.active, .ie-pdp-thumb:hover { border-color: var(--ie-red); opacity: 1; }

.ie-pdp-buy { display: flex; flex-direction: column; gap: 10px; padding: 26px; border: 1px solid var(--ie-line); border-radius: 18px; background: #fff; box-shadow: var(--ie-shadow-sm); }
.ie-pdp-cat { display: inline-flex; align-items: center; gap: 7px; align-self: flex-start; padding: 5px 11px; border-radius: 999px; background: var(--ie-red-soft); color: var(--ie-red); font-size: 12px; font-weight: 700; }
.ie-pdp-buy h1 { margin: 2px 0 0; color: var(--ie-ink); font-size: clamp(22px, 2.6vw, 30px); line-height: 1.2; }
.ie-pdp-seller { margin: 0; color: var(--ie-muted); font-size: 13px; }
.ie-pdp-seller strong { color: var(--ie-navy); }
.ie-pdp-seller i { color: var(--ie-success); font-size: 12px; }
.ie-pdp-price { margin-top: 8px; padding-top: 14px; border-top: 1px solid var(--ie-line); color: var(--ie-navy); font-size: 32px; font-weight: 800; }
.ie-pdp-price small { color: var(--ie-muted); font-size: 14px; font-weight: 600; }
.ie-pdp-modes { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; padding-top: 14px; border-top: 1px solid var(--ie-line); }
.ie-pdp-modes button { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 12px 14px; border: 2px solid var(--ie-line); border-radius: 12px; background: #fff; text-align: left; cursor: pointer; font-family: inherit; }
.ie-pdp-modes button span { color: var(--ie-muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
.ie-pdp-modes button strong { color: var(--ie-navy); font-size: 21px; }
.ie-pdp-modes button small { color: var(--ie-muted); font-size: 11.5px; }
.ie-pdp-modes button.active { border-color: var(--ie-red); background: #fff8f8; }
.ie-pdp-modes button.active span { color: var(--ie-red); }
.ie-pdp-rent-badge { display: inline-flex; align-items: center; gap: 6px; margin-left: 8px; padding: 4px 10px; border-radius: 999px; background: var(--ie-navy); color: #fff; font-size: 11.5px; font-weight: 700; vertical-align: middle; }
.ie-pdp-rent-hint { margin: 0; color: var(--ie-muted); font-size: 12px; text-align: center; }
.ie-stock { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; }
.ie-stock i { font-size: 8px; }
.ie-stock.ok { color: var(--ie-success); }
.ie-stock.low { color: var(--ie-warning); }
.ie-stock.out { color: var(--ie-muted); }
.ie-pdp-order { display: flex; flex-direction: column; gap: 10px; margin-top: 8px; padding: 16px; border-radius: 14px; background: #f7f8fa; }
.ie-pdp-order .ie-label { margin: 0; }
.ie-pdp-qty-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ie-qty { display: inline-flex; align-items: center; border: 1px solid var(--ie-line); border-radius: 999px; overflow: hidden; background: #fff; }
.ie-qty button { width: 42px; height: 42px; border: 0; background: #fff; color: var(--ie-navy); cursor: pointer; }
.ie-qty button:hover:not(:disabled) { background: #f0f3f7; }
.ie-qty button:disabled { opacity: 0.4; cursor: default; }
.ie-qty input { width: 60px; height: 42px; border: 0; border-left: 1px solid var(--ie-line); border-right: 1px solid var(--ie-line); text-align: center; font-size: 16px; font-weight: 800; color: var(--ie-navy); font-family: inherit; -moz-appearance: textfield; }
.ie-qty input::-webkit-inner-spin-button, .ie-qty input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.ie-pdp-subtotal { text-align: right; }
.ie-pdp-subtotal span { display: block; color: var(--ie-muted); font-size: 12px; }
.ie-pdp-subtotal strong { color: var(--ie-navy); font-size: 20px; }
.ie-pdp-add, .ie-pdp-buynow { width: 100%; justify-content: center; padding: 13px; font-size: 15px; }
.ie-pdp-add.is-added { background: var(--ie-success); border-color: var(--ie-success); color: #fff; }
.ie-pdp-incart { border: 0; background: none; color: var(--ie-navy); font-size: 12.5px; font-weight: 600; text-decoration: underline; cursor: pointer; font-family: inherit; }
.ie-pdp-assurances { display: grid; gap: 8px; margin: 6px 0 0; padding: 0; list-style: none; font-size: 13px; color: #4b5a6a; }
.ie-pdp-assurances i { width: 20px; color: var(--ie-red); }

.ie-pdp-details { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr); gap: 18px; margin-top: 26px; }
.ie-pdp-details h2, .ie-pdp-related h2 { margin: 0 0 12px; color: var(--ie-navy); font-size: 17px; }
.ie-pdp-desc p { margin: 0; color: #3c4b5b; font-size: 14.5px; line-height: 1.7; white-space: pre-line; }
.ie-pdp-muted { color: var(--ie-muted) !important; }
.ie-pdp-specs { margin: 0; }
.ie-pdp-specs div { display: flex; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--ie-line); font-size: 13.5px; }
.ie-pdp-specs div:last-child { border-bottom: 0; }
.ie-pdp-specs dt { color: var(--ie-muted); }
.ie-pdp-specs dd { margin: 0; color: var(--ie-navy); font-weight: 700; text-align: right; }

.ie-pdp-related { margin-top: 30px; }
.ie-pdp-related-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.ie-pdp-related-card { display: flex; flex-direction: column; gap: 6px; padding: 10px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; color: inherit; text-decoration: none; transition: box-shadow 0.2s ease; }
.ie-pdp-related-card:hover { box-shadow: 0 10px 26px #18283b14; }
.ie-pdp-related-media { display: grid; place-items: center; aspect-ratio: 1; overflow: hidden; border-radius: 10px; background: #f4f6f8; color: #b4bcc4; font-size: 28px; }
.ie-pdp-related-media img { width: 100%; height: 100%; object-fit: cover; }
.ie-pdp-related-card strong { color: var(--ie-ink); font-size: 13.5px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ie-pdp-related-card > span:last-child { color: var(--ie-navy); font-size: 14px; font-weight: 800; }

@media (max-width: 900px) {
  .ie-pdp-main, .ie-pdp-details { grid-template-columns: 1fr; }
  .ie-pdp-gallery { position: static; }
  .ie-pdp-related-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 520px) {
  .ie-pdp-buy { padding: 18px; }
  .ie-pdp-price { font-size: 26px; }
  .ie-pdp-thumb { flex-basis: 62px; height: 62px; }
}
</style>
