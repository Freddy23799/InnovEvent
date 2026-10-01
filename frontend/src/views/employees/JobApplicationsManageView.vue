<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import KpiCard from "../../components/KpiCard.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const STATUS_META = {
  pending: { label: "En attente", badge: "ie-badge-neutral" },
  reviewed: { label: "Examinée", badge: "ie-badge-warning" },
  accepted: { label: "Acceptée", badge: "ie-badge-success" },
  rejected: { label: "Refusée", badge: "ie-badge-danger" },
};
const STATUS_OPTIONS = [
  { value: "pending", label: "En attente" },
  { value: "reviewed", label: "Examinée" },
  { value: "accepted", label: "Acceptée" },
  { value: "rejected", label: "Refusée" },
];

const applications = ref([]);
const loading = ref(true);
const statusFilter = ref("");
const search = ref("");
const savingId = ref(null);
const notesDraft = reactive({});

const filteredApplications = computed(() => {
  let result = applications.value;
  if (statusFilter.value) result = result.filter((a) => a.status === statusFilter.value);
  const query = search.value.trim().toLowerCase();
  if (query) {
    result = result.filter((a) =>
      (a.full_name || "").toLowerCase().includes(query) || (a.desired_position || "").toLowerCase().includes(query)
    );
  }
  return result;
});

const stats = computed(() => ({
  total: applications.value.length,
  pending: applications.value.filter((a) => a.status === "pending").length,
  accepted: applications.value.filter((a) => a.status === "accepted").length,
}));

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/employees/job-applications/");
    applications.value = data.results || data;
    applications.value.forEach((a) => { notesDraft[a.id] = a.reviewer_notes || ""; });
  } finally {
    loading.value = false;
  }
}

async function review(application, status) {
  savingId.value = application.id;
  try {
    const { data } = await api.post(`/employees/job-applications/${application.id}/review/`, {
      status, reviewer_notes: notesDraft[application.id] || "",
    });
    Object.assign(application, data);
    toast.success("Candidature mise à jour.");
  } catch (e) {
    toast.error("Impossible de mettre à jour cette candidature.");
  } finally {
    savingId.value = null;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-briefcase" style="color: var(--ie-red); margin-right: 8px;"></i>Candidatures</h1>
        <p class="ie-page-subtitle">Candidatures reçues depuis l'espace client (CV joint), à examiner et suivre.</p>
      </div>
    </div>

    <div class="ie-kpi-grid" style="margin-bottom: 20px;">
      <KpiCard label="Total" :value="stats.total" icon="fa-solid fa-briefcase" />
      <KpiCard label="En attente" :value="stats.pending" icon="fa-solid fa-hourglass-half" />
      <KpiCard label="Acceptées" :value="stats.accepted" icon="fa-solid fa-check" />
    </div>

    <div style="display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap;">
      <input v-model="search" class="ie-input" placeholder="Rechercher un candidat ou un poste..." style="max-width: 280px;" />
      <select v-model="statusFilter" class="ie-select" style="max-width: 220px;">
        <option value="">Tous les statuts</option>
        <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
    </div>

    <SkeletonTable v-if="loading" :columns="5" />

    <div v-else-if="filteredApplications.length" style="display: flex; flex-direction: column; gap: 14px;">
      <div v-for="a in filteredApplications" :key="a.id" class="ie-card ie-card-body">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;">
          <div>
            <strong style="font-size: 14.5px; color: var(--ie-navy);">{{ a.full_name }}</strong>
            <p style="margin: 2px 0 0; font-size: 12.5px; color: var(--ie-muted);">
              {{ a.desired_position }} · {{ a.email }} · {{ a.phone }}
            </p>
            <p style="margin: 2px 0 0; font-size: 11.5px; color: var(--ie-muted);">
              Envoyée le {{ new Date(a.created_at).toLocaleDateString('fr-FR') }}
            </p>
          </div>
          <span class="ie-badge" :class="STATUS_META[a.status]?.badge">{{ STATUS_META[a.status]?.label || a.status }}</span>
        </div>

        <p v-if="a.motivation" style="margin: 10px 0 0; font-size: 12.5px; color: var(--ie-ink); line-height: 1.5;">
          <strong>Motivation :</strong> {{ a.motivation }}
        </p>

        <a :href="a.cv_file" target="_blank" rel="noopener" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 10px;">
          <i class="fa-solid fa-file-lines"></i> Télécharger le CV
        </a>

        <label class="ie-label" style="margin-top: 12px;">Notes d'examen</label>
        <textarea v-model="notesDraft[a.id]" class="ie-input" rows="2" placeholder="Notes internes (visibles par le candidat)..."></textarea>

        <div style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
          <button class="ie-btn ie-btn-ghost ie-btn-sm" :disabled="savingId === a.id" @click="review(a, 'reviewed')">
            Marquer comme examinée
          </button>
          <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="savingId === a.id" @click="review(a, 'accepted')">
            <i class="fa-solid fa-check"></i> Accepter
          </button>
          <button class="ie-btn ie-btn-danger ie-btn-sm" :disabled="savingId === a.id" @click="review(a, 'rejected')">
            <i class="fa-solid fa-xmark"></i> Refuser
          </button>
        </div>
      </div>
    </div>

    <EmptyState v-else icon="fa-solid fa-briefcase" text="Aucune candidature pour le moment." />
  </div>
</template>
