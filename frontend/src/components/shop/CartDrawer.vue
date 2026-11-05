<script setup>
import { useRouter } from "vue-router";
import { formatDay, formatMoney } from "../../data/saleCategories";
import { useCartStore } from "../../stores/cart";

const cart = useCartStore();
const router = useRouter();

function goToCheckout() {
  cart.closeDrawer();
  router.push({ name: "sale-checkout" });
}
</script>

<template>
  <Teleport to="body">
    <Transition name="ie-cart-fade">
      <div v-if="cart.drawerOpen" class="ie-cart-scrim" @click="cart.closeDrawer()"></div>
    </Transition>
    <Transition name="ie-cart-slide">
      <aside v-if="cart.drawerOpen" class="ie-cart-drawer" role="dialog" aria-modal="true" aria-label="Mon panier">
        <header class="ie-cart-head">
          <h2><i class="fa-solid fa-cart-shopping"></i> Mon panier <span v-if="cart.count">({{ cart.count }})</span></h2>
          <button type="button" class="ie-cart-close" aria-label="Fermer le panier" @click="cart.closeDrawer()"><i class="fa-solid fa-xmark"></i></button>
        </header>

        <div v-if="!cart.items.length" class="ie-cart-empty">
          <span><i class="fa-solid fa-basket-shopping"></i></span>
          <strong>Votre panier est vide</strong>
          <p>Parcourez la boutique et ajoutez les équipements dont vous avez besoin.</p>
          <button type="button" class="ie-btn ie-btn-primary" @click="cart.closeDrawer()">Continuer mes achats</button>
        </div>

        <template v-else>
          <div class="ie-cart-mode" role="radiogroup" aria-label="Acheter ou louer">
            <button type="button" role="radio" :aria-checked="!cart.isRental" :class="{ active: !cart.isRental }" @click="cart.setMode('purchase')">
              <i class="fa-solid fa-bag-shopping"></i> Acheter
            </button>
            <button type="button" role="radio" :aria-checked="cart.isRental" :class="{ active: cart.isRental }" @click="cart.setMode('rental')">
              <i class="fa-solid fa-calendar-days"></i> Louer
            </button>
          </div>
          <p v-if="cart.isRental" class="ie-cart-period">
            <i class="fa-regular fa-calendar"></i>
            <template v-if="cart.days">Du {{ formatDay(cart.rentalStart) }} au {{ formatDay(cart.rentalEnd) }} · {{ cart.days }} jour{{ cart.days > 1 ? "s" : "" }}</template>
            <template v-else>Dates de location à choisir à l'étape suivante.</template>
          </p>
          <p v-if="cart.incompatibleItems.length" class="ie-cart-warning">
            <i class="fa-solid fa-triangle-exclamation"></i>
            {{ cart.incompatibleItems.length }} produit{{ cart.incompatibleItems.length > 1 ? "s ne sont" : " n'est" }} pas proposé{{ cart.incompatibleItems.length > 1 ? "s" : "" }}
            {{ cart.isRental ? "à la location" : "à l'achat" }} : retirez-le{{ cart.incompatibleItems.length > 1 ? "s" : "" }} ou changez de mode.
          </p>
          <ul class="ie-cart-lines">
            <li v-for="item in cart.items" :key="item.id" :class="{ 'is-incompatible': cart.isRental ? !item.forRent : !item.forSale }">
              <router-link :to="{ name: 'sale-product', params: { id: item.id } }" class="ie-cart-thumb" @click="cart.closeDrawer()">
                <img v-if="item.photo" v-img="item.photo" :alt="item.title" />
                <i v-else class="fa-solid fa-box-open"></i>
              </router-link>
              <div class="ie-cart-info">
                <router-link :to="{ name: 'sale-product', params: { id: item.id } }" class="ie-cart-title" @click="cart.closeDrawer()">{{ item.title }}</router-link>
                <span v-if="cart.isRental ? !item.forRent : !item.forSale" class="ie-cart-unit ie-cart-unavailable">
                  Non proposé {{ cart.isRental ? "à la location" : "à l'achat" }}
                </span>
                <span v-else class="ie-cart-unit">{{ formatMoney(cart.lineUnit(item), item.currency) }} {{ cart.isRental ? "/ pièce / jour" : "/ pièce" }}</span>
                <div class="ie-cart-row">
                  <div class="ie-qty">
                    <button type="button" aria-label="Retirer une pièce" :disabled="item.quantity <= 1" @click="cart.setQuantity(item.id, item.quantity - 1)"><i class="fa-solid fa-minus"></i></button>
                    <input :value="item.quantity" type="number" min="1" :max="item.stock ?? undefined" aria-label="Quantité" @change="cart.setQuantity(item.id, Number($event.target.value))" />
                    <button type="button" aria-label="Ajouter une pièce" :disabled="item.stock !== null && item.quantity >= item.stock" @click="cart.setQuantity(item.id, item.quantity + 1)"><i class="fa-solid fa-plus"></i></button>
                  </div>
                  <strong>{{ formatMoney(cart.lineTotal(item), item.currency) }}</strong>
                </div>
              </div>
              <button type="button" class="ie-cart-remove" :aria-label="`Retirer ${item.title}`" @click="cart.remove(item.id)"><i class="fa-regular fa-trash-can"></i></button>
            </li>
          </ul>

          <footer class="ie-cart-foot">
            <div class="ie-cart-total">
              <span>
                {{ cart.isRental && !cart.days ? "Total par jour" : "Total" }}
                ({{ cart.count }} pièce{{ cart.count > 1 ? "s" : "" }}{{ cart.isRental && cart.days ? ` · ${cart.days} j` : "" }})
              </span>
              <strong>{{ formatMoney(cart.total, cart.currency) }}</strong>
            </div>
            <p>Paiement à la livraison ou ultérieurement — aucune carte demandée.</p>
            <button type="button" class="ie-btn ie-btn-primary ie-cart-cta" :disabled="cart.incompatibleItems.length > 0" @click="goToCheckout">
              {{ cart.isRental ? "Choisir les dates et commander" : "Passer la commande" }} <i class="fa-solid fa-arrow-right"></i>
            </button>
          </footer>
        </template>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ie-cart-scrim { position: fixed; inset: 0; z-index: 900; background: rgba(20, 30, 40, 0.45); }
