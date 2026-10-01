<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();

const props = defineProps({ id: { type: [String, Number], required: true } });

const TASK_STATUS_LABELS = { todo: "À faire", in_progress: "En cours", done: "Terminée", late: "En retard" };
const TASK_STATUS_BADGE = { todo: "ie-badge-neutral", in_progress: "ie-badge-warning", done: "ie-badge-success", late: "ie-badge-danger" };

const event = ref(null);
const tasks = ref([]);
const participants = ref([]);
const expenses = ref([]);
const loading = ref(true);

const showTaskForm = ref(false);
const taskForm = reactive({ title: "", due_date: "", priority: "medium" });

const showParticipantForm = ref(false);
const participantForm = reactive({ full_name: "", email: "" });

const showExpenseForm = ref(false);
const expenseForm = reactive({ label: "", category: "other", amount: 0, date: "" });

const linkCopied = ref(false);

async function copyTicketLink() {
  const url = `${window.location.origin}/billets/${props.id}`;
  try {
    await navigator.clipboard.writeText(url);
  } catch (e) {
    window.prompt("Copiez ce lien :", url);
    return;
  }
  linkCopied.value = true;
  setTimeout(() => (linkCopied.value = false), 2500);
}

async function loadEvent() {
  loading.value = true;
  try {
    const [eventRes, tasksRes, participantsRes, expensesRes] = await Promise.all([
      api.get(`/events/${props.id}/`),
      api.get("/events/tasks/", { params: { event: props.id } }),
      api.get("/events/participants/", { params: { event: props.id } }),
      api.get("/events/expenses/", { params: { event: props.id } }),
    ]);
    event.value = eventRes.data;
    tasks.value = tasksRes.data.results || tasksRes.data;
    participants.value = participantsRes.data.results || participantsRes.data;
    expenses.value = expensesRes.data.results || expensesRes.data;
  } finally {
    loading.value = false;
  }
}

async function addTask() {
  await api.post("/events/tasks/", { ...taskForm, event: props.id });
  Object.assign(taskForm, { title: "", due_date: "", priority: "medium" });
  showTaskForm.value = false;
  await loadEvent();
}

async function updateTaskStatus(task, status) {
  await api.patch(`/events/tasks/${task.id}/`, { status });
  await loadEvent();
}

async function addParticipant() {
  await api.post("/events/participants/", { ...participantForm, event: props.id });
  Object.assign(participantForm, { full_name: "", email: "" });
  showParticipantForm.value = false;
  await loadEvent();
}

async function addExpense() {
  await api.post("/events/expenses/", { ...expenseForm, event: props.id });
  Object.assign(expenseForm, { label: "", category: "other", amount: 0, date: "" });
  showExpenseForm.value = false;
  await loadEvent();
}

onMounted(loadEvent);
</script>

