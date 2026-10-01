<script setup>
import { ref } from "vue";
import { useRoute } from "vue-router";
import api from "../../services/api";

const route = useRoute();

const code = ref((route.query.code || "").toString().toUpperCase());
const loading = ref(false);
const notFound = ref(false);
const searched = ref(false);
const delivery = ref(null);

async function search() {
  if (!code.value.trim()) return;
  loading.value = true;
  notFound.value = false;
  searched.value = true;
  delivery.value = null;
  try {
    const { data } = await api.get("/deliveries/track/", { params: { code: code.value.trim().toUpperCase() } });
    delivery.value = data;
  } catch (e) {
    notFound.value = true;
  } finally {
    loading.value = false;
  }
}

if (code.value) search();
</script>

<template>
  <div class="ie-tracking-page">
    <h1><i class="fa-solid fa-truck" style="color: var(--ie-red); margin-right: 8px;"></i>Suivre ma livraison</h1>
    <p class="ie-page-subtitle">Entrez le code de suivi reçu par SMS ou email pour connaître l'état de votre livraison.</p>

    <div class="ie-card ie-card-body ie-tracking-search">
      <label class="ie-label">Code de suivi</label>
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <input v-model="code" class="ie-input" placeholder="Ex : TRK-A1B2C3D4" style="max-width: 260px; text-transform: uppercase;" @keyup.enter="search" />
        <button class="ie-btn ie-btn-primary" :disabled="loading || !code.trim()" @click="search">
          <i class="fa-solid fa-magnifying-glass"></i> {{ loading ? "Recherche…" : "Suivre" }}
        </button>
      </div>
    </div>

    <div v-if="searched && notFound" class="ie-alert ie-alert-danger" style="margin-top: 20px;">
      Aucune livraison trouvée pour ce code. Vérifiez le code reçu et réessayez.
    </div>

    <div v-if="delivery" class="ie-card ie-card-body" style="margin-top: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div>
          <h2 style="margin: 0 0 4px;">{{ delivery.reference }}</h2>
          <p style="margin: 0; color: var(--ie-muted); font-size: 13px;">Code : {{ delivery.tracking_code }}</p>
        </div>
        <span class="ie-badge ie-badge-success" style="font-size: 14px;">{{ delivery.status_display }}</span>
      </div>

      <p style="margin-top: 16px;"><strong>Départ :</strong> {{ delivery.pickup_city }}</p>
      <p><strong>Destination :</strong> {{ delivery.destination_city }}</p>
      <p v-if="delivery.scheduled_date"><strong>Livraison prévue :</strong> {{ delivery.scheduled_date }}</p>

      <h3 style="margin-top: 20px;">Étapes</h3>
      <div class="ie-tracking-timeline">
        <div v-for="(step, i) in delivery.status_history" :key="i" class="ie-tracking-step">
          <div class="ie-tracking-dot"></div>
          <div>
            <strong>{{ step.status_display }}</strong>
            <div style="font-size: 12px; color: var(--ie-muted);">{{ new Date(step.created_at).toLocaleString('fr-FR') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-tracking-page { max-width: 720px; margin: 0 auto; }
.ie-tracking-search { margin-top: 20px; }
.ie-tracking-timeline { display: flex; flex-direction: column; gap: 14px; margin-top: 10px; }
.ie-tracking-step { display: flex; align-items: center; gap: 12px; }
.ie-tracking-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--ie-red); flex-shrink: 0; }
</style>