.ie-cart-drawer {
  position: fixed; top: 0; right: 0; bottom: 0; z-index: 901; width: min(420px, 100vw);
  display: flex; flex-direction: column; background: #fff; box-shadow: -12px 0 40px rgba(20, 30, 40, 0.18);
}
.ie-cart-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; border-bottom: 1px solid var(--ie-line); }
.ie-cart-head h2 { margin: 0; font-size: 17px; color: var(--ie-navy); display: flex; align-items: center; gap: 10px; }
.ie-cart-head h2 i { color: var(--ie-red); }
.ie-cart-head h2 span { color: var(--ie-muted); font-weight: 600; }
.ie-cart-close { width: 36px; height: 36px; border: 0; border-radius: 50%; background: #f2f4f6; color: var(--ie-navy); cursor: pointer; }
.ie-cart-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 30px; text-align: center; }
.ie-cart-empty > span { display: grid; place-items: center; width: 74px; height: 74px; border-radius: 50%; background: var(--ie-red-soft); color: var(--ie-red); font-size: 28px; }
.ie-cart-empty strong { color: var(--ie-navy); font-size: 16px; }
.ie-cart-empty p { margin: 0 0 6px; color: var(--ie-muted); font-size: 13px; }
.ie-cart-mode { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin: 14px 20px 0; padding: 4px; border-radius: 12px; background: #eef0f2; }
.ie-cart-mode button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 9px; border: 0; border-radius: 9px; background: none; color: #5d6771; font-size: 13.5px; font-weight: 700; cursor: pointer; font-family: inherit; }
.ie-cart-mode button.active { background: #fff; color: var(--ie-navy); box-shadow: 0 2px 6px #0000001a; }
.ie-cart-mode button.active i { color: var(--ie-red); }
.ie-cart-period { display: flex; align-items: center; gap: 8px; margin: 10px 20px 0; color: var(--ie-navy); font-size: 12.5px; font-weight: 600; }
.ie-cart-warning { margin: 10px 20px 0; padding: 9px 12px; border-radius: 10px; background: var(--ie-warning-soft); color: #7a4f00; font-size: 12.5px; line-height: 1.4; }
.ie-cart-lines li.is-incompatible { opacity: 0.6; }
.ie-cart-unavailable { color: var(--ie-red) !important; font-weight: 600; }
.ie-cart-lines { flex: 1; overflow-y: auto; list-style: none; margin: 0; padding: 8px 20px; }
.ie-cart-lines li { position: relative; display: flex; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--ie-line); }
.ie-cart-thumb { display: grid; place-items: center; width: 76px; height: 76px; flex: 0 0 76px; overflow: hidden; border-radius: 10px; background: #f2f4f6; color: #9aa3ac; }
.ie-cart-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-cart-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; padding-right: 26px; }
.ie-cart-title { color: var(--ie-navy); font-weight: 700; font-size: 14px; text-decoration: none; line-height: 1.3; }
.ie-cart-unit { color: var(--ie-muted); font-size: 12px; }
.ie-cart-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 4px; }
.ie-cart-row strong { color: var(--ie-navy); font-size: 14px; white-space: nowrap; }
.ie-qty { display: inline-flex; align-items: center; border: 1px solid var(--ie-line); border-radius: 999px; overflow: hidden; }
.ie-qty button { width: 30px; height: 30px; border: 0; background: #f7f8fa; color: var(--ie-navy); cursor: pointer; font-size: 11px; }
.ie-qty button:disabled { opacity: 0.4; cursor: default; }
.ie-qty input { width: 42px; height: 30px; border: 0; text-align: center; font-weight: 700; color: var(--ie-navy); font-family: inherit; -moz-appearance: textfield; }
.ie-qty input::-webkit-inner-spin-button, .ie-qty input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.ie-cart-remove { position: absolute; top: 12px; right: 0; width: 28px; height: 28px; border: 0; border-radius: 50%; background: none; color: var(--ie-muted); cursor: pointer; }
.ie-cart-remove:hover { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-cart-foot { padding: 16px 20px max(16px, env(safe-area-inset-bottom)); border-top: 1px solid var(--ie-line); background: #fafbfc; }
.ie-cart-total { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.ie-cart-total span { color: var(--ie-muted); font-size: 13px; }
.ie-cart-total strong { color: var(--ie-navy); font-size: 22px; }
.ie-cart-foot p { margin: 6px 0 14px; color: var(--ie-muted); font-size: 12px; }
.ie-cart-cta { width: 100%; justify-content: center; padding: 13px; font-size: 15px; }
.ie-cart-fade-enter-active, .ie-cart-fade-leave-active { transition: opacity 0.2s ease; }
.ie-cart-fade-enter-from, .ie-cart-fade-leave-to { opacity: 0; }
.ie-cart-slide-enter-active, .ie-cart-slide-leave-active { transition: transform 0.25s ease; }
.ie-cart-slide-enter-from, .ie-cart-slide-leave-to { transform: translateX(100%); }
@media (prefers-reduced-motion: reduce) {
  .ie-cart-fade-enter-active, .ie-cart-fade-leave-active, .ie-cart-slide-enter-active, .ie-cart-slide-leave-active { transition: none; }
}
</style>
