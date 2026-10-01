<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const tiers = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = { code: "", label: "", level: 0, description: "", is_default: false, order: 0 };
const form = reactive({ ...emptyForm });

// Tarification des formules de durée (1, 3, 6, 12 mois...) — même grille pour
// tous les marketplaces premium. Entièrement configurable ici : aucun prix
// n'est plus codé en dur côté serveur.
const plans = ref([]);
const plansLoading = ref(true);
const showPlanForm = ref(false);
const planSubmitting = ref(false);
const planErrorMessage = ref("");
const editingPlanId = ref(null);

const emptyPlanForm = { code: "", label: "", months: 1, duration_days: 30, price: 0, discount_percent: 0, order: 0, marketplace_type: null };
const marketplaceLabels = {
  talent_missions: "Missions pour talents",
  sale: "Marketplace vente",
  actors: "Marketplace des acteurs",
  interior_design: "Décoration & design intérieur",
  venues: "Salles de réception",
};
const planForm = reactive({ ...emptyPlanForm });

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/tiers/");
    tiers.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function loadPlans() {
  plansLoading.value = true;
  try {
    const { data } = await api.get("/marketplace/plans/");
    plans.value = data.results || data;
  } finally {
    plansLoading.value = false;
  }
}

function startCreatePlan() {
  Object.assign(planForm, emptyPlanForm);
  editingPlanId.value = null;
  planErrorMessage.value = "";
  showPlanForm.value = true;
}

function startEditPlan(plan) {
  Object.assign(planForm, plan);
  editingPlanId.value = plan.id;
  planErrorMessage.value = "";
  showPlanForm.value = true;
}

async function submitPlanForm() {
  planErrorMessage.value = "";
  planSubmitting.value = true;
  try {
    if (editingPlanId.value) {
      await api.patch(`/marketplace/plans/${editingPlanId.value}/`, planForm);
    } else {
      await api.post("/marketplace/plans/", planForm);
    }
    showPlanForm.value = false;
    toast.success(editingPlanId.value ? "Modifications enregistrées." : "Formule tarifaire enregistrée.");
    await loadPlans();
  } catch (e) {
    planErrorMessage.value = e?.response?.data?.code?.[0] || e?.response?.data?.detail || "Impossible d'enregistrer cette formule.";
  } finally {
    planSubmitting.value = false;
  }
}

