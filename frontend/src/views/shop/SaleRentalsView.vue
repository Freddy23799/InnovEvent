<script setup>
import { computed, onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import { formatDay, formatMoney } from "../../data/saleCategories";
import api from "../../services/api";

// Planning des locations de la boutique (administration) : qui a pris quoi,
// combien de pièces, où et sur quelle période — et l'état de chaque location.
const TABS = [
  { value: "ongoing", label: "En cours", icon: "fa-solid fa-truck-fast" },
  { value: "upcoming", label: "À venir", icon: "fa-solid fa-calendar-plus" },
  { value: "closed", label: "Terminées", icon: "fa-solid fa-box-archive" },
];

const tab = ref("ongoing");
const rentals = ref([]);
const ongoing = ref([]);
const upcoming = ref([]);
const loading = ref(true);
const search = ref("");

async function fetchPeriod(period) {
  const { data } = await api.get("/marketplace/sale-orders/", { params: { order_type: "rental", period } });
  return data.results || data;
}

async function loadAll() {
  loading.value = true;
  try {
    [ongoing.value, upcoming.value] = await Promise.all([fetchPeriod("ongoing"), fetchPeriod("upcoming")]);
    rentals.value = tab.value === "ongoing" ? ongoing.value : tab.value === "upcoming" ? upcoming.value : await fetchPeriod("closed");
  } finally {
    loading.value = false;
  }
}

async function selectTab(value) {
  tab.value = value;
  loading.value = true;
  try {
    rentals.value = value === "ongoing" ? ongoing.value : value === "upcoming" ? upcoming.value : await fetchPeriod("closed");
  } finally {
    loading.value = false;
  }
}

const filteredRentals = computed(() => {
  const needle = search.value.trim().toLowerCase();
  if (!needle) return rentals.value;
  return rentals.value.filter((r) =>
    [r.number, r.delivery_name, r.delivery_phone, r.delivery_city, r.delivery_address, ...r.items.map((i) => i.title)]
      .join(" ").toLowerCase().includes(needle)
  );
});

const pieces = (order) => order.items.reduce((sum, item) => sum + item.quantity, 0);

// Pièces actuellement chez les clients, par produit.
const outByProduct = computed(() => {
  const totals = {};
  ongoing.value.filter((r) => r.rental_status === "out").forEach((r) => {
    r.items.forEach((item) => { totals[item.title] = (totals[item.title] || 0) + item.quantity; });
  });
  return Object.entries(totals).sort((a, b) => b[1] - a[1]);
});
const kpis = computed(() => {
  const todayIso = new Date().toISOString().slice(0, 10);
  return {
    out: ongoing.value.filter((r) => r.rental_status === "out").reduce((sum, r) => sum + pieces(r), 0),
    toDeliver: ongoing.value.filter((r) => r.rental_status === "reserved").length,
    toCollect: ongoing.value.filter((r) => r.rental_status === "out" && r.rental_end <= todayIso).length,
    upcoming: upcoming.value.length,
  };
});

function lateness(order) {
  const todayIso = new Date().toISOString().slice(0, 10);
  if (order.rental_status === "out" && order.rental_end < todayIso) return "late";
  if (order.rental_status === "out" && order.rental_end === todayIso) return "due";
  return "";
}

onMounted(loadAll);
</script>

<template>
  <div class="rp">
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-days" style="color: var(--ie-red); margin-right: 8px;"></i>Locations de la boutique</h1>
        <p class="ie-page-subtitle">Qui a loué quoi, combien de pièces, où et sur quelle période. Ouvrez une location pour la marquer sortie ou enregistrer son retour.</p>
      </div>
    </div>

    <div class="rp-kpis">
      <div><span><i class="fa-solid fa-boxes-stacked"></i></span><strong>{{ kpis.out }}</strong><small>pièces chez les clients</small></div>
      <div><span><i class="fa-solid fa-truck-fast"></i></span><strong>{{ kpis.toDeliver }}</strong><small>à livrer (période commencée)</small></div>
      <div :class="{ alert: kpis.toCollect }"><span><i class="fa-solid fa-rotate-left"></i></span><strong>{{ kpis.toCollect }}</strong><small>à récupérer aujourd'hui ou en retard</small></div>
      <div><span><i class="fa-solid fa-calendar-plus"></i></span><strong>{{ kpis.upcoming }}</strong><small>locations à venir</small></div>
    </div>

    <div class="rp-layout">
      <section class="ie-card rp-main">
        <div class="rp-toolbar">
          <div class="rp-tabs">
            <button v-for="t in TABS" :key="t.value" type="button" :class="{ active: tab === t.value }" @click="selectTab(t.value)">
              <i :class="t.icon"></i> {{ t.label }}
              <span v-if="t.value === 'ongoing'">{{ ongoing.length }}</span>
              <span v-else-if="t.value === 'upcoming'">{{ upcoming.length }}</span>
            </button>
          </div>
          <input v-model="search" type="search" class="ie-input rp-search" placeholder="Client, ville, produit, n° de facture…" aria-label="Rechercher une location" />
        </div>

        <div v-if="loading" class="rp-list"><div v-for="i in 3" :key="i" class="ie-skeleton" style="height: 110px; border-radius: 12px;"></div></div>
        <div v-else-if="filteredRentals.length" class="rp-list">
          <router-link v-for="r in filteredRentals" :key="r.id" :to="{ name: 'sale-invoice', params: { id: r.id } }" class="rp-item" :class="lateness(r)">
            <div class="rp-dates">
              <strong>{{ formatDay(r.rental_start) }}</strong>
              <i class="fa-solid fa-arrow-down"></i>
              <strong>{{ formatDay(r.rental_end) }}</strong>
              <small>{{ r.rental_days }} j</small>
            </div>
            <div class="rp-body">
              <div class="rp-head">
                <strong>{{ r.delivery_name }}</strong>
                <span class="rp-number">{{ r.number }}</span>
                <em class="rp-status" :class="r.status === 'cancelled' ? 'cancelled' : r.rental_status">{{ r.status === "cancelled" ? "Annulée" : r.rental_status_display }}</em>
                <em v-if="lateness(r) === 'late'" class="rp-status late">En retard</em>
                <em v-else-if="lateness(r) === 'due'" class="rp-status due">Retour aujourd'hui</em>
              </div>
              <p class="rp-where"><i class="fa-solid fa-location-dot"></i> {{ r.delivery_city }} — {{ r.delivery_address }} · <i class="fa-solid fa-phone"></i> {{ r.delivery_phone }}</p>
              <ul class="rp-items">
                <li v-for="item in r.items" :key="item.id"><b>{{ item.quantity }}</b> {{ item.title }}<template v-if="item.damaged_quantity || item.lost_quantity"> <i class="rp-damage">({{ item.damaged_quantity + item.lost_quantity }} abîmée(s)/perdue(s))</i></template></li>
              </ul>
            </div>
            <div class="rp-total">
              <strong>{{ formatMoney(r.total, r.currency) }}</strong>
              <small>{{ r.status_display }}</small>
            </div>
          </router-link>
        </div>
        <EmptyState v-else icon="fa-solid fa-calendar-xmark" :text="search ? 'Aucune location ne correspond à cette recherche.' : 'Aucune location dans cette catégorie.'" />
      </section>

      <aside class="ie-card ie-card-body rp-side">
        <h2>Matériel actuellement sorti</h2>
        <ul v-if="outByProduct.length" class="rp-out">
          <li v-for="[title, qty] in outByProduct" :key="title"><span>{{ title }}</span><strong>{{ qty }}</strong></li>
        </ul>
        <p v-else class="ie-field-hint">Aucun matériel chez les clients en ce moment.</p>
        <router-link :to="{ name: 'stock-movements' }" class="ie-btn ie-btn-ghost ie-btn-sm rp-stock-link"><i class="fa-solid fa-boxes-stacked"></i> Mouvements de stock</router-link>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.rp-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }
