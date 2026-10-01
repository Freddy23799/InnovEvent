<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const STATUS_LABELS = {
  carrier_assigned: "Transporteur affecté", collected: "Collectée", in_transit: "En transit",
  arrived: "Arrivée à destination", delivering: "En cours de livraison", delivered: "Livrée",
  failed: "Échec", postponed: "Reportée", cancelled: "Annulée",
};
const NEXT_STATUS = { carrier_assigned: "collected", collected: "in_transit", in_transit: "delivering" };
const NEXT_LABEL = { carrier_assigned: "Marquer collectée", collected: "Marquer en transit", in_transit: "Marquer en livraison" };
const TRACKABLE_STATUSES = ["carrier_assigned", "collected", "in_transit", "delivering"];

const loading = ref(true);
const deliveries = ref([]);
const acting = ref(null);
const sharingId = ref(null);
let sharingInterval = null;

function pushLocation(deliveryId) {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      api.post(`/deliveries/${deliveryId}/update-location/`, {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
      }).catch(() => {});
    },
    () => {},
    { timeout: 8000 },
  );
}

function startSharing(delivery) {
  sharingId.value = delivery.id;
  pushLocation(delivery.id);
  sharingInterval = setInterval(() => pushLocation(delivery.id), 20000);
  toast.success("Partage de position activé.");
}

function stopSharing() {
  if (sharingInterval) clearInterval(sharingInterval);
  sharingInterval = null;
  sharingId.value = null;
}

onBeforeUnmount(stopSharing);

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/deliveries/");
    deliveries.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

const today = new Date().toISOString().slice(0, 10);
const todayMissions = computed(() => deliveries.value.filter((d) => d.scheduled_date === today && !["delivered", "cancelled", "failed", "returned"].includes(d.status)));
const upcomingMissions = computed(() => deliveries.value.filter((d) => d.scheduled_date > today && !["delivered", "cancelled", "failed", "returned"].includes(d.status)));
const activeNoDate = computed(() => deliveries.value.filter((d) => !d.scheduled_date && !["delivered", "cancelled", "failed", "returned"].includes(d.status)));
const completedMissions = computed(() => deliveries.value.filter((d) => ["delivered", "cancelled", "failed", "returned"].includes(d.status)).slice(0, 20));

