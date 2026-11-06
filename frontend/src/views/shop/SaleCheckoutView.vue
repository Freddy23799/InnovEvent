<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import ShopBar from "../../components/shop/ShopBar.vue";
import { citiesForCountry } from "../../data/countries";
import { formatDay, formatMoney } from "../../data/saleCategories";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useCartStore } from "../../stores/cart";

const router = useRouter();
const auth = useAuthStore();
const cart = useCartStore();

const CITY_NAMES = citiesForCountry("CM").map((c) => c.name);
const user = auth.user || {};
const form = reactive({
  delivery_name: [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username || "",
  delivery_phone: user.phone || "",
  delivery_city: CITY_NAMES.includes(user.city) ? user.city : "",
  delivery_address: "",
  notes: "",
});
const submitting = ref(false);
const errorMessage = ref("");
const cityOptions = computed(() => (form.delivery_city && !CITY_NAMES.includes(form.delivery_city) ? [form.delivery_city, ...CITY_NAMES] : CITY_NAMES));

const now = new Date();
const today = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const rentalStart = computed({ get: () => cart.rentalStart, set: (value) => cart.setRentalDates(value, cart.rentalEnd && cart.rentalEnd >= value ? cart.rentalEnd : value) });
const rentalEnd = computed({ get: () => cart.rentalEnd, set: (value) => cart.setRentalDates(cart.rentalStart, value) });
const datesMissing = computed(() => cart.isRental && !cart.days);

// Disponibilité vérifiée en direct pour le mode et la période choisis (le
// serveur revérifie de toute façon à la validation).
const availability = ref({});
const checking = ref(false);
let checkTimer = null;

function payload() {
  return {
    items: cart.items.map((item) => ({ listing: item.id, quantity: item.quantity })),
    order_type: cart.mode,
    rental_start: cart.isRental ? cart.rentalStart || null : null,
    rental_end: cart.isRental ? cart.rentalEnd || null : null,
  };
}

async function checkAvailability() {
  availability.value = {};
  if (!cart.items.length || cart.incompatibleItems.length || datesMissing.value) return;
  checking.value = true;
  try {
    const { data } = await api.post("/marketplace/sale-orders/check-availability/", payload());
    availability.value = Object.fromEntries(data.lines.map((line) => [line.listing, line]));
  } catch (e) {
    availability.value = {};
  } finally {
    checking.value = false;
  }
}

const shortages = computed(() => cart.items.filter((item) => availability.value[item.id] && !availability.value[item.id].ok));
const canSubmit = computed(() => cart.items.length && !cart.incompatibleItems.length && !datesMissing.value && !shortages.value.length);

watch(
  () => [cart.mode, cart.rentalStart, cart.rentalEnd, cart.items.map((i) => `${i.id}:${i.quantity}`).join(",")],
  () => {
    clearTimeout(checkTimer);
    checkTimer = setTimeout(checkAvailability, 350);
  },
);

async function submitOrder() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const { data } = await api.post("/marketplace/sale-orders/", { ...form, ...payload() });
    cart.clear();
    router.replace({ name: "sale-invoice", params: { id: data.id }, query: { new: "1" } });
  } catch (e) {
    const data = e?.response?.data;
    errorMessage.value = data?.detail
      || [data?.items, data?.rental_start, data?.rental_end].flat().filter(Boolean).join(" ")
      || "Impossible d'enregistrer la commande. Vérifiez les informations saisies.";
    checkAvailability();
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  cart.ensureLoaded();
  checkAvailability();
});
</script>

