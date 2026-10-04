<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const ROLES = [
  { value: "admin", label: "Administrateur" },
  { value: "client", label: "Client" },
  { value: "organizer", label: "Organisateur" },
  { value: "participant", label: "Participant" },
  { value: "employee", label: "Employé" },
];

const users = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const search = ref("");

const emptyForm = { username: "", email: "", first_name: "", last_name: "", role: "participant", phone: "", password: "", is_active: true };
const form = reactive({ ...emptyForm });

function roleLabel(value) {
  return ROLES.find((r) => r.value === value)?.label || value;
}

async function loadUsers() {
  loading.value = true;
  try {
    const { data } = await api.get("/auth/users/", { params: search.value ? { search: search.value } : {} });
    users.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  showForm.value = true;
}

function startEdit(user) {
  Object.assign(form, { ...user, password: "" });
  editingId.value = user.id;
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  const payload = { ...form };
  if (!payload.password) delete payload.password;
  try {
    if (editingId.value) {
      await api.patch(`/auth/users/${editingId.value}/`, payload);
    } else {
      await api.post("/auth/users/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Utilisateur enregistré.");
    await loadUsers();
  } catch (e) {
    const errors = e?.response?.data?.errors;
    errorMessage.value = e?.response?.data?.detail || (errors ? Object.values(errors).flat().join(" ") : "Impossible d'enregistrer ce compte.");
  } finally {
    submitting.value = false;
  }
}

async function toggleActive(user) {
  await api.patch(`/auth/users/${user.id}/`, { is_active: !user.is_active });
  await loadUsers();
}

const remindingId = ref(null);
const reminderSent = ref(null);

async function remindUser(user) {
  remindingId.value = user.id;
  try {
    await api.post(`/auth/users/${user.id}/remind/`);
    reminderSent.value = user.id;
    setTimeout(() => {
      if (reminderSent.value === user.id) reminderSent.value = null;
    }, 3000);
  } finally {
    remindingId.value = null;
  }
}

onMounted(() => {
  loadUsers();
  setInterval(loadUsers, 30000);
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-users" style="color: var(--ie-red); margin-right: 8px;"></i>Utilisateurs</h1>
        <p class="ie-page-subtitle">Comptes, rôles et accès à la plateforme.</p>
      </div>
      <div class="ie-page-header-actions">
        <input v-model="search" class="ie-input" placeholder="Rechercher…" style="width:220px;" @keyup.enter="loadUsers" />
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvel utilisateur" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Identifiant</label>
            <input v-model="form.username" class="ie-input" required autocomplete="username" />
          </div>
          <div>
            <label class="ie-label">Email</label>
            <input v-model="form.email" type="email" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prénom</label>
            <input v-model="form.first_name" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.last_name" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Rôle</label>
            <select v-model="form.role" class="ie-select">
              <option v-for="r in ROLES" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Téléphone</label>
            <input v-model="form.phone" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">
          Mot de passe {{ editingId ? "(laisser vide pour ne pas changer)" : "" }}
        </label>
        <input v-model="form.password" type="password" class="ie-input" :required="!editingId" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Compte actif
        </label>
        <p v-if="errorMessage" style="color: var(--ie-red); font-size: 13px; margin-top: 10px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="users.length">
        <table class="ie-table">
          <thead>
            <tr><th>Nom</th><th>Identifiant</th><th>Email</th><th>Rôle</th><th>En ligne</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td><strong>{{ (user.first_name + " " + user.last_name).trim() || "—" }}</strong></td>
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
              <td><span class="ie-badge ie-badge-neutral">{{ roleLabel(user.role) }}</span></td>
              <td>
                <span class="ie-online-dot" :class="{ online: user.is_online }"></span>
                {{ user.is_online ? "En ligne" : "Hors ligne" }}
              </td>
              <td>
                <span class="ie-badge" :class="user.is_active ? 'ie-badge-success' : 'ie-badge-danger'">
                  {{ user.is_active ? "Actif" : "Désactivé" }}
                </span>
              </td>
              <td class="ie-table-actions">
                <button
                  class="ie-btn ie-btn-secondary ie-btn-sm"
                  :disabled="remindingId === user.id"
                  @click="remindUser(user)"
                >
                  <i class="fa-solid" :class="reminderSent === user.id ? 'fa-check' : 'fa-bell'"></i>
                  {{ reminderSent === user.id ? "Envoyé" : "Relancer" }}
                </button>
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(user)">Modifier</button>
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="toggleActive(user)">
                  {{ user.is_active ? "Désactiver" : "Activer" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-users" text="Aucun utilisateur trouvé." />
    </div>
  </div>
</template>

<style scoped>
.ie-online-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 999px;
  background: #c7cbd1; margin-right: 6px;
}
.ie-online-dot.online { background: var(--ie-success); box-shadow: 0 0 0 3px var(--ie-success-soft); }
</style>