async function deletePlan(plan) {
  if (!confirm(`Supprimer la formule « ${plan.label} » ? Elle ne sera plus proposée au moment de l'abonnement.`)) return;
  await api.delete(`/marketplace/plans/${plan.id}/`);
  await loadPlans();
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(tier) {
  Object.assign(form, tier);
  editingId.value = tier.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    if (editingId.value) {
      await api.patch(`/marketplace/tiers/${editingId.value}/`, form);
    } else {
      await api.post("/marketplace/tiers/", form);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Palier enregistré.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.code?.[0] || e?.response?.data?.detail || "Impossible d'enregistrer ce palier.";
  } finally {
    submitting.value = false;
  }
}

async function deleteTier(tier) {
  if (!confirm(`Supprimer le palier « ${tier.label} » ? Les fonctionnalités qui l'exigent comme palier minimum n'en exigeront plus.`)) return;
  await api.delete(`/marketplace/tiers/${tier.id}/`);
  await loadData();
}

onMounted(() => {
  loadData();
  loadPlans();
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-layer-group" style="color: var(--ie-red); margin-right: 8px;"></i>Paliers d'abonnement</h1>
        <p class="ie-page-subtitle">Free, Basic, Premium, Pro... créez autant de paliers que nécessaire ; associez-les ensuite aux fonctionnalités dans « Fonctionnalités Marketplace ».</p>
      </div>
      <div class="ie-page-header-actions">
        <router-link :to="{ name: 'premium-marketplace-features-manage' }" class="ie-btn ie-btn-ghost">
          <i class="fa-solid fa-arrow-left"></i> Fonctionnalités Marketplace
        </router-link>
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau palier" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Code (identifiant technique)</label>
            <input v-model="form.code" class="ie-input" required placeholder="ex : basic" :disabled="!!editingId" />
          </div>
          <div>
            <label class="ie-label">Libellé affiché</label>
            <input v-model="form.label" class="ie-input" required placeholder="ex : Basic" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Niveau</label>
            <input v-model.number="form.level" type="number" min="0" class="ie-input" required />
            <p class="ie-field-hint">Plus élevé = plus de privilèges. Sert à comparer les paliers entre eux.</p>
          </div>
          <div>
            <label class="ie-label">Ordre d'affichage</label>
            <input v-model.number="form.order" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="2"></textarea>
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_default" type="checkbox" /> Palier attribué par défaut à un nouvel abonnement
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="tiers.length">
        <table class="ie-table">
          <thead>
            <tr><th>Niveau</th><th>Code</th><th>Libellé</th><th>Description</th><th>Par défaut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in tiers" :key="t.id">
              <td class="ie-num">{{ t.level }}</td>
              <td><code>{{ t.code }}</code></td>
              <td><strong>{{ t.label }}</strong></td>
              <td style="color: var(--ie-muted); font-size: 12.5px;">{{ t.description }}</td>
              <td>
                <span class="ie-badge" :class="t.is_default ? 'ie-badge-success' : 'ie-badge-neutral'">{{ t.is_default ? "Oui" : "Non" }}</span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(t)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteTier(t)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-layer-group" text="Aucun palier d'abonnement créé pour le moment." />
    </div>

    <div class="ie-page-header" style="margin-top: 32px;">
      <div>
        <h2 style="margin: 0;"><i class="fa-solid fa-tags" style="color: var(--ie-red); margin-right: 8px;"></i>Tarifs des formules d'abonnement</h2>
        <p class="ie-page-subtitle">Prix et durées des marketplaces, dont le tarif dédié aux missions talent — modifiables à tout moment, sans déploiement.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showPlanForm ? (showPlanForm = false) : startCreatePlan()">
          <i class="fa-solid" :class="showPlanForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showPlanForm ? "Annuler" : "Nouvelle formule" }}
        </button>
      </div>
    </div>

    <div v-if="showPlanForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitPlanForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Code (identifiant technique)</label>
            <input v-model="planForm.code" class="ie-input" required placeholder="ex : 3_months" :disabled="!!editingPlanId" />
          </div>
          <div>
            <label class="ie-label">Libellé affiché</label>
            <input v-model="planForm.label" class="ie-input" required placeholder="ex : 3 mois" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Marketplace concernée</label>
        <select v-model="planForm.marketplace_type" class="ie-select">
          <option :value="null">Tous les marketplaces (formule commune)</option>
          <option value="talent_missions">Missions pour talents</option>
          <option value="sale">Marketplace vente</option><option value="actors">Marketplace des acteurs</option>
          <option value="interior_design">Décoration & design intérieur</option><option value="venues">Salles de réception</option>
        </select>
        <p class="ie-field-hint">Une formule propre à un Marketplace remplace les formules communes pour cet espace. Les tarifs enregistrés sont appliqués au prochain paiement.</p>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Durée (mois, affichage)</label>
            <input v-model.number="planForm.months" type="number" min="1" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Durée exacte (jours ajoutés à l'abonnement)</label>
            <input v-model.number="planForm.duration_days" type="number" min="1" class="ie-input" required />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix (XAF)</label>
            <input v-model.number="planForm.price" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Réduction affichée (%, informatif)</label>
            <input v-model.number="planForm.discount_percent" type="number" min="0" max="90" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Ordre d'affichage</label>
        <input v-model.number="planForm.order" type="number" min="0" class="ie-input" style="max-width: 160px;" />
        <p v-if="planErrorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ planErrorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="planSubmitting">
          {{ planSubmitting ? "Enregistrement…" : editingPlanId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="plansLoading" />
      <div class="ie-table-wrap" v-else-if="plans.length">
        <table class="ie-table">
          <thead>
            <tr><th>Marketplace</th><th>Code</th><th>Libellé</th><th>Durée</th><th>Prix</th><th>Réduction</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="p in plans" :key="p.id">
              <td><strong>{{ p.marketplace_type ? marketplaceLabels[p.marketplace_type] || p.marketplace_type : "Tous les marketplaces" }}</strong></td>
              <td><code>{{ p.code }}</code></td>
              <td>{{ p.label }}</td>
              <td>{{ p.duration_days }} j</td>
              <td class="ie-num">{{ Number(p.price).toLocaleString('fr-FR') }} XAF</td>
              <td>
                <span v-if="p.discount_percent" class="ie-badge ie-badge-success">-{{ p.discount_percent }}%</span>
                <span v-else class="ie-badge ie-badge-neutral">—</span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEditPlan(p)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deletePlan(p)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-tags" text="Aucune formule tarifaire créée pour le moment." />
    </div>
  </div>
</template>
