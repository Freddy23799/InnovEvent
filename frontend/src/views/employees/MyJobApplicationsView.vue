<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const STATUS_META = {
  pending: { label: "En attente", badge: "ie-badge-neutral" },
  reviewed: { label: "Examinée", badge: "ie-badge-warning" },
  accepted: { label: "Acceptée", badge: "ie-badge-success" },
  rejected: { label: "Refusée", badge: "ie-badge-danger" },
};

const applications = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const cvFile = ref(null);

const form = reactive({
  full_name: "", email: "", phone: "", desired_position: "", motivation: "",
});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/employees/job-applications/");
    applications.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function onCvChange(event) {
  cvFile.value = event.target.files[0] || null;
}

function resetForm() {
  form.full_name = "";
  form.email = "";
  form.phone = "";
  form.desired_position = "";
  form.motivation = "";
  cvFile.value = null;
}

async function submitApplication() {
  if (!cvFile.value) {
    toast.error("Veuillez joindre votre CV.");
    return;
  }
  submitting.value = true;
  try {
    const payload = new FormData();
    Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ""));
    payload.append("cv_file", cvFile.value);
    await api.post("/employees/job-applications/", payload);
    toast.success("Votre candidature a été envoyée.");
    resetForm();
    showForm.value = false;
    await loadData();
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d'envoyer votre candidature.");
  } finally {
    submitting.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-briefcase" style="color: var(--ie-red); margin-right: 8px;"></i>Rejoindre l'équipe</h1>
        <p class="ie-page-subtitle">Envoyez votre candidature (CV + informations) pour postuler à un poste chez InnovEvent-GS.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm = !showForm">
          <i class="fa-solid fa-paper-plane"></i> {{ showForm ? "Annuler" : "Nouvelle candidature" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <h3>Nouvelle candidature</h3>
      <div class="ie-form-row">
        <div>
          <label class="ie-label">Nom complet</label>
          <input v-model="form.full_name" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Poste souhaité</label>
          <input v-model="form.desired_position" class="ie-input" />
        </div>
      </div>
      <div class="ie-form-row" style="margin-top: 10px;">
        <div>
          <label class="ie-label">Email</label>
          <input v-model="form.email" type="email" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Téléphone</label>
          <input v-model="form.phone" class="ie-input" />
        </div>
      </div>
      <label class="ie-label" style="margin-top: 10px;">Lettre de motivation (optionnel)</label>
      <textarea v-model="form.motivation" class="ie-input" rows="4"></textarea>

      <label class="ie-label" style="margin-top: 10px;">CV <span class="ie-required">*</span></label>
      <input type="file" accept=".pdf,.doc,.docx,image/*" class="ie-input" @change="onCvChange" />
      <p class="ie-field-hint">Formats acceptés : PDF, Word ou image.</p>

      <button class="ie-btn ie-btn-primary" style="margin-top: 16px;" :disabled="submitting" @click="submitApplication">
        {{ submitting ? "Envoi…" : "Envoyer ma candidature" }}
      </button>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 160px;"></div>

    <div v-else-if="applications.length" style="display: flex; flex-direction: column; gap: 14px;">
      <div v-for="a in applications" :key="a.id" class="ie-card ie-card-body">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;">
          <div>
            <strong style="font-size: 14.5px; color: var(--ie-navy);">{{ a.desired_position }}</strong>
            <p style="margin: 2px 0 0; font-size: 12px; color: var(--ie-muted);">
              Envoyée le {{ new Date(a.created_at).toLocaleDateString('fr-FR') }}
            </p>
          </div>
          <span class="ie-badge" :class="STATUS_META[a.status]?.badge">{{ STATUS_META[a.status]?.label || a.status }}</span>
        </div>
        <p v-if="a.motivation" style="margin: 10px 0 0; font-size: 12.5px; color: var(--ie-muted); line-height: 1.5;">{{ a.motivation }}</p>
        <p v-if="a.reviewer_notes" style="margin: 8px 0 0; font-size: 12.5px; color: var(--ie-ink);">
          <strong>Retour de l'administration :</strong> {{ a.reviewer_notes }}
        </p>
        <a :href="a.cv_file" target="_blank" rel="noopener" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 10px;">
          <i class="fa-solid fa-file-lines"></i> Voir mon CV
        </a>
      </div>
    </div>

    <EmptyState v-else icon="fa-solid fa-briefcase" text="Vous n'avez envoyé aucune candidature pour le moment." />
  </div>
</template>

<style scoped>
.ie-required { color: var(--ie-red); }
.ie-field-hint { margin: 6px 0 0; font-size: 11.5px; color: var(--ie-muted); }
</style>
