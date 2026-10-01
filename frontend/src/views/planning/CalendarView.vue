<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();

const STATUS_LABELS = { draft: "Brouillon", published: "Publié", ongoing: "En cours", completed: "Terminé", cancelled: "Annulé" };
const STATUS_BADGE = { draft: "ie-badge-neutral", published: "ie-badge-success", ongoing: "ie-badge-warning", completed: "ie-badge-neutral", cancelled: "ie-badge-danger" };

const events = ref([]);
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
  const startOffset = (firstDay.getDay() + 6) % 7; // lundi = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let day = 1; day <= daysInMonth; day++) cells.push(new Date(year, month, day));
  while (cells.length % 7 !== 0) cells.push(null);

  const result = [];
  for (let i = 0; i < cells.length; i += 7) result.push(cells.slice(i, i + 7));
  return result;
});

function isSameDay(a, b) {
  return a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function eventsForDay(date) {
  if (!date) return [];
  return events.value.filter((e) => isSameDay(new Date(e.start_date), date));
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

const selectedDayEvents = computed(() => eventsForDay(selectedDate.value));
const selectedDayLabel = computed(() =>
  selectedDate.value.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
);

async function loadEvents() {
  loading.value = true;
  try {
    const { data } = await api.get("/events/", { params: { ordering: "start_date" } });
    events.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadEvents);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-days" style="color: var(--ie-red); margin-right: 8px;"></i>Calendrier des événements</h1>
        <p class="ie-page-subtitle">Cliquez sur un jour pour voir le détail des événements prévus.</p>
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
              :class="{ today: isToday(day), empty: !day, occupied: eventsForDay(day).length, selected: isSameDay(day, selectedDate) }"
              @click="selectDay(day)"
            >
              <span v-if="day" class="ie-calendar-day">{{ day.getDate() }}</span>
              <div class="ie-calendar-events">
                <div v-for="ev in eventsForDay(day).slice(0, 2)" :key="ev.id" class="ie-calendar-dot" :title="ev.title">
                  {{ ev.title }}
                </div>
                <div v-if="eventsForDay(day).length > 2" class="ie-calendar-more">+{{ eventsForDay(day).length - 2 }} autre(s)</div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-circle-info"></i>{{ selectedDayLabel }}</h2>
        <span class="ie-badge ie-badge-neutral">{{ selectedDayEvents.length }} événement(s)</span>
      </div>
      <div class="ie-card-body">
        <div v-if="!selectedDayEvents.length" class="ie-empty-state">
          <i class="fa-solid fa-calendar-xmark"></i>
          Aucun événement ce jour-là — journée libre.
        </div>
        <div v-else class="ie-day-events">
          <div v-for="ev in selectedDayEvents" :key="ev.id" class="ie-day-event-card">
            <div class="ie-day-event-thumb">
              <img v-if="ev.photo" :src="ev.photo" :alt="ev.title" class="ie-zoomable" @click="lightbox.open(ev.photo, ev.title)" />
              <i v-else class="fa-solid fa-calendar-week"></i>
            </div>
            <div class="ie-day-event-content">
              <div class="ie-day-event-header">
                <strong>{{ ev.title }}</strong>
                <span class="ie-badge" :class="STATUS_BADGE[ev.status] || 'ie-badge-neutral'">{{ STATUS_LABELS[ev.status] || ev.status }}</span>
              </div>
              <p class="ie-day-event-desc">{{ ev.description || "Aucune description fournie pour cet événement." }}</p>
              <div class="ie-day-event-meta">
                <span><i class="fa-solid fa-clock"></i> {{ new Date(ev.start_date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) }} — {{ new Date(ev.end_date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) }}</span>
                <span><i class="fa-solid fa-users"></i> {{ ev.participants_count }} participant(s)</span>
                <router-link :to="{ name: 'event-detail', params: { id: ev.id } }" class="ie-btn ie-btn-secondary ie-btn-sm">
                  Voir la fiche complète
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
.ie-day-event-card { display: flex; gap: 14px; border: 1px solid var(--ie-line); border-radius: var(--ie-radius-md); padding: 14px 16px; }
.ie-day-event-thumb {
  width: 72px; height: 72px; border-radius: 8px; overflow: hidden; flex-shrink: 0;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-day-event-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-day-event-thumb i { color: var(--ie-navy); opacity: 0.4; font-size: 22px; }
.ie-day-event-content { flex: 1; min-width: 0; }
.ie-day-event-header { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 8px; }
.ie-day-event-desc { font-size: 13px; color: var(--ie-muted); margin: 0 0 12px; line-height: 1.55; }
.ie-day-event-meta { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; font-size: 12.5px; color: var(--ie-ink); }
.ie-day-event-meta i { color: var(--ie-red); margin-right: 4px; }
</style>
