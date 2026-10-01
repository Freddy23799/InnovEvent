<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../../services/api";

const STATUS_BADGE = {
  created: "ie-badge-neutral", pending: "ie-badge-warning", confirmed: "ie-badge-success", to_prepare: "ie-badge-warning",
  ready: "ie-badge-warning", carrier_assigned: "ie-badge-success", collected: "ie-badge-success", in_transit: "ie-badge-success",
  arrived: "ie-badge-success", delivering: "ie-badge-success", delivered: "ie-badge-success", failed: "ie-badge-danger",
  postponed: "ie-badge-warning", cancelled: "ie-badge-danger", returning: "ie-badge-warning", returned: "ie-badge-danger",
};

const deliveries = ref([]);
const loading = ref(true);
const cursor = ref(new Date());
const selectedDate = ref(new Date());

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString("fr-FR", { month: "long", year: "numeric" })
);

const weeks = computed(() => {
  const year = cursor.value.getFullYear();
  const month = cursor.value.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let day = 1; day <= daysInMonth; day++) cells.push(new Date(year, month, day));
  while (cells.length % 7 !== 0) cells.push(null);

  const result = [];
  for (let i = 0; i < cells.length; i += 7) result.push(cells.slice(i, i + 7));
  return result;
});

function dateKey(date) {
  if (!date) return "";
  return date.toISOString().slice(0, 10);
}

function isSameDay(a, b) {
  return a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function deliveriesForDay(date) {
  if (!date) return [];
  const key = dateKey(date);
  return deliveries.value.filter((d) => d.scheduled_date === key);
}

function isToday(date) {
  return isSameDay(date, new Date());
}

function selectDay(date) {
  if (!date) return;
  selectedDate.value = date;
}

function changeMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1);
}

const selectedDayDeliveries = computed(() => deliveriesForDay(selectedDate.value));
const selectedDayLabel = computed(() =>
  selectedDate.value.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
);

const selectedDayConflicts = computed(() => {
  const byDriver = new Map();
  for (const d of selectedDayDeliveries.value) {
    if (!d.driver) continue;
    if (!byDriver.has(d.driver)) byDriver.set(d.driver, []);
    byDriver.get(d.driver).push(d);
  }
  return [...byDriver.entries()].filter(([, list]) => list.length > 1).map(([, list]) => list);
});

async function loadDeliveries() {
  loading.value = true;
  try {
    const all = [];
    let url = "/deliveries/";
    while (url) {
      const { data } = await api.get(url);
      if (Array.isArray(data)) {
        all.push(...data);
        break;
      }
      all.push(...(data.results || []));
      url = data.next ? data.next.replace(api.defaults.baseURL, "") : null;
    }
    deliveries.value = all.filter((d) => d.scheduled_date);
  } finally {
    loading.value = false;
  }
}

