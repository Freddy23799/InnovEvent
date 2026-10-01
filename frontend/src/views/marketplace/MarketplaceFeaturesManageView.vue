<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";

const MARKETPLACE_LABELS = {
  sale: "Marketplace vente",
  interior_design: "Décoration & design intérieur",
  actors: "Marketplace des acteurs",
  venues: "Salles de réception",
};

const VISIBILITY_OPTIONS = [
  { value: "everyone", label: "Tout le monde" },
  { value: "authenticated", label: "Utilisateurs connectés" },
  { value: "non_subscriber", label: "Utilisateurs non abonnés" },
  { value: "subscriber", label: "Utilisateurs abonnés" },
  { value: "admin", label: "Administrateurs uniquement" },
];
const STATE_OPTIONS = [
  { value: "shown", label: "Affiché" },
  { value: "hidden", label: "Masqué" },
  { value: "locked", label: "Verrouillé" },
  { value: "upsell", label: "Affiché avec message d'abonnement" },
];
const STATE_BADGE = { shown: "ie-badge-success", hidden: "ie-badge-neutral", locked: "ie-badge-danger", upsell: "ie-badge-warning" };

const loading = ref(true);
const features = ref([]);
const tiers = ref([]);
const savingId = ref(null);
const savedFlash = reactive({});

const groupedFeatures = computed(() => {
  const groups = {};
  for (const f of features.value) {
    (groups[f.marketplace_type] ||= []).push(f);
  }
  return groups;
});

async function loadData() {
  loading.value = true;
  try {
    const [featuresRes, tiersRes] = await Promise.all([
      api.get("/marketplace/features/"),
      api.get("/marketplace/tiers/"),
    ]);
    features.value = featuresRes.data.results || featuresRes.data;
    tiers.value = tiersRes.data.results || tiersRes.data;
  } finally {
    loading.value = false;
  }
}

async function updateFeature(feature, patch) {
  savingId.value = feature.id;
  try {
    const { data } = await api.patch(`/marketplace/features/${feature.id}/`, patch);
    Object.assign(feature, data);
    savedFlash[feature.id] = true;
    setTimeout(() => { savedFlash[feature.id] = false; }, 1500);
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
        <h1><i class="fa-solid fa-sliders" style="color: var(--ie-red); margin-right: 8px;"></i>Fonctionnalités Marketplace</h1>
        <p class="ie-page-subtitle">
          Moteur central de permissions : définissez qui voit quoi, et ce qui nécessite un abonnement — sans toucher au code.
          Une fonctionnalité masquée n'est jamais supprimée, elle redevient disponible en un clic.
        </p>
      </div>
      <div class="ie-page-header-actions">
        <router-link :to="{ name: 'marketplace-tiers-manage' }" class="ie-btn ie-btn-ghost">
          <i class="fa-solid fa-layer-group"></i> Gérer les paliers d'abonnement
        </router-link>
      </div>
    </div>

    <div v-if="loading" class="ie-card"><SkeletonTable /></div>

    <template v-else>
      <div v-for="(list, marketplaceType) in groupedFeatures" :key="marketplaceType" class="ie-card" style="margin-bottom: 20px;">
        <div class="ie-card-body" style="padding-bottom: 8px;">
          <h2 style="margin: 0;">{{ MARKETPLACE_LABELS[marketplaceType] || marketplaceType }}</h2>
        </div>
        <div class="ie-table-wrap">
          <table class="ie-table">
            <thead>
              <tr>
                <th>Fonctionnalité</th>
                <th>Visibilité</th>
                <th>État</th>
                <th>Palier minimum</th>
                <th>Message d'abonnement</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in list" :key="f.id">
                <td>
                  <strong>{{ f.label }}</strong>
                  <p v-if="f.description" class="ie-field-hint" style="margin: 2px 0 0;">{{ f.description }}</p>
                </td>
                <td>
                  <select
                    class="ie-select" :value="f.visibility" :disabled="savingId === f.id"
                    @change="updateFeature(f, { visibility: $event.target.value })"
                  >
                    <option v-for="v in VISIBILITY_OPTIONS" :key="v.value" :value="v.value">{{ v.label }}</option>
                  </select>
                </td>
                <td>
                  <select
                    class="ie-select" :value="f.state" :disabled="savingId === f.id"
                    @change="updateFeature(f, { state: $event.target.value })"
                  >
                    <option v-for="s in STATE_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
                  </select>
                </td>
                <td>
                  <select
                    class="ie-select" :value="f.min_tier ?? ''" :disabled="savingId === f.id"
                    @change="updateFeature(f, { min_tier: $event.target.value || null })"
                  >
                    <option value="">Aucun</option>
                    <option v-for="t in tiers" :key="t.id" :value="t.id">{{ t.label }}</option>
                  </select>
                </td>
                <td>
                  <input
                    class="ie-input" :value="f.upsell_message" placeholder="Ex : Abonnez-vous pour accéder à..."
                    :disabled="savingId === f.id"
                    @change="updateFeature(f, { upsell_message: $event.target.value })"
                  />
                </td>
                <td style="white-space: nowrap;">
                  <span class="ie-badge" :class="STATE_BADGE[f.state]">{{ STATE_OPTIONS.find(s => s.value === f.state)?.label }}</span>
                  <i v-if="savedFlash[f.id]" class="fa-solid fa-circle-check" style="color: var(--ie-success); margin-left: 6px;"></i>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <EmptyState v-if="!features.length" icon="fa-solid fa-sliders" text="Aucune fonctionnalité de marketplace configurée pour le moment." />
    </template>
  </div>
</template>

<style scoped>
.ie-table td:nth-child(1) { min-width: 200px; }
.ie-table td:nth-child(2) select { min-width: 170px; }
.ie-table td:nth-child(3) select { min-width: 190px; }
.ie-table td:nth-child(4) select { min-width: 110px; }
.ie-table td:nth-child(5) input { min-width: 220px; }
.ie-table td { vertical-align: top; padding-top: 14px; }
</style>
