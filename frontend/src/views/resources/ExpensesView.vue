<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const CATEGORY_LABELS = {
  purchase: "Achat de matériel",
  maintenance: "Maintenance / réparation",
  logistics: "Logistique / transport",
  utilities: "Charges (eau, électricité, internet)",
  other: "Autre",
};

const expenses = ref([]);
const equipmentList = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const categoryFilter = ref("");

const emptyForm = { category: "purchase", label: "", amount: 0, equipment: "", incurred_at: "", notes: "" };
const form = reactive({ ...emptyForm });

const totalAmount = computed(() => expenses.value.reduce((sum, e) => sum + Number(e.amount), 0));

async function loadData() {
  loading.value = true;
  try {
    const params = {};
    if (categoryFilter.value) params.category = categoryFilter.value;
    const [expensesRes, equipmentRes] = await Promise.all([
      api.get("/equipment/expenses/", { params }),
      api.get("/equipment/", { params: { is_active: true } }),
    ]);
    expenses.value = expensesRes.data.results || expensesRes.data;
    equipmentList.value = equipmentRes.data.results || equipmentRes.data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm, { incurred_at: new Date().toISOString().slice(0, 10) });
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = { ...form, equipment: form.equipment || null };
    await api.post("/equipment/expenses/", payload);
    showForm.value = false;
    toast.success("Dépense enregistrée.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette dépense.";
  } finally {
    submitting.value = false;
  }
}

async function deleteExpense(expense) {
  if (!confirm(`Supprimer la dépense « ${expense.label} » ?`)) return;
  await api.delete(`/equipment/expenses/${expense.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-sack-dollar" style="color: var(--ie-red); margin-right: 8px;"></i>Dépenses</h1>
        <p class="ie-page-subtitle">Suivi des dépenses liées au matériel : achats, réparations, logistique.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle dépense" }}
        </button>
      </div>
    </div>

    <div class="ie-kpi-grid" style="margin-bottom: 20px;">
      <div class="ie-card" style="padding:16px;">
        <b class="ie-kpi-num">{{ Number(totalAmount).toLocaleString('fr-FR') }} XAF</b>
        <span>Total des dépenses affichées</span>
      </div>
      <div class="ie-card" style="padding:16px;">
        <b class="ie-kpi-num">{{ expenses.length }}</b>
        <span>Dépense(s) enregistrée(s)</span>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Libellé</label>
            <input v-model="form.label" class="ie-input" required placeholder="Ex: Achat de 10 chaises pliantes" />
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select">
              <option v-for="(label, value) in CATEGORY_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Montant (XAF)</label>
            <input v-model.number="form.amount" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Date</label>
            <input v-model="form.incurred_at" type="date" class="ie-input" required />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Matériel concerné (optionnel)</label>
        <select v-model="form.equipment" class="ie-select">
          <option value="">Aucun matériel spécifique</option>
          <option v-for="e in equipmentList" :key="e.id" :value="e.id">{{ e.name }}</option>
        </select>
        <label class="ie-label" style="margin-top: 14px;">Notes (optionnel)</label>
        <textarea v-model="form.notes" class="ie-input" rows="2"></textarea>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : "Enregistrer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-file-invoice-dollar"></i>Journal des dépenses</h2>
        <select v-model="categoryFilter" class="ie-select" style="width: 240px;" @change="loadData">
          <option value="">Toutes les catégories</option>
          <option v-for="(label, value) in CATEGORY_LABELS" :key="value" :value="value">{{ label }}</option>
        </select>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="expenses.length">
        <table class="ie-table">
          <thead>
            <tr><th>Date</th><th>Libellé</th><th>Catégorie</th><th>Matériel</th><th class="ie-num">Montant</th><th>Enregistré par</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="e in expenses" :key="e.id">
              <td>{{ new Date(e.incurred_at).toLocaleDateString('fr-FR') }}</td>
              <td><strong>{{ e.label }}</strong><div v-if="e.notes" style="font-size:11px; color: var(--ie-muted);">{{ e.notes }}</div></td>
              <td><span class="ie-badge ie-badge-neutral">{{ CATEGORY_LABELS[e.category] || e.category }}</span></td>
              <td>{{ e.equipment_name || "—" }}</td>
              <td class="ie-num"><strong>{{ Number(e.amount).toLocaleString('fr-FR') }} XAF</strong></td>
              <td>{{ e.recorded_by_name || "—" }}</td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteExpense(e)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-sack-dollar" text="Aucune dépense enregistrée." />
    </div>
  </div>
</template>

<style scoped>
.ie-kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.ie-kpi-num { display: block; font-size: 22px; color: var(--ie-navy); }
@media (max-width: 700px) { .ie-kpi-grid { grid-template-columns: 1fr; } }
</style>