async function advanceStatus(delivery) {
  const next = NEXT_STATUS[delivery.status];
  if (!next) return;
  acting.value = delivery.id;
  try {
    await api.post(`/deliveries/${delivery.id}/change-status/`, { status: next, comment: "" });
    toast.success("Statut mis à jour.");
    await loadData();
  } catch (e) {
    toast.error("Impossible de mettre à jour ce statut.");
  } finally {
    acting.value = null;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-truck-fast" style="color: var(--ie-red); margin-right: 8px;"></i>Mes livraisons</h1>
    <p class="ie-page-subtitle">Missions qui vous sont affectées en tant que chauffeur.</p>

    <div v-if="loading" class="ie-card ie-card-body">Chargement…</div>

    <template v-else>
      <EmptyState
        v-if="!deliveries.length"
        icon="fa-solid fa-truck-fast"
        text="Aucune livraison ne vous est affectée pour le moment. Si vous êtes chauffeur, contactez l'administrateur pour lier votre compte à votre profil chauffeur."
      />

      <template v-else>
        <div class="ie-card ie-section" style="padding: 20px; margin-top: 16px;">
          <h2 style="margin-bottom: 14px;">Aujourd'hui ({{ todayMissions.length }})</h2>
          <div v-if="!todayMissions.length" style="color: var(--ie-muted);">Aucune mission aujourd'hui.</div>
          <div v-for="d in todayMissions" :key="d.id" class="ie-mission-row">
            <div>
              <strong>{{ d.reference }}</strong> — {{ d.destination_address }}
              <div style="font-size: 12px; color: var(--ie-muted);">{{ STATUS_LABELS[d.status] }}</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <router-link :to="{ name: 'delivery-detail', params: { id: d.id } }" class="ie-btn ie-btn-ghost ie-btn-sm">Détail</router-link>
              <button v-if="NEXT_STATUS[d.status]" class="ie-btn ie-btn-primary ie-btn-sm" :disabled="acting === d.id" @click="advanceStatus(d)">
                {{ NEXT_LABEL[d.status] }}
              </button>
              <button
                v-if="TRACKABLE_STATUSES.includes(d.status) && sharingId !== d.id"
                class="ie-btn ie-btn-secondary ie-btn-sm" @click="startSharing(d)"
              >
                <i class="fa-solid fa-location-crosshairs"></i> Partager ma position
              </button>
              <button v-else-if="sharingId === d.id" class="ie-btn ie-btn-danger ie-btn-sm" @click="stopSharing">
                <i class="fa-solid fa-location-crosshairs"></i> Arrêter le partage
              </button>
            </div>
          </div>
        </div>

        <div class="ie-card ie-section" style="padding: 20px; margin-top: 16px;" v-if="activeNoDate.length">
          <h2 style="margin-bottom: 14px;">En cours ({{ activeNoDate.length }})</h2>
          <div v-for="d in activeNoDate" :key="d.id" class="ie-mission-row">
            <div>
              <strong>{{ d.reference }}</strong> — {{ d.destination_address }}
              <div style="font-size: 12px; color: var(--ie-muted);">{{ STATUS_LABELS[d.status] }}</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <router-link :to="{ name: 'delivery-detail', params: { id: d.id } }" class="ie-btn ie-btn-ghost ie-btn-sm">Détail</router-link>
              <button v-if="NEXT_STATUS[d.status]" class="ie-btn ie-btn-primary ie-btn-sm" :disabled="acting === d.id" @click="advanceStatus(d)">
                {{ NEXT_LABEL[d.status] }}
              </button>
              <button
                v-if="TRACKABLE_STATUSES.includes(d.status) && sharingId !== d.id"
                class="ie-btn ie-btn-secondary ie-btn-sm" @click="startSharing(d)"
              >
                <i class="fa-solid fa-location-crosshairs"></i> Partager ma position
              </button>
              <button v-else-if="sharingId === d.id" class="ie-btn ie-btn-danger ie-btn-sm" @click="stopSharing">
                <i class="fa-solid fa-location-crosshairs"></i> Arrêter le partage
              </button>
            </div>
          </div>
        </div>

        <div class="ie-card ie-section" style="padding: 20px; margin-top: 16px;">
          <h2 style="margin-bottom: 14px;">À venir ({{ upcomingMissions.length }})</h2>
          <div v-if="!upcomingMissions.length" style="color: var(--ie-muted);">Aucune mission programmée.</div>
          <div v-for="d in upcomingMissions" :key="d.id" class="ie-mission-row">
            <div>
              <strong>{{ d.reference }}</strong> — {{ d.destination_address }}
              <div style="font-size: 12px; color: var(--ie-muted);">{{ d.scheduled_date }} — {{ STATUS_LABELS[d.status] }}</div>
            </div>
            <router-link :to="{ name: 'delivery-detail', params: { id: d.id } }" class="ie-btn ie-btn-ghost ie-btn-sm">Détail</router-link>
          </div>
        </div>

        <div class="ie-card ie-section" style="padding: 20px; margin-top: 16px;" v-if="completedMissions.length">
          <h2 style="margin-bottom: 14px;">Historique récent</h2>
          <div v-for="d in completedMissions" :key="d.id" class="ie-mission-row">
            <div>
              <strong>{{ d.reference }}</strong> — {{ d.destination_address }}
              <div style="font-size: 12px; color: var(--ie-muted);">{{ STATUS_LABELS[d.status] || d.status }}</div>
            </div>
            <router-link :to="{ name: 'delivery-detail', params: { id: d.id } }" class="ie-btn ie-btn-ghost ie-btn-sm">Détail</router-link>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.ie-mission-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--ie-border); }
.ie-mission-row:last-child { border-bottom: none; }
</style>
