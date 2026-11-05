<script setup>
import { computed, onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import ShopBar from "../../components/shop/ShopBar.vue";
import { formatDay, formatMoney } from "../../data/saleCategories";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";

// Le client voit ses commandes ; l'administration voit toutes les commandes
// de la boutique (et ouvre chaque facture pour la marquer payée ou annulée).
const auth = useAuthStore();
const isAdmin = computed(() => auth.role === "admin");
const orders = ref([]);
const loading = ref(true);
const statusFilter = ref("");

const STATUS_FILTERS = [
  { value: "", label: "Toutes" },
  { value: "pending_payment", label: "À payer" },
  { value: "paid", label: "Payées" },
  { value: "cancelled", label: "Annulées" },
];

async function loadOrders() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/sale-orders/", { params: { status: statusFilter.value || undefined } });
    orders.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function setFilter(value) {
  statusFilter.value = value;
  loadOrders();
}

function pieces(order) {
  return order.items.reduce((sum, item) => sum + item.quantity, 0);
}

onMounted(loadOrders);
</script>

<template>
  <div class="ie-orders">
    <ShopBar :crumbs="[{ label: isAdmin ? 'Commandes de la boutique' : 'Mes commandes' }]" />

    <div class="ie-orders-head">
      <div>
        <h1>{{ isAdmin ? "Commandes de la boutique" : "Mes commandes" }}</h1>
        <p class="ie-page-subtitle">{{ isAdmin ? "Toutes les commandes et leurs factures. Ouvrez une facture pour la marquer payée ou l'annuler." : "Retrouvez vos factures et le suivi de vos commandes." }}</p>
      </div>
      <div class="ie-orders-filters">
        <button v-for="f in STATUS_FILTERS" :key="f.value" type="button" :class="{ active: statusFilter === f.value }" @click="setFilter(f.value)">{{ f.label }}</button>
      </div>
    </div>

    <div v-if="loading" class="ie-orders-list" aria-busy="true">
      <div v-for="i in 3" :key="i" class="ie-skeleton" style="height: 96px; border-radius: 14px;"></div>
    </div>
    <div v-else-if="orders.length" class="ie-orders-list">
      <router-link v-for="order in orders" :key="order.id" :to="{ name: 'sale-invoice', params: { id: order.id } }" class="ie-order">
        <div class="ie-order-thumbs">
          <span v-for="item in order.items.slice(0, 3)" :key="item.id">
            <img v-if="item.photo" v-img="item.photo" :alt="item.title" />
            <i v-else class="fa-solid fa-box-open"></i>
          </span>
          <b v-if="order.items.length > 3">+{{ order.items.length - 3 }}</b>
        </div>
        <div class="ie-order-main">
          <strong>{{ order.number }}</strong>
          <span>
            <b class="ie-order-type" :class="order.order_type">{{ order.order_type_display }}</b>
            <template v-if="order.order_type === 'rental'">{{ formatDay(order.rental_start) }} → {{ formatDay(order.rental_end) }}</template>
            <template v-else>{{ new Date(order.created_at).toLocaleDateString("fr-FR") }}</template>
            · {{ pieces(order) }} pièce{{ pieces(order) > 1 ? "s" : "" }}
            <template v-if="isAdmin"> · {{ order.buyer_name }} · {{ order.delivery_city }}</template>
          </span>
        </div>
        <em v-if="order.order_type === 'rental' && order.status !== 'cancelled'" class="ie-order-status rental">{{ order.rental_status_display }}</em>
        <em class="ie-order-status" :class="order.status">{{ order.status_display }}</em>
        <strong class="ie-order-total">{{ formatMoney(order.total, order.currency) }}</strong>
        <i class="fa-solid fa-chevron-right ie-order-chevron"></i>
      </router-link>
    </div>
    <EmptyState v-else icon="fa-solid fa-file-invoice" :text="statusFilter ? 'Aucune commande avec ce statut.' : 'Aucune commande pour le moment.'">
      <router-link v-if="!isAdmin" :to="{ name: 'sale-shop' }" class="ie-btn ie-btn-primary">Découvrir la boutique</router-link>
    </EmptyState>
  </div>
</template>

<style scoped>
.ie-orders { max-width: 980px; margin: 0 auto; min-width: 0; }
.ie-orders-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.ie-orders-head h1 { margin: 0; }
.ie-orders-filters { display: flex; gap: 4px; padding: 4px; border-radius: 999px; background: #eef0f2; overflow-x: auto; }
.ie-orders-filters button { flex-shrink: 0; padding: 7px 14px; border: 0; border-radius: 999px; background: none; color: #5d6771; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; }
.ie-orders-filters button.active { background: #fff; color: var(--ie-navy); box-shadow: 0 2px 6px #0000001a; }
.ie-orders-list { display: grid; gap: 10px; }
.ie-order {
  display: flex; align-items: center; gap: 16px; padding: 14px 18px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff;
  color: inherit; text-decoration: none; transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
.ie-order:hover { border-color: #cfd5dc; box-shadow: 0 10px 24px #18283b12; }
.ie-order-thumbs { display: flex; align-items: center; flex-shrink: 0; }
.ie-order-thumbs span { display: grid; place-items: center; width: 46px; height: 46px; margin-left: -10px; overflow: hidden; border: 2px solid #fff; border-radius: 10px; background: #f2f4f6; color: #9aa3ac; }
.ie-order-thumbs span:first-child { margin-left: 0; }
.ie-order-thumbs img { width: 100%; height: 100%; object-fit: cover; }
.ie-order-thumbs b { margin-left: 6px; color: var(--ie-muted); font-size: 12px; }
.ie-order-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ie-order-main strong { color: var(--ie-navy); font-size: 15px; }
.ie-order-main span { color: var(--ie-muted); font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ie-order-status { flex-shrink: 0; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 800; font-style: normal; text-transform: uppercase; }
.ie-order-status.pending_payment { background: #fff3d6; color: #8a5a00; }
.ie-order-status.paid { background: #dff3e7; color: #1e7b4d; }
.ie-order-status.cancelled { background: #eceff2; color: #5d6771; }
.ie-order-status.rental { background: var(--ie-navy-soft); color: var(--ie-navy); }
.ie-order-type { margin-right: 4px; padding: 1px 7px; border-radius: 5px; background: #eef0f2; color: var(--ie-navy); font-size: 11px; }
.ie-order-type.rental { background: var(--ie-navy); color: #fff; }
.ie-order-total { flex-shrink: 0; min-width: 110px; color: var(--ie-navy); font-size: 15px; text-align: right; }
.ie-order-chevron { color: #b4bcc4; font-size: 12px; }
@media (max-width: 640px) {
  .ie-order { flex-wrap: wrap; gap: 10px 12px; padding: 12px 14px; }
  .ie-order-main { flex-basis: calc(100% - 160px); }
  .ie-order-chevron { display: none; }
  .ie-order-total { min-width: 0; margin-left: auto; }
}
</style>
