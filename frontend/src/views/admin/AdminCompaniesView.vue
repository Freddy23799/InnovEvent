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

const companies = ref([]);
const loading = ref(true);
const saving = ref({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/companies/");
    companies.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function updateStatus(company, status) {
  saving.value[company.id] = true;
  try {
    const { data } = await api.patch(`/companies/${company.id}/verify/`, { verification_status: status });
    Object.assign(company, data);
    toast.success("Statut de vérification mis à jour.");
  } finally {
    saving.value[company.id] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-building" style="color: var(--ie-red); margin-right: 8px;"></i>Entreprises</h1>
        <p class="ie-page-subtitle">Comptes « Entreprise » inscrits sur la plateforme — vérification des documents justificatifs.</p>
      </div>
    </div>

    <SkeletonTable v-if="loading" />
    <div v-else-if="companies.length" class="ie-card">
      <div class="ie-table-wrap">
        <table class="ie-table">
          <thead>
            <tr><th>Raison sociale</th><th>Représentant</th><th>RCCM / NIU</th><th>Documents</th><th>Statut</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in companies" :key="c.id">
              <td>
                <strong>{{ c.raison_sociale }}</strong>
                <p class="ie-field-hint" style="margin: 2px 0 0;">{{ c.activite || "—" }} · {{ c.adresse || "—" }}</p>
              </td>
              <td>{{ c.representant || "—" }}<p class="ie-field-hint" style="margin: 2px 0 0;">{{ c.phone }} · {{ c.email }}</p></td>
              <td>{{ c.rccm || "—" }}<br />{{ c.niu || "—" }}</td>
              <td>
                <a v-for="d in c.documents" :key="d.id" :href="d.file" target="_blank" rel="noopener" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin: 2px;">
                  <i class="fa-solid fa-file-lines"></i> {{ d.label || "Document" }}
                </a>
                <span v-if="!c.documents.length" class="ie-field-hint">Aucun</span>
              </td>
              <td>
                <select
                  class="ie-select" style="font-size: 12.5px; padding: 4px 8px;" :value="c.verification_status" :disabled="saving[c.id]"
                  @change="updateStatus(c, $event.target.value)"
                >
                  <option v-for="s in VERIFICATION_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <EmptyState v-else icon="fa-solid fa-building" text="Aucune entreprise inscrite pour le moment." />
  </div>
</template>