<template>
  <div v-if="event">
    <div class="ie-event-banner ie-card" v-if="event.photo">
      <img :src="event.photo" :alt="event.title" class="ie-zoomable" @click="lightbox.open(event.photo, event.title)" />
    </div>

    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-week" style="color: var(--ie-red); margin-right: 8px;"></i>{{ event.title }}</h1>
        <p class="ie-page-subtitle">{{ event.description || "Aucune description." }}</p>
      </div>
      <div class="ie-page-header-actions">
        <button
          v-if="event.is_public && event.status === 'published'"
          class="ie-btn ie-btn-ghost"
          @click="copyTicketLink"
        >
          <i :class="linkCopied ? 'fa-solid fa-check' : 'fa-solid fa-link'"></i> {{ linkCopied ? "Lien copié !" : "Lien direct billetterie" }}
        </button>
        <span v-else class="ie-ticket-link-hint" title="L'événement doit être public et publié pour générer un lien de billetterie partageable.">
          <i class="fa-solid fa-circle-info"></i> Lien billetterie disponible une fois l'événement public et publié
        </span>
      </div>
    </div>

    <div class="ie-kpi-grid">
      <div class="ie-card" style="padding: 16px;">
        <b style="display:block; font-size: 20px; color: var(--ie-navy);">{{ Number(event.budget_total).toLocaleString('fr-FR') }} XAF</b>
        <span style="font-size:12px; color: var(--ie-muted);">Budget total</span>
      </div>
      <div class="ie-card" style="padding: 16px;">
        <b style="display:block; font-size: 20px; color: var(--ie-navy);">{{ Number(event.remaining_budget).toLocaleString('fr-FR') }} XAF</b>
        <span style="font-size:12px; color: var(--ie-muted);">Budget restant</span>
      </div>
      <div class="ie-card" style="padding: 16px;">
        <b style="display:block; font-size: 20px; color: var(--ie-navy);">{{ event.participants_count }}</b>
        <span style="font-size:12px; color: var(--ie-muted);">Participants</span>
      </div>
      <div class="ie-card" style="padding: 16px;">
        <b style="display:block; font-size: 20px; color: var(--ie-navy);">{{ event.progress_percent }}%</b>
        <span style="font-size:12px; color: var(--ie-muted);">Avancement des tâches</span>
      </div>
    </div>

    <!-- Tâches -->
    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-list-check"></i>Tâches</h2>
        <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="showTaskForm = !showTaskForm">
          <i class="fa-solid" :class="showTaskForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showTaskForm ? "Annuler" : "Ajouter" }}
        </button>
      </div>
      <div v-if="showTaskForm" class="ie-card-body" style="border-bottom: 1px solid var(--ie-line);">
        <form class="ie-form-row" style="align-items: end;" @submit.prevent="addTask">
          <div>
            <label class="ie-label">Titre</label>
            <input v-model="taskForm.title" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Échéance</label>
            <input v-model="taskForm.due_date" type="date" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Priorité</label>
            <select v-model="taskForm.priority" class="ie-select">
              <option value="low">Basse</option><option value="medium">Moyenne</option><option value="high">Haute</option>
            </select>
          </div>
          <button class="ie-btn ie-btn-primary" type="submit">Ajouter</button>
        </form>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="tasks.length">
        <table class="ie-table">
          <thead><tr><th>Titre</th><th>Échéance</th><th>Priorité</th><th>Statut</th></tr></thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id">
              <td>{{ task.title }}</td>
              <td>{{ task.due_date || "—" }}</td>
              <td>{{ task.priority }}</td>
              <td>
                <select
                  class="ie-select"
                  style="width: auto; padding: 4px 8px; font-size: 12px;"
                  :value="task.status"
                  @change="updateTaskStatus(task, $event.target.value)"
                >
                  <option v-for="(label, value) in TASK_STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-list-check" text="Aucune tâche pour cet événement." />
    </div>

    <!-- Participants -->
    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-user-group"></i>Participants</h2>
        <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="showParticipantForm = !showParticipantForm">
          <i class="fa-solid" :class="showParticipantForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showParticipantForm ? "Annuler" : "Ajouter" }}
        </button>
      </div>
      <div v-if="showParticipantForm" class="ie-card-body" style="border-bottom: 1px solid var(--ie-line);">
        <form class="ie-form-row" style="align-items: end;" @submit.prevent="addParticipant">
          <div>
            <label class="ie-label">Nom complet</label>
            <input v-model="participantForm.full_name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Email</label>
            <input v-model="participantForm.email" type="email" class="ie-input" />
          </div>
          <button class="ie-btn ie-btn-primary" type="submit">Ajouter</button>
        </form>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="participants.length">
        <table class="ie-table">
          <thead><tr><th>Nom</th><th>Email</th><th>Statut</th></tr></thead>
          <tbody>
            <tr v-for="p in participants" :key="p.id">
              <td>{{ p.full_name || "—" }}</td>
              <td>{{ p.email || "—" }}</td>
              <td><span class="ie-badge" :class="p.checked_in ? 'ie-badge-success' : 'ie-badge-neutral'">{{ p.checked_in ? "Présent" : "Inscrit" }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-user-group" text="Aucun participant inscrit." />
    </div>

    <!-- Dépenses -->
    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-sack-dollar"></i>Dépenses</h2>
        <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="showExpenseForm = !showExpenseForm">
          <i class="fa-solid" :class="showExpenseForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showExpenseForm ? "Annuler" : "Ajouter" }}
        </button>
      </div>
      <div v-if="showExpenseForm" class="ie-card-body" style="border-bottom: 1px solid var(--ie-line);">
        <form class="ie-form-row" style="align-items: end;" @submit.prevent="addExpense">
          <div>
            <label class="ie-label">Libellé</label>
            <input v-model="expenseForm.label" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="expenseForm.category" class="ie-select">
              <option value="venue">Salle</option><option value="provider">Prestataire</option>
              <option value="equipment">Matériel</option><option value="other">Autre</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Montant (XAF)</label>
            <input v-model.number="expenseForm.amount" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Date</label>
            <input v-model="expenseForm.date" type="date" class="ie-input" required />
          </div>
          <button class="ie-btn ie-btn-primary" type="submit">Ajouter</button>
        </form>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="expenses.length">
        <table class="ie-table">
          <thead><tr><th>Libellé</th><th>Catégorie</th><th class="ie-num">Montant</th><th>Date</th></tr></thead>
          <tbody>
            <tr v-for="expense in expenses" :key="expense.id">
              <td>{{ expense.label }}</td>
              <td>{{ expense.category }}</td>
              <td class="ie-num">{{ Number(expense.amount).toLocaleString('fr-FR') }} XAF</td>
              <td>{{ expense.date }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-sack-dollar" text="Aucune dépense enregistrée." />
    </div>
  </div>
  <div v-else-if="loading" class="ie-skeleton" style="height: 200px;"></div>
</template>

<style scoped>
.ie-event-banner { overflow: hidden; margin-bottom: 20px; height: 220px; }
.ie-event-banner img { width: 100%; height: 100%; object-fit: cover; }
.ie-ticket-link-hint { font-size: 12px; color: var(--ie-muted); max-width: 220px; text-align: right; display: inline-flex; align-items: center; gap: 6px; }
.ie-ticket-link-hint i { color: var(--ie-muted); flex-shrink: 0; }
</style>

