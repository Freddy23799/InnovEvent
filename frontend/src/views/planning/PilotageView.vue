<script setup>
import { computed, onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import HorizontalBarList from "../../components/HorizontalBarList.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";

const tasks = ref([]);
const events = ref([]);
const participants = ref([]);
const loading = ref(true);
const statusFilter = ref("");

const STATUS_LABELS = {
  todo: "À faire",
  in_progress: "En cours",
  done: "Terminée",
  late: "En retard",
};

const eventById = computed(() => {
  const map = {};
  events.value.forEach((e) => (map[e.id] = e));
  return map;
});

const filteredTasks = computed(() => {
  if (!statusFilter.value) return tasks.value;
  return tasks.value.filter((t) => t.status === statusFilter.value);
});

const kpis = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  return {
    total: tasks.value.length,
    done: tasks.value.filter((t) => t.status === "done").length,
    late: tasks.value.filter((t) => t.due_date && t.due_date < today && t.status !== "done").length,
    inProgress: tasks.value.filter((t) => t.status === "in_progress").length,
  };
});

const participantKpis = computed(() => ({
  total: participants.value.length,
  checkedIn: participants.value.filter((p) => p.checked_in).length,
}));

const participantsByEvent = computed(() => {
  const counts = {};
  participants.value.forEach((p) => {
    const title = eventById.value[p.event]?.title || `Événement #${p.event}`;
    counts[title] = (counts[title] || 0) + 1;
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value, display: `${value} participant(s)` }));
});

const downloadingReport = ref(false);

async function downloadReport() {
  downloadingReport.value = true;
  try {
    const response = await api.get("/events/participants/report/", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "rapport-participants.pdf";
    link.click();
    window.URL.revokeObjectURL(url);
  } finally {
    downloadingReport.value = false;
  }
}

async function loadData() {
  loading.value = true;
  try {
    const [tasksRes, eventsRes, participantsRes] = await Promise.all([
      api.get("/events/tasks/", { params: { ordering: "due_date" } }),
      api.get("/events/"),
      api.get("/events/participants/"),
    ]);
    tasks.value = tasksRes.data.results || tasksRes.data;
    events.value = eventsRes.data.results || eventsRes.data;
    participants.value = participantsRes.data.results || participantsRes.data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-compass" style="color: var(--ie-red); margin-right: 8px;"></i>Pilotage des événements</h1>
    <p style="color: var(--ie-muted); margin: 6px 0 20px;">Vue transverse des tâches et des participants sur l'ensemble des événements.</p>

    <div class="ie-kpi-grid">
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ kpis.total }}</b><span>Tâches totales</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ kpis.inProgress }}</b><span>En cours</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ kpis.done }}</b><span>Terminées</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num" style="color: var(--ie-red);">{{ kpis.late }}</b><span>En retard</span></div>
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-list-check"></i>Tâches</h2>
        <select v-model="statusFilter" class="ie-select" style="width: 200px;">
          <option value="">Tous les statuts</option>
          <option value="todo">À faire</option>
          <option value="in_progress">En cours</option>
          <option value="done">Terminée</option>
          <option value="late">En retard</option>
        </select>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="filteredTasks.length">
        <table class="ie-table">
          <thead>
            <tr><th>Tâche</th><th>Événement</th><th>Échéance</th><th>Priorité</th><th>Statut</th></tr>
          </thead>
          <tbody>
            <tr v-for="task in filteredTasks" :key="task.id">
              <td>{{ task.title }}</td>
              <td>{{ eventById[task.event]?.title || "—" }}</td>
              <td>{{ task.due_date || "—" }}</td>
              <td>{{ task.priority }}</td>
              <td><span class="ie-badge ie-badge-neutral">{{ STATUS_LABELS[task.status] || task.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-list-check" text="Aucune tâche à afficher." />
    </div>

    <div class="ie-kpi-grid ie-section">
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ participantKpis.total }}</b><span>Participants inscrits (tous événements)</span></div>
      <div class="ie-card" style="padding:16px;"><b class="ie-kpi-num">{{ participantKpis.checkedIn }}</b><span>Présents (check-in effectué)</span></div>
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-user-group"></i>Participants par événement</h2>
      </div>
      <div class="ie-card-body">
        <div v-if="loading" class="ie-skeleton" style="height: 120px;"></div>
        <HorizontalBarList v-else :items="participantsByEvent" />
      </div>
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-address-book"></i>Liste des participants</h2>
        <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="downloadReport" :disabled="downloadingReport">
          <i class="fa-solid fa-file-pdf"></i> {{ downloadingReport ? "Génération…" : "Rapport PDF" }}
        </button>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="participants.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Email</th><th>Événement</th><th>Statut</th></tr>
          </thead>
          <tbody>
            <tr v-for="p in participants" :key="p.id">
              <td>{{ p.full_name || "—" }}</td>
              <td>{{ p.email || "—" }}</td>
              <td>{{ eventById[p.event]?.title || "—" }}</td>
              <td><span class="ie-badge" :class="p.checked_in ? 'ie-badge-success' : 'ie-badge-neutral'">{{ p.checked_in ? "Présent" : "Inscrit" }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-user-group" text="Aucun participant enregistré." />
    </div>
  </div>
</template>

<style scoped>
.ie-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.ie-kpi-num { display: block; font-size: 22px; color: var(--ie-navy); }
@media (max-width: 900px) { .ie-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