<template>
  <div class="co">
    <ShopBar :crumbs="[{ label: 'Commande' }]" />

    <EmptyState v-if="!cart.items.length" icon="fa-solid fa-basket-shopping" text="Votre panier est vide.">
      <router-link :to="{ name: 'sale-shop' }" class="ie-btn ie-btn-primary">Découvrir la boutique</router-link>
    </EmptyState>

    <form v-else class="co-grid" @submit.prevent="submitOrder">
      <div class="co-steps">
        <!-- 1. Achat ou location -->
        <section class="ie-card ie-card-body">
          <h2 class="co-step"><span>1</span> Achat ou location ?</h2>
          <div class="co-modes" role="radiogroup" aria-label="Type de commande">
            <button
              type="button" role="radio" :aria-checked="!cart.isRental" class="co-mode" :class="{ active: !cart.isRental, disabled: !cart.canBuyAll }"
              @click="cart.setMode('purchase')"
            >
              <i class="fa-solid fa-bag-shopping"></i>
              <strong>J'achète</strong>
              <small>Le matériel vous appartient.</small>
              <em v-if="!cart.canBuyAll">Certains produits ne sont pas vendus</em>
            </button>
            <button
              type="button" role="radio" :aria-checked="cart.isRental" class="co-mode" :class="{ active: cart.isRental, disabled: !cart.canRentAll }"
              @click="cart.setMode('rental')"
            >
              <i class="fa-solid fa-calendar-days"></i>
              <strong>Je loue</strong>
              <small>Pour la durée de votre événement, puis retour.</small>
              <em v-if="!cart.canRentAll">Certains produits ne sont pas loués</em>
            </button>
          </div>

          <div v-if="cart.isRental" class="co-dates">
            <div>
              <label class="ie-label" for="co-start">Du</label>
              <input id="co-start" v-model="rentalStart" type="date" class="ie-input" :min="today" required />
            </div>
            <div>
              <label class="ie-label" for="co-end">Au (inclus)</label>
              <input id="co-end" v-model="rentalEnd" type="date" class="ie-input" :min="rentalStart || today" required />
            </div>
            <div class="co-days">
              <strong>{{ cart.days || "—" }}</strong>
              <span>jour{{ cart.days > 1 ? "s" : "" }}</span>
            </div>
          </div>

          <p v-if="cart.incompatibleItems.length" class="co-alert warn">
            <i class="fa-solid fa-triangle-exclamation"></i>
            Non proposé{{ cart.incompatibleItems.length > 1 ? "s" : "" }} {{ cart.isRental ? "à la location" : "à l'achat" }} :
            {{ cart.incompatibleItems.map((i) => i.title).join(", ") }}. Retirez-{{ cart.incompatibleItems.length > 1 ? "les" : "le" }} du panier ou changez de mode.
          </p>
          <p v-else-if="shortages.length" class="co-alert danger">
            <i class="fa-solid fa-circle-exclamation"></i>
            Stock insuffisant{{ cart.isRental ? " sur cette période" : "" }} :
            <template v-for="(item, index) in shortages" :key="item.id">
              {{ index ? " ; " : "" }}« {{ item.title }} » — {{ availability[item.id].available }} disponible{{ availability[item.id].available > 1 ? "s" : "" }} sur {{ item.quantity }}
            </template>.
            {{ cart.isRental ? "Réduisez la quantité ou choisissez d'autres dates." : "Réduisez la quantité." }}
          </p>
          <p v-else-if="!datesMissing && Object.keys(availability).length" class="co-alert ok">
            <i class="fa-solid fa-circle-check"></i>
            {{ cart.isRental ? `Tout est disponible du ${formatDay(cart.rentalStart)} au ${formatDay(cart.rentalEnd)}.` : "Tout est disponible." }}
          </p>
          <p v-else-if="checking" class="co-alert">Vérification des disponibilités…</p>
        </section>

        <!-- 2. Livraison -->
        <section class="ie-card ie-card-body">
          <h2 class="co-step"><span>2</span> {{ cart.isRental ? "Lieu de l'événement" : "Livraison" }}</h2>
          <p class="co-hint">{{ cart.isRental ? "Où devons-nous livrer et récupérer le matériel ?" : "Où devons-nous livrer votre commande ?" }}</p>
          <div class="ie-form-row">
            <div>
              <label class="ie-label" for="co-name">Nom complet</label>
              <input id="co-name" v-model="form.delivery_name" class="ie-input" required autocomplete="name" />
            </div>
            <div>
              <label class="ie-label" for="co-phone">Téléphone</label>
              <input id="co-phone" v-model="form.delivery_phone" class="ie-input" type="tel" required autocomplete="tel" placeholder="Ex : 6 70 00 00 00" />
            </div>
          </div>
          <label class="ie-label" for="co-city" style="margin-top: 14px;">Ville</label>
          <select id="co-city" v-model="form.delivery_city" class="ie-select" required>
            <option value="" disabled>Choisir une ville</option>
            <option v-for="city in cityOptions" :key="city" :value="city">{{ city }}</option>
          </select>
          <label class="ie-label" for="co-address" style="margin-top: 14px;">{{ cart.isRental ? "Adresse du lieu de l'événement" : "Adresse de livraison" }}</label>
          <textarea id="co-address" v-model="form.delivery_address" class="ie-input" rows="3" required placeholder="Quartier, rue, salle, point de repère…"></textarea>
          <label class="ie-label" for="co-notes" style="margin-top: 14px;">Note (optionnel)</label>
          <textarea id="co-notes" v-model="form.notes" class="ie-input" rows="2" :placeholder="cart.isRental ? 'Heure de livraison souhaitée, accès, contact sur place…' : 'Date souhaitée, horaires, instructions…'"></textarea>
        </section>

        <!-- 3. Paiement -->
        <section class="ie-card ie-card-body">
          <h2 class="co-step"><span>3</span> Paiement</h2>
          <div class="co-pay">
            <i class="fa-solid fa-hand-holding-dollar"></i>
            <div>
              <strong>Paiement à la livraison ou ultérieurement</strong>
              <p>Aucun paiement maintenant : votre facture est émise « À payer » et l'équipe InnovEvent vous contacte pour organiser la livraison{{ cart.isRental ? " et le retour du matériel" : "" }}.</p>
            </div>
          </div>
        </section>
      </div>

      <aside class="ie-card co-summary">
        <div class="co-summary-head">
          <h2>Récapitulatif</h2>
          <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="cart.openDrawer()"><i class="fa-solid fa-pen"></i> Modifier</button>
        </div>
        <span class="co-type" :class="{ rent: cart.isRental }">
          <i class="fa-solid" :class="cart.isRental ? 'fa-calendar-days' : 'fa-bag-shopping'"></i>
          {{ cart.isRental ? (cart.days ? `Location · ${cart.days} jour${cart.days > 1 ? "s" : ""}` : "Location · dates à choisir") : "Achat" }}
        </span>
        <ul>
          <li v-for="item in cart.items" :key="item.id" :class="{ short: availability[item.id] && !availability[item.id].ok }">
            <span class="co-thumb">
              <img v-if="item.photo" v-img="item.photo" :alt="item.title" />
              <i v-else class="fa-solid fa-box-open"></i>
              <b>{{ item.quantity }}</b>
            </span>
            <span class="co-line">
              <strong>{{ item.title }}</strong>
              <small>
                {{ item.quantity }} × {{ formatMoney(cart.lineUnit(item), item.currency) }}{{ cart.isRental ? ` × ${cart.days || 1} j` : "" }}
              </small>
            </span>
            <strong class="co-amount">{{ formatMoney(cart.lineTotal(item), item.currency) }}</strong>
          </li>
        </ul>
        <div class="co-totals">
          <div><span>Sous-total ({{ cart.count }} pièce{{ cart.count > 1 ? "s" : "" }})</span><span>{{ formatMoney(cart.total, cart.currency) }}</span></div>
          <div v-if="cart.isRental"><span>Soit par jour</span><span>{{ formatMoney(cart.perDayTotal, cart.currency) }}</span></div>
          <div><span>Livraison</span><span>À convenir</span></div>
          <div class="co-grand"><span>Total</span><strong>{{ formatMoney(cart.total, cart.currency) }}</strong></div>
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button type="submit" class="ie-btn ie-btn-primary co-submit" :disabled="submitting || !canSubmit">
          <i class="fa-solid fa-file-invoice"></i>
          {{ submitting ? "Enregistrement…" : cart.isRental ? "Réserver et générer ma facture" : "Valider et générer ma facture" }}
        </button>
        <p v-if="datesMissing" class="co-legal">Choisissez les dates de location pour continuer.</p>
        <p v-else class="co-legal">Les prix et les disponibilités sont vérifiés au moment de la validation.</p>
      </aside>
    </form>
  </div>
