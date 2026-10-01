<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../../services/api";

const profile = ref(null);
const loading = ref(true);
const cursor = ref(new Date());
const monthData = ref({});
const monthLoading = ref(false);
const settings = reactive({ min_notice_days: 2, max_bookings_per_day: 1 });
const settingsSaving = ref(false);
const settingsSaved = ref(false);

const monthLabel = computed(() => cursor.value.toLocaleDateString("fr-FR", { month: "long", year: "numeric" }));

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

function isoDate(date) {
  return date ? date.toISOString().slice(0, 10) : null;
}

function statusFor(date) {
  return monthData.value[isoDate(date)] || null;
}

async function loadProfile() {
  const { data } = await api.get("/marketplace/profiles/");
  const list = data.results || data;
  const own = list.find((p) => p.is_owner);
  if (own) {
    const { data: full } = await api.get(`/marketplace/profiles/${own.id}/`);
    profile.value = full;
    const { data: s } = await api.get(`/marketplace/profiles/${own.id}/availability-settings/`);
    Object.assign(settings, s);
  }
}

async function loadMonth() {
  if (!profile.value) return;
  monthLoading.value = true;
  try {
    const { data } = await api.get(`/marketplace/profiles/${profile.value.id}/availability/`, {
      params: { year: cursor.value.getFullYear(), month: cursor.value.getMonth() + 1 },
    });
    monthData.value = data;
  } finally {
    monthLoading.value = false;
  }
}

function changeMonth(delta) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1);
  loadMonth();
}

async function toggleDay(date) {
  const status = statusFor(date);
  if (status === "past" || status === "too_soon" || status === "full") return;
  if (status === "blocked") {
    const { data } = await api.get("/marketplace/blocked-dates/", { params: { profile: profile.value.id } });
    const match = (data.results || data).find((b) => b.date === isoDate(date));
    if (match) await api.delete(`/marketplace/blocked-dates/${match.id}/`);
  } else {
    await api.post("/marketplace/blocked-dates/", { profile: profile.value.id, date: isoDate(date) });
  }
  await loadMonth();
}

async function saveSettings() {
  settingsSaving.value = true;
  try {
    await api.patch(`/marketplace/profiles/${profile.value.id}/availability-settings/`, settings);
    settingsSaved.value = true;
    setTimeout(() => { settingsSaved.value = false; }, 1500);
    await loadMonth();
  } finally {
    settingsSaving.value = false;
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    await loadProfile();
    await loadMonth();
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-check" style="color: var(--ie-red); margin-right: 8px;"></i>Mes disponibilités</h1>
        <p class="ie-page-subtitle">Cliquez sur un jour pour le bloquer ou le débloquer. Les prestations confirmées bloquent automatiquement leur date.</p>
      </div>
      <div class="ie-calendar-nav" v-if="profile">
        <button class="ie-btn ie-btn-secondary" @click="changeMonth(-1)"><i class="fa-solid fa-chevron-left"></i></button>
        <strong class="ie-month-label">{{ monthLabel }}</strong>
        <button class="ie-btn ie-btn-secondary" @click="changeMonth(1)"><i class="fa-solid fa-chevron-right"></i></button>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 400px;"></div>

    <template v-else-if="profile">
      <div class="ie-card ie-card-body" style="margin-bottom: 20px;">
        <h2 style="margin: 0 0 12px;">Réglages</h2>
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Délai minimum de réservation (jours)</label>
            <input v-model.number="settings.min_notice_days" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Prestations maximum par jour</label>
            <input v-model.number="settings.max_bookings_per_day" type="number" min="1" class="ie-input" />
          </div>
          <button class="ie-btn ie-btn-primary ie-btn-sm" style="align-self: flex-end;" :disabled="settingsSaving" @click="saveSettings">
            {{ settingsSaving ? "Enregistrement…" : "Enregistrer" }}
            <i v-if="settingsSaved" class="fa-solid fa-circle-check" style="margin-left: 6px;"></i>
          </button>
        </div>
      </div>

      <div class="ie-card ie-card-body" style="overflow-x: auto;">
        <div class="ie-availability-legend">
          <span><i class="ie-dot ie-dot-available"></i> Disponible</span>
          <span><i class="ie-dot ie-dot-blocked"></i> Bloqué</span>
          <span><i class="ie-dot ie-dot-full"></i> Complet</span>
          <span><i class="ie-dot ie-dot-disabled"></i> Passé / trop proche</span>
        </div>
        <div v-if="monthLoading" class="ie-skeleton" style="height: 300px; margin-top: 12px;"></div>
        <table v-else class="ie-calendar" style="margin-top: 12px;">
          <thead>
            <tr><th v-for="d in ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']" :key="d">{{ d }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(week, wi) in weeks" :key="wi">
              <td
                v-for="(day, di) in week" :key="di"
                class="ie-calendar-cell ie-availability-cell"
                :class="[{ empty: !day }, day ? `status-${statusFor(day)}` : '']"
                @click="day && toggleDay(day)"
              >
                <span v-if="day" class="ie-calendar-day">{{ day.getDate() }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="ie-card ie-card-body">
      <p class="ie-field-hint">Créez d'abord votre profil professionnel pour gérer vos disponibilités.</p>
    </div>
  </div>
</template>

<style scoped>
.ie-calendar-nav { display: flex; align-items: center; gap: 12px; }
.ie-month-label { color: var(--ie-navy); text-transform: capitalize; min-width: 150px; text-align: center; }
.ie-calendar { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ie-calendar th { padding: 8px; font-size: 11px; color: var(--ie-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.ie-calendar-cell { border: 1px solid var(--ie-line); vertical-align: top; height: 60px; padding: 6px; width: 14.28%; }
.ie-calendar-cell.empty { background: #fafbfc; }
.ie-calendar-day { font-size: 12px; font-weight: 700; color: var(--ie-navy); }

.ie-availability-cell { cursor: pointer; transition: background 0.1s ease; }
.ie-availability-cell.status-available { background: var(--ie-success-soft); }
.ie-availability-cell.status-blocked { background: var(--ie-red-soft); }
.ie-availability-cell.status-full { background: var(--ie-warning-soft); }
.ie-availability-cell.status-past, .ie-availability-cell.status-too_soon { background: #f2f3f5; cursor: default; opacity: 0.6; }

.ie-availability-legend { display: flex; gap: 18px; flex-wrap: wrap; font-size: 12px; color: var(--ie-muted); }
.ie-availability-legend span { display: inline-flex; align-items: center; gap: 6px; }
.ie-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.ie-dot-available { background: var(--ie-success); }
.ie-dot-blocked { background: var(--ie-red); }
.ie-dot-full { background: var(--ie-warning); }
.ie-dot-disabled { background: #b7bcc2; }
</style>
