<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "../../services/api";

const commissions = ref([]);
const loading = ref(true);
const saving = reactive({});
const saved = reactive({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/commissions/");
    commissions.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function save(commission) {
  saving[commission.id] = true;
  try {
    const { data } = await api.patch(`/marketplace/commissions/${commission.id}/`, {
      commission_percent: commission.commission_percent,
    });
    Object.assign(commission, data);
    saved[commission.id] = true;
    setTimeout(() => { saved[commission.id] = false; }, 1500);
  } finally {
    saving[commission.id] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-percent" style="color: var(--ie-red); margin-right: 8px;"></i>Commissions</h1>
        <p class="ie-page-subtitle">
          Pourcentage prélevé par InnovEvent sur chaque devis payé, par marketplace. Le taux appliqué est figé au moment du paiement — le modifier n'affecte que les paiements futurs.
        </p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <div v-else class="ie-commission-grid">
      <div v-for="c in commissions" :key="c.id" class="ie-card ie-card-body">
        <h2 style="margin: 0 0 12px; font-size: 15px;">{{ c.marketplace_label }}</h2>
        <div style="display: flex; align-items: center; gap: 10px;">
          <input v-model.number="c.commission_percent" type="number" min="0" max="100" step="0.5" class="ie-input" style="max-width: 100px;" />
          <span style="font-size: 14px; color: var(--ie-muted);">%</span>
          <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="saving[c.id]" @click="save(c)">
            {{ saving[c.id] ? "..." : "Enregistrer" }}
          </button>
          <i v-if="saved[c.id]" class="fa-solid fa-circle-check" style="color: var(--ie-success);"></i>
        </div>
        <p class="ie-field-hint" style="margin-top: 10px;">
          Ex : un devis de 100 000 XAF rapporte {{ (100000 * c.commission_percent / 100).toLocaleString('fr-FR') }} XAF à InnovEvent
          et {{ (100000 - 100000 * c.commission_percent / 100).toLocaleString('fr-FR') }} XAF au prestataire.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-commission-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
</style>