</template>

<style scoped>
.co { max-width: 1120px; margin: 0 auto; min-width: 0; }
.co-grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 22px; align-items: start; }
.co-steps { display: grid; gap: 16px; }
.co-step { display: flex; align-items: center; gap: 10px; margin: 0; color: var(--ie-navy); font-size: 18px; }
.co-step span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--ie-red); color: #fff; font-size: 13px; }
.co-hint { margin: 6px 0 16px; color: var(--ie-muted); font-size: 13px; }

.co-modes { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
.co-mode {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 16px; border: 2px solid var(--ie-line); border-radius: 14px;
  background: #fff; text-align: left; cursor: pointer; font-family: inherit; transition: border-color 0.15s ease, background 0.15s ease;
}
.co-mode i { display: grid; place-items: center; width: 38px; height: 38px; margin-bottom: 4px; border-radius: 10px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 16px; }
.co-mode strong { color: var(--ie-navy); font-size: 15px; }
.co-mode small { color: var(--ie-muted); font-size: 12.5px; }
.co-mode em { color: var(--ie-warning); font-size: 11.5px; font-style: normal; font-weight: 600; }
.co-mode.active { border-color: var(--ie-red); background: #fff8f8; }
.co-mode.active i { background: var(--ie-red); color: #fff; }
.co-mode.disabled:not(.active) { opacity: 0.65; }

.co-dates { display: grid; grid-template-columns: 1fr 1fr auto; gap: 12px; align-items: end; margin-top: 16px; padding: 14px; border-radius: 12px; background: #f7f8fa; }
.co-days { display: flex; flex-direction: column; align-items: center; min-width: 70px; padding: 6px 10px; border-radius: 10px; background: var(--ie-navy); color: #fff; }
.co-days strong { font-size: 20px; line-height: 1.1; }
.co-days span { font-size: 11px; opacity: 0.8; }

.co-alert { display: flex; gap: 8px; margin: 14px 0 0; padding: 10px 12px; border-radius: 10px; background: #f2f4f6; color: #4b5a6a; font-size: 13px; line-height: 1.45; }
.co-alert i { margin-top: 2px; }
.co-alert.ok { background: var(--ie-success-soft); color: var(--ie-success); }
.co-alert.warn { background: var(--ie-warning-soft); color: #7a4f00; }
.co-alert.danger { background: var(--ie-red-soft); color: var(--ie-red); }

.co-pay { display: flex; gap: 14px; margin-top: 14px; padding: 16px; border: 1px solid #cfe7d9; border-radius: 12px; background: var(--ie-success-soft); }
.co-pay > i { color: var(--ie-success); font-size: 22px; margin-top: 2px; }
.co-pay strong { color: var(--ie-navy); font-size: 14px; }
.co-pay p { margin: 4px 0 0; color: #4b5a6a; font-size: 13px; line-height: 1.5; }

.co-summary { position: sticky; top: 0; padding: 20px; }
.co-summary-head { display: flex; align-items: center; justify-content: space-between; }
.co-summary h2 { margin: 0; color: var(--ie-navy); font-size: 17px; }
.co-type { display: inline-flex; align-items: center; gap: 7px; margin-top: 10px; padding: 5px 11px; border-radius: 999px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 12px; font-weight: 700; }
.co-type.rent { background: var(--ie-navy); color: #fff; }
.co-summary ul { list-style: none; margin: 12px 0 0; padding: 0; max-height: 340px; overflow-y: auto; }
.co-summary li { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--ie-line); }
.co-summary li.short .co-line small { color: var(--ie-red); }
.co-thumb { position: relative; display: grid; place-items: center; width: 54px; height: 54px; flex: 0 0 54px; border-radius: 10px; background: #f2f4f6; color: #9aa3ac; }
.co-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 10px; }
.co-thumb b { position: absolute; top: -6px; right: -6px; display: grid; place-items: center; min-width: 20px; height: 20px; padding: 0 4px; border-radius: 999px; background: var(--ie-navy); color: #fff; font-size: 11px; }
.co-line { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.co-line strong { color: var(--ie-ink); font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.co-line small { color: var(--ie-muted); font-size: 12px; }
.co-amount { color: var(--ie-navy); font-size: 13.5px; white-space: nowrap; }
.co-totals { display: grid; gap: 8px; margin: 14px 0; font-size: 13.5px; color: #4b5a6a; }
.co-totals div { display: flex; justify-content: space-between; gap: 10px; }
.co-grand { padding-top: 12px; border-top: 2px solid var(--ie-navy); color: var(--ie-navy); font-size: 15px; font-weight: 700; }
.co-grand strong { font-size: 24px; }
.co-submit { width: 100%; justify-content: center; padding: 14px; font-size: 15px; }
.co-legal { margin: 10px 0 0; color: var(--ie-muted); font-size: 11.5px; text-align: center; }
@media (max-width: 900px) {
  .co-grid { grid-template-columns: 1fr; }
  .co-summary { position: static; }
}
@media (max-width: 560px) {
  .co-modes { grid-template-columns: 1fr; }
  .co-dates { grid-template-columns: 1fr 1fr; }
  .co-days { grid-column: 1 / -1; flex-direction: row; justify-content: center; gap: 6px; }
}
</style>
