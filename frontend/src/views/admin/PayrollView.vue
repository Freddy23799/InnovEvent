<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const payslips = ref([]);
const employees = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");

const now = new Date();
const emptyForm = {
  employee: "", period_month: now.getMonth() + 1, period_year: now.getFullYear(),
  base_salary: 0, bonuses: 0, allowances: 0, deductions: 0,
};
const form = reactive({ ...emptyForm });

async function loadData() {
  loading.value = true;
  try {
    const [payslipsRes, employeesRes] = await Promise.all([
      api.get("/payroll/"),
      api.get("/employees/"),
    ]);
    payslips.value = payslipsRes.data.results || payslipsRes.data;
    employees.value = employeesRes.data.results || employeesRes.data;
  } finally {
    loading.value = false;
  }
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    await api.post("/payroll/", form);
    showForm.value = false;
    toast.success("Bulletin de paie enregistré.");
    Object.assign(form, emptyForm);
    await loadData();
  } catch (e) {
    const errors = e?.response?.data?.errors;
    errorMessage.value = errors ? Object.values(errors).flat().join(" ") : "Impossible de générer cette fiche de paie.";
  } finally {
    submitting.value = false;
  }
}

async function downloadPayslip(payslip) {
  const response = await api.get(`/payroll/${payslip.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `paie-${payslip.employee_name}-${payslip.period_month}-${payslip.period_year}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-money-check-dollar" style="color: var(--ie-red); margin-right: 8px;"></i>Paie</h1>
        <p class="ie-page-subtitle">Génération et historique des fiches de paie mensuelles.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm = !showForm">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle fiche de paie" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Employé</label>
            <select v-model="form.employee" class="ie-select" required>
              <option value="" disabled>Choisir un employé</option>
              <option v-for="e in employees" :key="e.id" :value="e.id">{{ e.first_name }} {{ e.last_name }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Salaire de base (XAF)</label>
            <input v-model.number="form.base_salary" type="number" min="0" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Mois</label>
            <input v-model.number="form.period_month" type="number" min="1" max="12" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Année</label>
            <input v-model.number="form.period_year" type="number" min="2020" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Primes (XAF)</label>
            <input v-model.number="form.bonuses" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Indemnités (XAF)</label>
            <input v-model.number="form.allowances" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Retenues (XAF)</label>
        <input v-model.number="form.deductions" type="number" min="0" class="ie-input" />
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Génération…" : "Générer la fiche" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="payslips.length">
        <table class="ie-table">
          <thead>
            <tr><th>Employé</th><th>Période</th><th class="ie-num">Salaire de base</th><th class="ie-num">Net à payer</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="payslip in payslips" :key="payslip.id">
              <td><strong>{{ payslip.employee_name }}</strong></td>
              <td>{{ String(payslip.period_month).padStart(2, '0') }}/{{ payslip.period_year }}</td>
              <td class="ie-num">{{ Number(payslip.base_salary).toLocaleString('fr-FR') }} XAF</td>
              <td class="ie-num"><strong>{{ Number(payslip.net_pay).toLocaleString('fr-FR') }} XAF</strong></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="downloadPayslip(payslip)">
                  <i class="fa-solid fa-download"></i> PDF
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-money-check-dollar" text="Aucune fiche de paie générée." />
    </div>
  </div>
</template>
