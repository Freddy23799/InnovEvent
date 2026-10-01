<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const employees = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = { first_name: "", last_name: "", position: "", contact: "", hire_date: "", is_active: true };
const form = reactive({ ...emptyForm });

async function loadEmployees() {
  loading.value = true;
  try {
    const { data } = await api.get("/employees/");
    employees.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(employee) {
  Object.assign(form, employee);
  editingId.value = employee.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    if (editingId.value) {
      await api.patch(`/employees/${editingId.value}/`, form);
    } else {
      await api.post("/employees/", form);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Employé enregistré.");
    await loadEmployees();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cet employé.";
  } finally {
    submitting.value = false;
  }
}

async function toggleActive(employee) {
  await api.patch(`/employees/${employee.id}/`, { is_active: !employee.is_active });
  await loadEmployees();
}

onMounted(loadEmployees);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-users-gear" style="color: var(--ie-red); margin-right: 8px;"></i>Employés</h1>
        <p class="ie-page-subtitle">Personnel InnovEvent-GS et informations RH de base.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvel employé" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Prénom</label>
            <input v-model="form.first_name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.last_name" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Poste</label>
            <input v-model="form.position" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Contact</label>
            <input v-model="form.contact" class="ie-input" placeholder="Téléphone ou email" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Date d'entrée</label>
        <input v-model="form.hire_date" type="date" class="ie-input" required />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Employé actif
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="employees.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Poste</th><th>Contact</th><th>Date d'entrée</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="employee in employees" :key="employee.id">
              <td><strong>{{ employee.first_name }} {{ employee.last_name }}</strong></td>
              <td>{{ employee.position }}</td>
              <td>{{ employee.contact || "—" }}</td>
              <td>{{ employee.hire_date }}</td>
              <td><span class="ie-badge" :class="employee.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ employee.is_active ? "Actif" : "Inactif" }}</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(employee)">Modifier</button>
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="toggleActive(employee)">
                  {{ employee.is_active ? "Désactiver" : "Activer" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-users-gear" text="Aucun employé enregistré." />
    </div>
  </div>
</template>
