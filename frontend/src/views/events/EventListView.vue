<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const lightbox = useLightboxStore();
const auth = useAuthStore();
const toast = useToastStore();
const canPublish = computed(() => auth.role === "admin" || auth.role === "organizer");

const STATUS_LABELS = { draft: "Brouillon", published: "Publié", ongoing: "En cours", completed: "Terminé", cancelled: "Annulé" };
const STATUS_BADGE = { draft: "ie-badge-neutral", published: "ie-badge-success", ongoing: "ie-badge-warning", completed: "ie-badge-neutral", cancelled: "ie-badge-danger" };

const events = ref([]);
const venues = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = { title: "", description: "", venue: "", start_date: "", end_date: "", budget_total: 0, status: "draft", is_public: false };
const form = reactive({ ...emptyForm });
const downloadingReport = ref(false);

async function downloadReport() {
  downloadingReport.value = true;
  try {
    const response = await api.get("/events/report/", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "rapport-evenements.pdf";
    link.click();
    window.URL.revokeObjectURL(url);
  } finally {
    downloadingReport.value = false;
  }
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  if (!photoFile.value) return form;
  const payload = new FormData();
  Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ""));
  payload.append("photo", photoFile.value);
  return payload;
}

async function loadEvents() {
  loading.value = true;
  try {
    const [eventsRes, venuesRes] = await Promise.all([
      api.get("/events/"),
      api.get("/venues/", { params: { is_active: true } }),
    ]);
    events.value = eventsRes.data.results || eventsRes.data;
    venues.value = venuesRes.data.results || venuesRes.data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(event) {
  Object.assign(form, {
    title: event.title, description: event.description, venue: event.venue || "",
    start_date: event.start_date?.slice(0, 16), end_date: event.end_date?.slice(0, 16),
    budget_total: event.budget_total, status: event.status, is_public: event.is_public,
  });
  editingId.value = event.id;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/events/${editingId.value}/`, payload);
    } else {
      await api.post("/events/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Événement enregistré.");
    await loadEvents();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer l'événement.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadEvents);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-calendar-week" style="color: var(--ie-red); margin-right: 8px;"></i>Événements</h1>
        <p class="ie-page-subtitle">Créez et pilotez vos événements de bout en bout.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-secondary" @click="downloadReport" :disabled="downloadingReport">
          <i class="fa-solid fa-file-pdf"></i> {{ downloadingReport ? "Génération…" : "Rapport PDF" }}
        </button>
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvel événement" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Titre</label>
            <input v-model="form.title" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Lieu (salle)</label>
            <select v-model="form.venue" class="ie-select">
              <option value="">Non défini</option>
              <option v-for="v in venues" :key="v.id" :value="v.id">{{ v.name }} ({{ v.city }})</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Début</label>
            <input v-model="form.start_date" type="datetime-local" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Fin</label>
            <input v-model="form.end_date" type="datetime-local" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Statut</label>
            <select v-model="form.status" class="ie-select">
              <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Budget total (XAF)</label>
            <input v-model.number="form.budget_total" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <label class="ie-label" style="margin-top: 14px;">Photo de l'événement</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label v-if="canPublish" style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_public" type="checkbox" /> Événement public avec billetterie (visible sur le marché des événements)
        </label>
        <p v-else class="ie-field-hint">
          Un compte client crée un événement privé. Pour vendre des billets au public, un compte organisateur est nécessaire.
        </p>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer l'événement" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="events.length">
        <table class="ie-table">
          <thead>
            <tr>
              <th class="ie-num">No</th><th>Photo</th><th>Nom</th><th>Date début</th><th>Date fin</th>
              <th>Lieu</th><th>Statut</th><th>Description</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(event, index) in events" :key="event.id">
              <td class="ie-num">{{ index + 1 }}</td>
              <td>
                <div class="ie-event-thumb">
                  <img v-if="event.photo" :src="event.photo" :alt="event.title" class="ie-zoomable" @click="lightbox.open(event.photo, event.title)" />
                  <i v-else class="fa-solid fa-calendar-week"></i>
                </div>
              </td>
              <td><strong>{{ event.title }}</strong></td>
              <td>{{ new Date(event.start_date).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) }}</td>
              <td>{{ new Date(event.end_date).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) }}</td>
              <td>{{ event.venue_name || "—" }}</td>
              <td><span class="ie-badge" :class="STATUS_BADGE[event.status] || 'ie-badge-neutral'">{{ STATUS_LABELS[event.status] || event.status }}</span></td>
              <td class="ie-event-desc">{{ event.description || "—" }}</td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(event)">Modifier</button>
                <router-link :to="{ name: 'event-detail', params: { id: event.id } }" class="ie-btn ie-btn-secondary ie-btn-sm">Détails</router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-calendar-week" text="Aucun événement pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-event-thumb {
  width: 44px; height: 44px; border-radius: 8px; overflow: hidden;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-event-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-event-thumb i { color: var(--ie-navy); opacity: 0.4; font-size: 15px; }
.ie-event-desc { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ie-muted); font-size: 12.5px; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 10px 0 0; }
</style>
