<script setup>
import { onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const VERIFICATION_STATUSES = [
  { value: "not_verified", label: "Non vérifié" },
  { value: "profile_verified", label: "Profil vérifié" },
  { value: "identity_verified", label: "Identité vérifiée" },
  { value: "company_verified", label: "Entreprise vérifiée" },
  { value: "portfolio_verified", label: "Portfolio vérifié" },
  { value: "professional_partner", label: "Partenaire professionnel" },
];

const talents = ref([]);
const loading = ref(true);
const saving = ref({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/talents/");
    talents.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function updateStatus(talent, status) {
  saving.value[talent.id] = true;
  try {
    const { data } = await api.patch(`/talents/${talent.id}/verify/`, { verification_status: status });
    Object.assign(talent, data);
    toast.success("Statut de vérification mis à jour.");
  } finally {
    saving.value[talent.id] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-star" style="color: var(--ie-red); margin-right: 8px;"></i>Talents</h1>
        <p class="ie-page-subtitle">Profils « Talent » à la recherche d'une opportunité — annuaire visible sur la page d'accueil.</p>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <div v-else-if="talents.length" class="ie-card">
      <div class="ie-table-wrap">
        <table class="ie-table">
          <thead>
            <tr><th>Talent</th><th>Ville</th><th>Opportunité recherchée</th><th>Disponibilité</th><th>Statut</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in talents" :key="t.id">
              <td>
                <strong>{{ t.full_name }}</strong>
                <p class="ie-field-hint" style="margin: 2px 0 0;">{{ t.competences || "—" }}</p>
              </td>
              <td>{{ t.city || "—" }}</td>
              <td>{{ t.opportunity_type_display }}</td>
              <td>{{ t.disponibilite_display }}</td>
              <td>
                <select
                  class="ie-select" style="font-size: 12.5px; padding: 4px 8px;" :value="t.verification_status" :disabled="saving[t.id]"
                  @change="updateStatus(t, $event.target.value)"
                >
                  <option v-for="s in VERIFICATION_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <EmptyState v-else icon="fa-solid fa-star" text="Aucun profil talent pour le moment." />
  </div>
</template>