onMounted(loadDeliveries);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-days" style="color: var(--ie-red); margin-right: 8px;"></i>Planning des livraisons</h1>
        <p class="ie-page-subtitle">Cliquez sur un jour pour voir les livraisons programmées et détecter les conflits d'affectation.</p>
      </div>
      <div class="ie-calendar-nav">
        <button class="ie-btn ie-btn-secondary" @click="changeMonth(-1)"><i class="fa-solid fa-chevron-left"></i></button>
        <strong class="ie-month-label">{{ monthLabel }}</strong>
        <button class="ie-btn ie-btn-secondary" @click="changeMonth(1)"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
    </div>

    <div class="ie-card ie-card-body" style="overflow-x: auto;">
      <div v-if="loading" class="ie-skeleton" style="height: 400px;"></div>
      <table v-else class="ie-calendar">
        <thead>
          <tr>
            <th v-for="d in ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']" :key="d">{{ d }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(week, wi) in weeks" :key="wi">
            <td
              v-for="(day, di) in week" :key="di"
              class="ie-calendar-cell"
              :class="{ today: isToday(day), empty: !day, occupied: deliveriesForDay(day).length, selected: isSameDay(day, selectedDate) }"
              @click="selectDay(day)"
            >
              <span v-if="day" class="ie-calendar-day">{{ day.getDate() }}</span>
              <div class="ie-calendar-events">
                <div v-for="dl in deliveriesForDay(day).slice(0, 2)" :key="dl.id" class="ie-calendar-dot" :title="dl.reference">
                  {{ dl.reference }}
                </div>
                <div v-if="deliveriesForDay(day).length > 2" class="ie-calendar-more">+{{ deliveriesForDay(day).length - 2 }} autre(s)</div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-circle-info"></i>{{ selectedDayLabel }}</h2>
        <span class="ie-badge ie-badge-neutral">{{ selectedDayDeliveries.length }} livraison(s)</span>
      </div>
      <div class="ie-card-body">
        <div v-if="selectedDayConflicts.length" class="ie-alert ie-alert-warning" style="margin-bottom: 14px;">
          <i class="fa-solid fa-triangle-exclamation"></i> Conflit d'affectation détecté : un même chauffeur a plusieurs livraisons ce jour-là.
        </div>
        <div v-if="!selectedDayDeliveries.length" class="ie-empty-state">
          <i class="fa-solid fa-calendar-xmark"></i>
          Aucune livraison programmée ce jour-là.
        </div>
        <div v-else class="ie-day-events">
          <div v-for="dl in selectedDayDeliveries" :key="dl.id" class="ie-day-event-card">
            <div class="ie-day-event-content">
              <div class="ie-day-event-header">
                <strong>{{ dl.reference }} — {{ dl.destination_address }}</strong>
                <span class="ie-badge" :class="STATUS_BADGE[dl.status] || 'ie-badge-neutral'">{{ dl.status_display }}</span>
              </div>
              <div class="ie-day-event-meta">
                <span><i class="fa-solid fa-truck"></i> {{ dl.carrier_name || "Non affecté" }}</span>
                <span><i class="fa-solid fa-id-card"></i> {{ dl.driver_name || "Aucun chauffeur" }}</span>
                <span><i class="fa-solid fa-car"></i> {{ dl.vehicle_plate || "Aucun véhicule" }}</span>
                <router-link :to="{ name: 'delivery-detail', params: { id: dl.id } }" class="ie-btn ie-btn-secondary ie-btn-sm">
                  Voir la fiche
                </router-link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.ie-calendar-nav { display: flex; align-items: center; gap: 12px; }
.ie-month-label { color: var(--ie-navy); text-transform: capitalize; min-width: 150px; text-align: center; }
.ie-calendar { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ie-calendar th { padding: 8px; font-size: 11px; color: var(--ie-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.ie-calendar-cell { border: 1px solid var(--ie-line); vertical-align: top; height: 96px; padding: 6px; width: 14.28%; cursor: pointer; transition: background 0.1s ease; }
.ie-calendar-cell:hover { background: #fafbfc; }
.ie-calendar-cell.empty { background: #fafbfc; cursor: default; }
.ie-calendar-cell.today .ie-calendar-day { color: var(--ie-red); }
.ie-calendar-cell.occupied { box-shadow: inset 3px 0 0 var(--ie-red); }
.ie-calendar-cell.selected { background: var(--ie-red-soft); }
.ie-calendar-day { font-size: 12px; font-weight: 700; color: var(--ie-navy); }
.ie-calendar-events { display: flex; flex-direction: column; gap: 3px; margin-top: 4px; }
.ie-calendar-dot {
  background: var(--ie-navy); color: #fff; border-radius: 5px;
  padding: 3px 6px; font-size: 10.5px; text-align: left;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ie-calendar-more { font-size: 10.5px; color: var(--ie-muted); padding-left: 2px; }

.ie-day-events { display: flex; flex-direction: column; gap: 14px; }
.ie-day-event-card { border: 1px solid var(--ie-line); border-radius: var(--ie-radius-md); padding: 14px 16px; }
.ie-day-event-header { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.ie-day-event-meta { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; font-size: 12.5px; color: var(--ie-ink); }
.ie-day-event-meta i { color: var(--ie-red); margin-right: 4px; }
</style>
