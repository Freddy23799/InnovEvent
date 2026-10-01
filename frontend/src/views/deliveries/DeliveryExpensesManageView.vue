<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const auth = useAuthStore();
const isAdmin = auth.role === "admin";

const CATEGORIES = [
  { value: "fuel", label: "Carburant" }, { value: "toll", label: "Péage" }, { value: "maintenance", label: "Entretien" },
  { value: "parking", label: "Stationnement" }, { value: "other", label: "Autre" },
];

const expenses = ref([]);
const carriers = ref([]);
const vehicles = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");

const emptyForm = { category: "fuel", amount: 0, description: "", expense_date: new Date().toISOString().slice(0, 10), carrier: "", vehicle: "" };
const form = reactive({ ...emptyForm });

async function loadData() {
  loading.value = true;
  try {
    const [expensesRes, carriersRes, vehiclesRes] = await Promise.all([
      api.get("/deliveries/expenses/"), api.get("/deliveries/carriers/"), api.get("/deliveries/vehicles/"),
    ]);
    expenses.value = expensesRes.data.results || expensesRes.data;
    carriers.value = carriersRes.data.results || carriersRes.data;
    vehicles.value = vehiclesRes.data.results || vehiclesRes.data;
  } finally {
    loading.value = false;
  }
}

const totalAmount = computed(() => expenses.value.reduce((sum, e) => sum + Number(e.amount), 0));

function startCreate() {
  Object.assign(form, emptyForm);
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = { ...form, carrier: form.carrier || null, vehicle: form.vehicle || null };
    await api.post("/deliveries/expenses/", payload);
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
  if (!confirm("Supprimer cette dépense ?")) return;
  await api.delete(`/deliveries/expenses/${expense.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-receipt" style="color: var(--ie-red); margin-right: 8px;"></i>Dépenses transport</h1>
        <p class="ie-page-subtitle">Carburant, péages, entretien... rattachés à un véhicule, un transporteur ou une livraison.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle dépense" }}
        </button>
      </div>
    </div>

    <div class="ie-kpi-grid" style="margin-bottom: 20px;">
      <div class="ie-card ie-kpi"><b>{{ expenses.length }}</b><span>Dépenses enregistrées</span></div>
      <div class="ie-card ie-kpi"><b>{{ totalAmount.toLocaleString('fr-FR') }} XAF</b><span>Total cumulé</span></div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select">
              <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Montant (XAF)</label>
            <input v-model.number="form.amount" type="number" min="0" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div v-if="isAdmin">
            <label class="ie-label">Transporteur</label>
            <select v-model="form.carrier" class="ie-select">
              <option value="">—</option>
              <option v-for="c in carriers" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Véhicule</label>
            <select v-model="form.vehicle" class="ie-select">
              <option value="">—</option>
              <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Date</label>
            <input v-model="form.expense_date" type="date" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Description</label>
            <input v-model="form.description" class="ie-input" />
          </div>
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="expenses.length">
        <table class="ie-table">
          <thead>
            <tr><th>Date</th><th>Catégorie</th><th>Description</th><th>Transporteur</th><th>Véhicule</th><th class="ie-num">Montant</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="e in expenses" :key="e.id">
              <td>{{ e.expense_date }}</td>
              <td>{{ e.category_display }}</td>
              <td>{{ e.description || "—" }}</td>
              <td>{{ e.carrier_name || "—" }}</td>
              <td>{{ e.vehicle_plate || "—" }}</td>
              <td class="ie-num">{{ Number(e.amount).toLocaleString('fr-FR') }} XAF</td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteExpense(e)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-receipt" text="Aucune dépense transport enregistrée pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-kpi { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.ie-kpi b { font-size: 22px; color: var(--ie-navy); }
.ie-kpi span { font-size: 12px; color: var(--ie-muted); }
</style>