.rp-kpis > div { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 12px; align-items: center; padding: 14px 16px; border: 1px solid var(--ie-line); border-radius: 14px; background: #fff; }
.rp-kpis span { grid-row: span 2; display: grid; place-items: center; width: 42px; height: 42px; border-radius: 11px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 16px; }
.rp-kpis strong { color: var(--ie-navy); font-size: 22px; line-height: 1.1; }
.rp-kpis small { color: var(--ie-muted); font-size: 12px; }
.rp-kpis > div.alert { border-color: #f0dcb0; background: var(--ie-warning-soft); }
.rp-kpis > div.alert span { background: var(--ie-warning); color: #fff; }

.rp-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 18px; align-items: start; }
.rp-main { padding: 16px; }
.rp-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.rp-tabs { display: flex; gap: 4px; padding: 4px; border-radius: 12px; background: #eef0f2; }
.rp-tabs button { display: inline-flex; align-items: center; gap: 7px; padding: 8px 12px; border: 0; border-radius: 9px; background: none; color: #5d6771; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; }
.rp-tabs button span { padding: 0 6px; border-radius: 999px; background: #dfe3e8; font-size: 11px; }
.rp-tabs button.active { background: #fff; color: var(--ie-navy); box-shadow: 0 2px 6px #0000001a; }
.rp-search { max-width: 280px; }
.rp-list { display: grid; gap: 10px; }
.rp-item { display: flex; gap: 16px; padding: 14px; border: 1px solid var(--ie-line); border-left: 4px solid var(--ie-line); border-radius: 12px; color: inherit; text-decoration: none; transition: box-shadow 0.2s ease; }
.rp-item:hover { box-shadow: 0 10px 24px #18283b12; }
.rp-item.due { border-left-color: var(--ie-warning); }
.rp-item.late { border-left-color: var(--ie-red); }
.rp-dates { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; min-width: 92px; padding: 8px; border-radius: 10px; background: #f7f8fa; text-align: center; }
.rp-dates strong { color: var(--ie-navy); font-size: 12.5px; }
.rp-dates i { color: var(--ie-muted); font-size: 10px; }
.rp-dates small { margin-top: 2px; padding: 1px 8px; border-radius: 999px; background: var(--ie-navy); color: #fff; font-size: 11px; font-weight: 700; }
.rp-body { flex: 1; min-width: 0; }
.rp-head { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.rp-head strong { color: var(--ie-navy); font-size: 15px; }
.rp-number { color: var(--ie-muted); font-size: 12px; }
.rp-status { padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 800; font-style: normal; }
.rp-status.reserved { background: var(--ie-navy-soft); color: var(--ie-navy); }
.rp-status.out { background: #e0ecff; color: #1d4f9c; }
.rp-status.returned { background: var(--ie-success-soft); color: var(--ie-success); }
.rp-status.cancelled { background: #eceff2; color: #5d6771; }
.rp-status.due { background: var(--ie-warning-soft); color: var(--ie-warning); }
.rp-status.late { background: var(--ie-red-soft); color: var(--ie-red); }
.rp-where { margin: 6px 0 8px; color: #4b5a6a; font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rp-where i { color: var(--ie-muted); font-size: 11px; }
.rp-items { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }
.rp-items li { padding: 4px 9px; border-radius: 8px; background: #f2f4f6; color: #39495b; font-size: 12px; }
.rp-items b { color: var(--ie-red); }
.rp-damage { color: var(--ie-warning); font-style: normal; }
.rp-total { display: flex; flex-direction: column; align-items: flex-end; justify-content: center; gap: 2px; text-align: right; }
.rp-total strong { color: var(--ie-navy); font-size: 15px; white-space: nowrap; }
.rp-total small { color: var(--ie-muted); font-size: 11.5px; }

.rp-side h2 { margin: 0 0 12px; color: var(--ie-navy); font-size: 15px; }
.rp-out { display: grid; gap: 6px; margin: 0 0 14px; padding: 0; list-style: none; }
.rp-out li { display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px; border-radius: 8px; background: #f7f8fa; font-size: 13px; }
.rp-out strong { color: var(--ie-red); }
.rp-stock-link { width: 100%; justify-content: center; }

@media (max-width: 1000px) {
  .rp-layout { grid-template-columns: 1fr; }
  .rp-kpis { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .rp-kpis { grid-template-columns: 1fr; }
  .rp-item { flex-wrap: wrap; }
  .rp-dates { flex-direction: row; min-width: 0; width: 100%; }
  .rp-total { flex-direction: row; align-items: baseline; gap: 8px; width: 100%; justify-content: flex-end; }
  .rp-search { max-width: none; width: 100%; }
}
</style>
