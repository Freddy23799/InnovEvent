<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import { ACTOR_CATEGORY_GROUPS, OTHER_CATEGORY_GROUP } from "../../data/actorCategories";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const MARKETPLACE_LABELS = { actors: "Marketplace des acteurs", interior_design: "Décoration & design intérieur" };
const CATEGORY_GROUPS = [...ACTOR_CATEGORY_GROUPS, OTHER_CATEGORY_GROUP];

const VERIFICATION_STATUSES = [
  { value: "not_verified", label: "Non vérifié" },
  { value: "profile_verified", label: "Profil vérifié" },
  { value: "identity_verified", label: "Identité vérifiée" },
  { value: "company_verified", label: "Entreprise vérifiée" },
  { value: "portfolio_verified", label: "Portfolio vérifié" },
  { value: "professional_partner", label: "Partenaire professionnel" },
];

const profiles = ref([]);
const loading = ref(true);
const saving = reactive({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/profiles/");
    profiles.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function toggleBadge(profile, field) {
  saving[profile.id] = true;
  try {
    const { data } = await api.patch(`/marketplace/profiles/${profile.id}/badges/`, { [field]: !profile[field] });
    Object.assign(profile, data);
  } finally {
    saving[profile.id] = false;
  }
}

async function updateVerificationStatus(profile, status) {
  saving[profile.id] = true;
  try {
    const { data } = await api.patch(`/marketplace/profiles/${profile.id}/badges/`, { verification_status: status });
    Object.assign(profile, data);
    toast.success("Statut de vérification mis à jour.");
  } finally {
    saving[profile.id] = false;
  }
}

// --- Ajout direct d'une prestation par l'administration ---------------------
const showForm = ref(false);
const ownerMode = ref("new"); // "new" | "existing"
const partnerUsers = ref([]);
const emptyForm = {
  marketplace_type: "actors", category: "", business_name: "", city: "", description: "",
  owner_user: "", new_owner_username: "", new_owner_email: "", new_owner_first_name: "", new_owner_last_name: "",
};
const form = reactive({ ...emptyForm });
const submitting = ref(false);
const errorMessage = ref("");
const lastCreated = ref(null);

async function loadPartnerUsers() {
  try {
    const { data } = await api.get("/auth/users/", { params: { role: "partner" } });
    partnerUsers.value = data.results || data;
  } catch {
    partnerUsers.value = [];
  }
}

function toggleForm() {
  showForm.value = !showForm.value;
  if (showForm.value) {
    Object.assign(form, emptyForm);
    errorMessage.value = "";
    lastCreated.value = null;
    loadPartnerUsers();
  }
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = {
      marketplace_type: form.marketplace_type, category: form.category,
      business_name: form.business_name, city: form.city, description: form.description,
    };
    if (ownerMode.value === "existing") {
      payload.owner_user = form.owner_user;
    } else {
      payload.new_owner_username = form.new_owner_username;
      payload.new_owner_email = form.new_owner_email;
      payload.new_owner_first_name = form.new_owner_first_name;
      payload.new_owner_last_name = form.new_owner_last_name;
    }
    const { data } = await api.post("/marketplace/profiles/admin-create/", payload);
    lastCreated.value = data;
    profiles.value.unshift(data);
    Object.assign(form, emptyForm);
    toast.success("Prestataire enregistré.");
  } catch (e) {
    const detail = e?.response?.data?.detail;
    errorMessage.value = typeof detail === "object" ? Object.values(detail).flat().join(" ") : (detail || "Impossible de créer cette prestation.");
  } finally {
    submitting.value = false;
  }
}

const categoryLabel = computed(() => {
  for (const group of CATEGORY_GROUPS) {
    const found = group.items.find((i) => i.value === form.category);
    if (found) return found.label;
  }
  return "";
});

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-people-group" style="color: var(--ie-red); margin-right: 8px;"></i>Prestataires</h1>
        <p class="ie-page-subtitle">Ajoutez directement une prestation dans une catégorie, et accordez les badges de reconnaissance.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="toggleForm">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Ajouter un prestataire" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <div v-if="lastCreated" class="ie-alert ie-alert-success" style="margin-bottom: 14px;">
        <i class="fa-solid fa-circle-check"></i> « {{ lastCreated.business_name }} » créé et déjà abonné, visible immédiatement dans le Marketplace.
        <template v-if="lastCreated.generated_password">
          <br />Compte <strong>{{ lastCreated.owner_username }}</strong> — mot de passe généré : <code>{{ lastCreated.generated_password }}</code>
          <span class="ie-field-hint"> (à transmettre au prestataire — ne sera plus affiché ensuite)</span>
        </template>
      </div>

      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Marketplace</label>
            <select v-model="form.marketplace_type" class="ie-select">
              <option value="actors">Marketplace des acteurs</option>
              <option value="interior_design">Décoration & design intérieur</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select" required>
              <option value="" disabled>Choisir une catégorie…</option>
              <optgroup v-for="g in CATEGORY_GROUPS" :key="g.title" :label="g.title">
                <option v-for="c in g.items" :key="c.value" :value="c.value">{{ c.label }}</option>
              </optgroup>
            </select>
          </div>
        </div>
        <p v-if="categoryLabel" class="ie-field-hint" style="margin-top: 4px;">{{ categoryLabel }}</p>

        <label class="ie-label" style="margin-top: 14px;">Nom de l'entreprise / activité</label>
        <input v-model="form.business_name" class="ie-input" required placeholder="Ex : SnapBooth Cameroun" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Ville</label>
            <input v-model="form.city" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="2"></textarea>

        <label class="ie-label" style="margin-top: 18px;">Compte prestataire</label>
        <div class="ie-owner-mode-toggle">
          <button type="button" class="ie-btn ie-btn-sm" :class="ownerMode === 'new' ? 'ie-btn-primary' : 'ie-btn-ghost'" @click="ownerMode = 'new'">
            Créer un nouveau compte
          </button>
          <button type="button" class="ie-btn ie-btn-sm" :class="ownerMode === 'existing' ? 'ie-btn-primary' : 'ie-btn-ghost'" @click="ownerMode = 'existing'">
            Utiliser un compte existant
          </button>
        </div>

        <template v-if="ownerMode === 'new'">
          <div class="ie-form-row" style="margin-top: 10px;">
            <div>
              <label class="ie-label">Identifiant</label>
              <input v-model="form.new_owner_username" class="ie-input" required placeholder="Ex : presta_snapbooth" />
            </div>
            <div>
              <label class="ie-label">Email</label>
              <input v-model="form.new_owner_email" type="email" class="ie-input" />
            </div>
          </div>
          <div class="ie-form-row" style="margin-top: 10px;">
            <div>
              <label class="ie-label">Prénom</label>
              <input v-model="form.new_owner_first_name" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Nom</label>
              <input v-model="form.new_owner_last_name" class="ie-input" />
            </div>
          </div>
          <p class="ie-field-hint" style="margin-top: 6px;">Un mot de passe sera généré automatiquement et affiché une seule fois après création.</p>
        </template>
        <template v-else>
          <select v-model="form.owner_user" class="ie-select" style="margin-top: 10px;" required>
            <option value="" disabled>Choisir un compte prestataire…</option>
            <option v-for="u in partnerUsers" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
          </select>
          <p v-if="!partnerUsers.length" class="ie-field-hint" style="margin-top: 6px;">Aucun compte prestataire disponible — créez-en un nouveau plutôt.</p>
        </template>

        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 14px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Création…" : "Créer cette prestation" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div v-else-if="profiles.length" class="ie-table-wrap">
        <table class="ie-table">
          <thead>
            <tr>
              <th>Prestataire</th><th>Marketplace</th><th>Note</th>
              <th>Statut de vérification</th><th>★ Recommandé</th><th>🏆 Top</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in profiles" :key="p.id">
              <td>
                <strong>{{ p.business_name }}</strong>
                <p class="ie-field-hint" style="margin: 2px 0 0;">{{ p.category_display }} · {{ p.city }}</p>
              </td>
              <td>{{ MARKETPLACE_LABELS[p.marketplace_type] || p.marketplace_type }}</td>
              <td>{{ p.average_rating ? `${p.average_rating} ★ (${p.review_count})` : "—" }}</td>
              <td>
                <select
                  class="ie-select" style="font-size: 12.5px; padding: 4px 8px;" :value="p.verification_status" :disabled="saving[p.id]"
                  @change="updateVerificationStatus(p, $event.target.value)"
                >
                  <option v-for="s in VERIFICATION_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
              </td>
              <td>
                <label class="ie-badge-toggle">
                  <input type="checkbox" :checked="p.is_recommended" :disabled="saving[p.id]" @change="toggleBadge(p, 'is_recommended')" />
                </label>
              </td>
              <td>
                <label class="ie-badge-toggle">
                  <input type="checkbox" :checked="p.is_top" :disabled="saving[p.id]" @change="toggleBadge(p, 'is_top')" />
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-award" text="Aucun profil professionnel pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-badge-toggle input { width: 18px; height: 18px; cursor: pointer; }
.ie-owner-mode-toggle { display: flex; gap: 8px; margin-top: 6px; }
</style>
