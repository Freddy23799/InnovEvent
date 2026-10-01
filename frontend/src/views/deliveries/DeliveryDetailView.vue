<script setup>
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const toast = useToastStore();

const ACTIVE_TRACKING_STATUSES = ["carrier_assigned", "collected", "in_transit", "arrived", "delivering"];
const mapContainer = ref(null);
let mapInstance = null;
let mapMarker = null;
let clientMapMarker = null;
let mapPollInterval = null;

const STATUS_ORDER = [
  "created", "pending", "confirmed", "to_prepare", "ready", "carrier_assigned",
  "collected", "in_transit", "arrived", "delivering", "delivered",
];
const STATUS_BADGE = {
  created: "ie-badge-neutral", pending: "ie-badge-warning", confirmed: "ie-badge-success", to_prepare: "ie-badge-warning",
  ready: "ie-badge-warning", carrier_assigned: "ie-badge-success", collected: "ie-badge-success", in_transit: "ie-badge-success",
  arrived: "ie-badge-success", delivering: "ie-badge-success", delivered: "ie-badge-success", failed: "ie-badge-danger",
  postponed: "ie-badge-warning", cancelled: "ie-badge-danger", returning: "ie-badge-warning", returned: "ie-badge-danger",
};
const ALL_STATUSES = [
  { value: "created", label: "Créée" }, { value: "pending", label: "En attente" }, { value: "confirmed", label: "Confirmée" },
  { value: "to_prepare", label: "À préparer" }, { value: "ready", label: "Prête à récupérer" },
  { value: "carrier_assigned", label: "Transporteur affecté" }, { value: "collected", label: "Collectée" },
  { value: "in_transit", label: "En transit" }, { value: "arrived", label: "Arrivée à destination" },
  { value: "delivering", label: "En cours de livraison" }, { value: "delivered", label: "Livrée" },
  { value: "failed", label: "Échec de livraison" }, { value: "postponed", label: "Reportée" }, { value: "cancelled", label: "Annulée" },
  { value: "returning", label: "Retour en cours" }, { value: "returned", label: "Retournée" },
];

const CARRIER_STATUS_LABELS = {
  available: "Disponible", busy: "Occupé", off_duty: "Hors service", suspended: "Suspendu", inactive: "Inactif",
};
const DRIVER_STATUS_LABELS = {
  available: "Disponible", on_mission: "En mission", off_duty: "Hors service", suspended: "Suspendu",
};

const delivery = ref(null);
const carriers = ref([]);
const drivers = ref([]);
const vehicles = ref([]);
const loading = ref(true);
const notFound = ref(false);

const showAssignForm = ref(false);
const assignForm = ref({ carrier: "", driver: "", vehicle: "" });
const assignSubmitting = ref(false);
const assignWarnings = ref([]);

const statusForm = ref({ status: "", comment: "" });
const statusSubmitting = ref(false);

const showProofForm = ref(false);
const proofForm = ref({ receiver_name: "", receiver_phone: "", otp_code: "" });
const proofSubmitting = ref(false);
const proofPhotoFile = ref(null);
const signatureCanvas = ref(null);
const hasSignature = ref(false);
let signatureCtx = null;
let drawing = false;

function onProofPhotoChange(event) {
  proofPhotoFile.value = event.target.files[0] || null;
}

function initSignatureCanvas() {
  const canvas = signatureCanvas.value;
  if (!canvas) return;
  signatureCtx = canvas.getContext("2d");
  signatureCtx.lineWidth = 2;
  signatureCtx.lineCap = "round";
  signatureCtx.strokeStyle = "#1B2733";
  hasSignature.value = false;
}

function pointerPos(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  const point = event.touches ? event.touches[0] : event;
  return { x: point.clientX - rect.left, y: point.clientY - rect.top };
}

function startDraw(event) {
  drawing = true;
  const { x, y } = pointerPos(signatureCanvas.value, event);
  signatureCtx.beginPath();
  signatureCtx.moveTo(x, y);
}

function draw(event) {
  if (!drawing) return;
  event.preventDefault();
  const { x, y } = pointerPos(signatureCanvas.value, event);
  signatureCtx.lineTo(x, y);
  signatureCtx.stroke();
  hasSignature.value = true;
}

function stopDraw() {
  drawing = false;
}

function clearSignature() {
  const canvas = signatureCanvas.value;
  signatureCtx.clearRect(0, 0, canvas.width, canvas.height);
  hasSignature.value = false;
}

function signatureBlob() {
  return new Promise((resolve) => {
    if (!hasSignature.value) {
      resolve(null);
      return;
    }
    signatureCanvas.value.toBlob((blob) => resolve(blob), "image/png");
  });
}

const RETURN_REASONS = [
  { value: "refused", label: "Refusé par le destinataire" }, { value: "damaged", label: "Colis endommagé" },
  { value: "wrong_address", label: "Adresse erronée" }, { value: "client_absent", label: "Destinataire absent" },
  { value: "other", label: "Autre" },
];
const showReturnForm = ref(false);
const returnForm = ref({ reason: "refused", condition_notes: "", refund_status: "none", refund_amount: null });
const returnSubmitting = ref(false);

const isAdmin = computed(() => auth.role === "admin");
const myCarrierId = ref(null);
const isCarrierOwner = computed(() => auth.role === "partner" && myCarrierId.value && delivery.value?.carrier === myCarrierId.value);
const canAssign = computed(() => isAdmin.value || isCarrierOwner.value);
const isClientOwner = computed(() => delivery.value?.client === auth.user?.id);
const sharingLocation = ref(false);
const locationWatchId = ref(null);
const locationError = ref("");

async function loadData() {
  loading.value = true;
  notFound.value = false;
  try {
    if (auth.role === "partner" && myCarrierId.value === null) {
      try {
        const { data: me } = await api.get("/deliveries/carriers/me/");
        myCarrierId.value = me.id;
      } catch (e) {
        myCarrierId.value = false; // pas de profil transporteur lié à ce compte
      }
    }
    const { data } = await api.get(`/deliveries/${route.params.id}/`);
    delivery.value = data;
    assignForm.value = { carrier: data.carrier || "", driver: data.driver || "", vehicle: data.vehicle || "" };
    if (isAdmin.value) {
      const [carriersRes, driversRes, vehiclesRes] = await Promise.all([
        api.get("/deliveries/carriers/"), api.get("/deliveries/drivers/"), api.get("/deliveries/vehicles/"),
      ]);
      carriers.value = carriersRes.data.results || carriersRes.data;
      drivers.value = driversRes.data.results || driversRes.data;
      vehicles.value = vehiclesRes.data.results || vehiclesRes.data;
    } else if (isCarrierOwner.value) {
      // Un transporteur ne réaffecte jamais à un autre transporteur : seuls
      // ses propres chauffeurs/véhicules sont proposés (déjà filtrés côté
      // backend), et le sélecteur « Transporteur » reste masqué.
      const [driversRes, vehiclesRes] = await Promise.all([api.get("/deliveries/drivers/"), api.get("/deliveries/vehicles/")]);
      drivers.value = driversRes.data.results || driversRes.data;
      vehicles.value = vehiclesRes.data.results || vehiclesRes.data;
    }
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
  } finally {
    loading.value = false;
  }
}

const timelineSteps = computed(() => {
  if (!delivery.value) return [];
  const reached = new Map((delivery.value.status_history || []).map((h) => [h.new_status, h.created_at]));
  const currentIndex = STATUS_ORDER.indexOf(delivery.value.status);
  return STATUS_ORDER.map((s, i) => ({
    status: s,
    label: ALL_STATUSES.find((x) => x.value === s)?.label,
    done: i <= currentIndex,
    at: reached.get(s),
  }));
});

async function submitAssign() {
  assignSubmitting.value = true;
  assignWarnings.value = [];
  try {
    const payload = {
      carrier: assignForm.value.carrier || null, driver: assignForm.value.driver || null,
      vehicle: assignForm.value.vehicle || null,
    };
    const { data } = await api.post(`/deliveries/${delivery.value.id}/assign/`, payload);
    delivery.value = data;
    showAssignForm.value = false;
    toast.success("Affectation enregistrée.");
  } catch (e) {
    if (e?.response?.status === 409) {
      assignWarnings.value = e.response.data.warnings || [];
    } else {
      toast.error("Impossible d'affecter cette livraison.");
    }
  } finally {
    assignSubmitting.value = false;
  }
}

async function forceAssign() {
  assignSubmitting.value = true;
  try {
    const payload = {
      carrier: assignForm.value.carrier || null, driver: assignForm.value.driver || null,
      vehicle: assignForm.value.vehicle || null, force: true,
    };
    const { data } = await api.post(`/deliveries/${delivery.value.id}/assign/`, payload);
    delivery.value = data;
    showAssignForm.value = false;
    assignWarnings.value = [];
    toast.success("Affectation forcée enregistrée.");
  } catch (e) {
    toast.error("Impossible d'affecter cette livraison.");
  } finally {
    assignSubmitting.value = false;
  }
}

async function changeStatus(newStatus) {
  statusSubmitting.value = true;
  try {
    const { data } = await api.post(`/deliveries/${delivery.value.id}/change-status/`, {
      status: newStatus, comment: statusForm.value.comment,
    });
    delivery.value = data;
    statusForm.value.comment = "";
    toast.success("Statut mis à jour.");
  } catch (e) {
    toast.error(e?.response?.data?.detail || e?.response?.data?.non_field_errors?.[0] || "Transition impossible.");
  } finally {
    statusSubmitting.value = false;
  }
}

function driverNextStatus() {
  const map = {
    carrier_assigned: "collected", collected: "in_transit", in_transit: "delivering",
  };
  return map[delivery.value?.status];
}
function driverNextLabel() {
  return ALL_STATUSES.find((s) => s.value === driverNextStatus())?.label;
}

async function pushClientPosition(coords) {
  try {
    const { data } = await api.post(`/deliveries/${delivery.value.id}/update-client-location/`, {
      latitude: coords.latitude, longitude: coords.longitude,
    });
    delivery.value.client_latitude = data.client_latitude;
    delivery.value.client_longitude = data.client_longitude;
    delivery.value.client_location_at = data.client_location_at;
    await nextTick();
    renderOrUpdateMap();
  } catch (e) {
    // publication non critique — on ignore une erreur ponctuelle
  }
}

function startSharingLocation() {
  if (!navigator.geolocation) {
    locationError.value = "La géolocalisation n'est pas disponible sur cet appareil.";
    return;
  }
  locationError.value = "";
  sharingLocation.value = true;
  locationWatchId.value = navigator.geolocation.watchPosition(
    (pos) => pushClientPosition({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
    () => {
      locationError.value = "Impossible d'accéder à votre position. Vérifiez l'autorisation de localisation.";
      sharingLocation.value = false;
    },
    { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 },
  );
}

function stopSharingLocation() {
  if (locationWatchId.value !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(locationWatchId.value);
  }
  locationWatchId.value = null;
  sharingLocation.value = false;
}

function getCurrentPosition() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => resolve(null),
      { timeout: 5000 },
    );
  });
}

async function submitProof() {
  proofSubmitting.value = true;
  try {
    const position = await getCurrentPosition();
    const sigBlob = await signatureBlob();
    const payload = new FormData();
    Object.entries(proofForm.value).forEach(([key, value]) => payload.append(key, value));
    if (position) {
      payload.append("latitude", position.latitude);
      payload.append("longitude", position.longitude);
    }
    if (proofPhotoFile.value) payload.append("photo", proofPhotoFile.value);
    if (sigBlob) payload.append("signature_image", sigBlob, "signature.png");

    const { data } = await api.post(`/deliveries/${delivery.value.id}/confirm-proof/`, payload);
    delivery.value = data;
    showProofForm.value = false;
    toast.success(position ? "Livraison confirmée avec géolocalisation." : "Livraison confirmée.");
  } catch (e) {
    toast.error("Impossible de confirmer la livraison.");
  } finally {
    proofSubmitting.value = false;
  }
}

async function submitReturn() {
  returnSubmitting.value = true;
  try {
    const { data } = await api.post(`/deliveries/${delivery.value.id}/return/`, returnForm.value);
    delivery.value = data;
    showReturnForm.value = false;
    toast.success("Retour enregistré.");
  } catch (e) {
    toast.error("Impossible d'enregistrer ce retour.");
  } finally {
    returnSubmitting.value = false;
  }
}

async function downloadPdf() {
  const res = await api.get(`/deliveries/${delivery.value.id}/pdf/`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  window.open(url, "_blank");
}

const markerIcon = L.icon({
  iconUrl: new URL("leaflet/dist/images/marker-icon.png", import.meta.url).href,
  iconRetinaUrl: new URL("leaflet/dist/images/marker-icon-2x.png", import.meta.url).href,
  shadowUrl: new URL("leaflet/dist/images/marker-shadow.png", import.meta.url).href,
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

function renderOrUpdateMap() {
  const lat = delivery.value?.last_latitude;
  const lng = delivery.value?.last_longitude;
  const clientLat = delivery.value?.client_latitude;
  const clientLng = delivery.value?.client_longitude;
  if ((!lat || !lng) && (!clientLat || !clientLng)) return;
  if (!mapContainer.value) return;

  if (!mapInstance) {
    mapInstance = L.map(mapContainer.value).setView([Number(lat || clientLat), Number(lng || clientLng)], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 18,
    }).addTo(mapInstance);
  }

  if (lat && lng) {
    const position = [Number(lat), Number(lng)];
    if (!mapMarker) {
      mapMarker = L.marker(position, { icon: markerIcon }).bindTooltip("Chauffeur").addTo(mapInstance);
    } else {
      mapMarker.setLatLng(position);
    }
  }

  if (clientLat && clientLng) {
    const clientPosition = [Number(clientLat), Number(clientLng)];
    if (!clientMapMarker) {
      clientMapMarker = L.circleMarker(clientPosition, {
        radius: 9, color: "#1976d2", fillColor: "#42a5f5", fillOpacity: 0.9, weight: 2,
      }).bindTooltip("Destinataire").addTo(mapInstance);
    } else {
      clientMapMarker.setLatLng(clientPosition);
    }
  }

  if (mapMarker && clientMapMarker) {
    mapInstance.fitBounds(L.latLngBounds([mapMarker.getLatLng(), clientMapMarker.getLatLng()]), { padding: [30, 30], maxZoom: 15 });
  } else if (mapMarker) {
    mapInstance.setView(mapMarker.getLatLng());
  } else if (clientMapMarker) {
    mapInstance.setView(clientMapMarker.getLatLng());
  }
}

async function refreshMapPosition() {
  if (!delivery.value) return;
  try {
    const { data } = await api.get(`/deliveries/${delivery.value.id}/`);
    delivery.value.last_latitude = data.last_latitude;
    delivery.value.last_longitude = data.last_longitude;
    delivery.value.last_location_at = data.last_location_at;
    delivery.value.client_latitude = data.client_latitude;
    delivery.value.client_longitude = data.client_longitude;
    delivery.value.client_location_at = data.client_location_at;
    await nextTick();
    renderOrUpdateMap();
  } catch (e) {
    // suivi non critique — on ignore silencieusement une erreur ponctuelle
  }
}

function stopMapPolling() {
  if (mapPollInterval) clearInterval(mapPollInterval);
  mapPollInterval = null;
}

watch(
  () => delivery.value?.status,
  async (status) => {
    stopMapPolling();
    if (status && ACTIVE_TRACKING_STATUSES.includes(status)) {
      await nextTick();
      renderOrUpdateMap();
      mapPollInterval = setInterval(refreshMapPosition, 20000);
    } else {
      // Livraison confirmée (ou annulée/retournée) : le partage de position
      // du client n'a plus lieu d'être — on coupe le suivi navigateur.
      stopSharingLocation();
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  stopMapPolling();
  stopSharingLocation();
});

onMounted(loadData);
</script>

<template>
  <div>
    <button class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-bottom: 14px;" @click="router.back()">
      <i class="fa-solid fa-arrow-left"></i> Retour
    </button>

    <div v-if="loading" class="ie-card ie-card-body">Chargement…</div>
    <EmptyState v-else-if="notFound" icon="fa-solid fa-triangle-exclamation" text="Livraison introuvable." />

    <template v-else-if="delivery">
      <div class="ie-page-header">
        <div>
          <h1><i class="fa-solid fa-box-open" style="color: var(--ie-red); margin-right: 8px;"></i>{{ delivery.reference }}</h1>
          <p class="ie-page-subtitle">Code de suivi public : <strong>{{ delivery.tracking_code }}</strong></p>
        </div>
        <div class="ie-page-header-actions">
          <span class="ie-badge" :class="STATUS_BADGE[delivery.status]" style="font-size: 14px;">{{ delivery.status_display }}</span>
          <button class="ie-btn ie-btn-ghost" @click="downloadPdf"><i class="fa-solid fa-file-pdf"></i> Bon de livraison</button>
        </div>
      </div>

      <div class="ie-detail-grid">
        <div class="ie-card ie-card-body">
          <h3>Expéditeur / Destinataire</h3>
          <p><strong>Client :</strong> {{ delivery.client_name || "—" }} ({{ delivery.client_phone || "—" }})</p>
          <p><strong>Départ :</strong> {{ delivery.pickup_address }}</p>
          <p><strong>Destination :</strong> {{ delivery.destination_address }}</p>
          <p><strong>Destinataire :</strong> {{ delivery.recipient_name || "—" }} ({{ delivery.recipient_phone || "—" }})</p>
          <p v-if="delivery.description"><strong>Description :</strong> {{ delivery.description }}</p>
          <p v-if="delivery.special_instructions"><strong>Instructions :</strong> {{ delivery.special_instructions }}</p>
        </div>

        <div class="ie-card ie-card-body">
          <h3>Transport</h3>
          <p><strong>Type :</strong> {{ delivery.delivery_type }} — <strong>Priorité :</strong> {{ delivery.priority }}</p>
          <p><strong>Transporteur :</strong> {{ delivery.carrier_name || "Non affecté" }}</p>
          <p><strong>Chauffeur :</strong> {{ delivery.driver_name || "Non affecté" }}</p>
          <p><strong>Véhicule :</strong> {{ delivery.vehicle_plate || "Non affecté" }}</p>
          <p><strong>Zone :</strong> {{ delivery.zone_name || "—" }}</p>

          <template v-if="ACTIVE_TRACKING_STATUSES.includes(delivery.status)">
            <p style="margin-top: 12px; margin-bottom: 6px;"><strong>Position en direct :</strong></p>
            <div v-if="delivery.last_latitude || delivery.client_latitude" ref="mapContainer" class="ie-delivery-map"></div>
            <p v-else style="color: var(--ie-muted); font-size: 13px;">
              Aucune position partagée pour le moment.
            </p>
            <p v-if="delivery.last_location_at" style="font-size: 11.5px; color: var(--ie-muted); margin-top: 4px;">
              <i class="fa-solid fa-truck" style="color: var(--ie-red);"></i> Chauffeur mis à jour : {{ new Date(delivery.last_location_at).toLocaleTimeString('fr-FR') }}
            </p>
            <p v-if="delivery.client_location_at" style="font-size: 11.5px; color: var(--ie-muted); margin-top: 2px;">
              <i class="fa-solid fa-location-dot" style="color: #1976d2;"></i> Destinataire mis à jour : {{ new Date(delivery.client_location_at).toLocaleTimeString('fr-FR') }}
            </p>

            <div v-if="isClientOwner" class="ie-alert" :class="sharingLocation ? 'ie-alert-success' : 'ie-alert-warning'" style="margin-top: 10px;">
              <p v-if="!sharingLocation" style="margin: 0 0 8px;">
                <i class="fa-solid fa-location-crosshairs"></i>
                Activez votre localisation pour faciliter la livraison par le transporteur.
              </p>
              <p v-else style="margin: 0 0 8px;">
                <i class="fa-solid fa-location-crosshairs"></i>
                Votre position est partagée avec le transporteur. Elle sera automatiquement coupée une fois la livraison validée.
              </p>
              <p v-if="locationError" style="margin: 0 0 8px; color: var(--ie-danger, #c0392b);">{{ locationError }}</p>
              <button v-if="!sharingLocation" class="ie-btn ie-btn-primary ie-btn-sm" @click="startSharingLocation">
                Activer ma localisation
              </button>
              <button v-else class="ie-btn ie-btn-ghost ie-btn-sm" @click="stopSharingLocation">
                Couper le partage
              </button>
            </div>
          </template>

          <template v-if="canAssign">
            <button class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 8px;" @click="showAssignForm = !showAssignForm">
              {{ showAssignForm ? "Annuler" : "Affecter / réaffecter" }}
            </button>
            <div v-if="showAssignForm" style="margin-top: 12px;">
              <template v-if="isAdmin">
                <label class="ie-label">Transporteur</label>
                <select v-model="assignForm.carrier" class="ie-select">
                  <option value="">—</option>
                  <option v-for="c in carriers" :key="c.id" :value="c.id">
                    {{ c.name }} — {{ CARRIER_STATUS_LABELS[c.status] || c.status }}
                  </option>
                </select>
              </template>
              <label class="ie-label" style="margin-top: 10px;">Chauffeur</label>
              <select v-model="assignForm.driver" class="ie-select">
                <option value="">—</option>
                <option v-for="d in drivers" :key="d.id" :value="d.id">
                  {{ d.full_name }} — {{ DRIVER_STATUS_LABELS[d.status] || d.status }}
                </option>
              </select>
              <label class="ie-label" style="margin-top: 10px;">Véhicule</label>
              <select v-model="assignForm.vehicle" class="ie-select">
                <option value="">—</option>
                <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}</option>
              </select>
              <p v-if="assignWarnings.length" class="ie-alert ie-alert-warning" style="margin-top: 10px;">
                <span v-for="(w, i) in assignWarnings" :key="i">{{ w }}<br /></span>
              </p>
              <div style="display: flex; gap: 8px; margin-top: 10px;">
                <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="assignSubmitting" @click="submitAssign">Valider</button>
                <button v-if="assignWarnings.length" class="ie-btn ie-btn-danger ie-btn-sm" :disabled="assignSubmitting" @click="forceAssign">
                  Forcer malgré les avertissements
                </button>
              </div>
            </div>
          </template>
        </div>

        <div class="ie-card ie-card-body">
          <h3>Colis</h3>
          <ul v-if="delivery.parcels?.length" class="ie-plain-list">
            <li v-for="p in delivery.parcels" :key="p.id">
              {{ p.description }} — Qté {{ p.quantity }}<span v-if="p.weight_kg"> — {{ p.weight_kg }} kg</span>
              <span v-if="p.is_fragile" class="ie-badge ie-badge-warning" style="margin-left: 6px;">Fragile</span>
            </li>
          </ul>
          <p v-else style="color: var(--ie-muted);">Aucun colis renseigné.</p>
        </div>

        <div class="ie-card ie-card-body">
          <h3>Financier</h3>
          <p><strong>Montant :</strong> {{ Number(delivery.amount).toLocaleString('fr-FR') }} XAF</p>
          <p><strong>Montant estimé (zone) :</strong> {{ Number(delivery.estimated_amount).toLocaleString('fr-FR') }} XAF</p>
          <p><strong>Mode de paiement :</strong> {{ delivery.payment_mode }}</p>
          <p><strong>Paiement lié :</strong> {{ delivery.payment ? `#${delivery.payment}` : "En attente" }}</p>
        </div>
      </div>

      <div class="ie-card ie-card-body" style="margin-top: 20px;">
        <h3>Historique des statuts</h3>
        <div class="ie-timeline">
          <div v-for="step in timelineSteps" :key="step.status" class="ie-timeline-step" :class="{ 'is-done': step.done }">
            <div class="ie-timeline-dot"></div>
            <div>
              <strong>{{ step.label }}</strong>
              <div v-if="step.at" style="font-size: 12px; color: var(--ie-muted);">{{ new Date(step.at).toLocaleString('fr-FR') }}</div>
            </div>
          </div>
        </div>

        <template v-if="isAdmin">
          <label class="ie-label" style="margin-top: 16px;">Changer le statut manuellement</label>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
            <select v-model="statusForm.status" class="ie-select" style="max-width: 260px;">
              <option value="">Choisir un statut</option>
              <option v-for="s in ALL_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
            <input v-model="statusForm.comment" class="ie-input" placeholder="Commentaire (optionnel)" style="max-width: 260px;" />
            <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="!statusForm.status || statusSubmitting" @click="changeStatus(statusForm.status)">
              Appliquer
            </button>
          </div>
        </template>

        <template v-else-if="driverNextStatus()">
          <button class="ie-btn ie-btn-primary" style="margin-top: 16px;" :disabled="statusSubmitting" @click="changeStatus(driverNextStatus())">
            <i class="fa-solid fa-truck-fast"></i> Marquer « {{ driverNextLabel() }} »
          </button>
        </template>

        <template v-if="!isAdmin && delivery.status === 'delivering' && !delivery.proof">
          <button
            class="ie-btn ie-btn-ghost" style="margin-top: 12px;"
            @click="showProofForm = !showProofForm; if (showProofForm) nextTick(initSignatureCanvas)"
          >
            {{ showProofForm ? "Annuler" : "Confirmer la livraison (preuve)" }}
          </button>
          <div v-if="showProofForm" style="margin-top: 12px;">
            <label class="ie-label">Nom du réceptionnaire</label>
            <input v-model="proofForm.receiver_name" class="ie-input" />
            <label class="ie-label" style="margin-top: 10px;">Téléphone du réceptionnaire</label>
            <input v-model="proofForm.receiver_phone" class="ie-input" />
            <label class="ie-label" style="margin-top: 10px;">Code OTP (optionnel)</label>
            <input v-model="proofForm.otp_code" class="ie-input" />

            <label class="ie-label" style="margin-top: 10px;">Photo du colis livré (optionnel)</label>
            <input type="file" accept="image/*" capture="environment" class="ie-input" @change="onProofPhotoChange" />

            <label class="ie-label" style="margin-top: 10px;">Signature du réceptionnaire (optionnel)</label>
            <canvas
              ref="signatureCanvas" width="320" height="140" class="ie-signature-pad"
              @mousedown="startDraw" @mousemove="draw" @mouseup="stopDraw" @mouseleave="stopDraw"
              @touchstart="startDraw" @touchmove="draw" @touchend="stopDraw"
            ></canvas>
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 6px;" @click="clearSignature">
              Effacer la signature
            </button>

            <button class="ie-btn ie-btn-primary" style="margin-top: 16px;" :disabled="proofSubmitting" @click="submitProof">
              {{ proofSubmitting ? "Confirmation…" : "Confirmer la livraison" }}
            </button>
          </div>
        </template>
      </div>

      <div v-if="delivery.proof" class="ie-card ie-card-body" style="margin-top: 20px;">
        <h3>Preuve de livraison</h3>
        <p><strong>Réceptionnaire :</strong> {{ delivery.proof.receiver_name || "—" }} ({{ delivery.proof.receiver_phone || "—" }})</p>
        <p><strong>Confirmée le :</strong> {{ new Date(delivery.proof.confirmed_at).toLocaleString('fr-FR') }}</p>
        <p v-if="delivery.proof.latitude && delivery.proof.longitude">
          <strong>Position :</strong>
          <a :href="`https://www.google.com/maps?q=${delivery.proof.latitude},${delivery.proof.longitude}`" target="_blank" rel="noopener">
            {{ delivery.proof.latitude }}, {{ delivery.proof.longitude }} <i class="fa-solid fa-up-right-from-square"></i>
          </a>
        </p>
        <div style="display: flex; gap: 16px; margin-top: 10px; flex-wrap: wrap;">
          <div v-if="delivery.proof.photo">
            <p style="margin: 0 0 4px; font-size: 12.5px; color: var(--ie-muted);">Photo du colis</p>
            <img :src="delivery.proof.photo" alt="Photo de livraison" class="ie-proof-thumb" />
          </div>
          <div v-if="delivery.proof.signature_image">
            <p style="margin: 0 0 4px; font-size: 12.5px; color: var(--ie-muted);">Signature</p>
            <img :src="delivery.proof.signature_image" alt="Signature du réceptionnaire" class="ie-proof-thumb" />
          </div>
        </div>
      </div>

      <div v-if="isAdmin && !['returning', 'returned', 'cancelled'].includes(delivery.status)" class="ie-card ie-card-body" style="margin-top: 20px;">
        <h3>Retour</h3>
        <p v-if="!delivery.return_record" style="color: var(--ie-muted); margin-bottom: 10px;">Aucun retour enregistré pour cette livraison.</p>
        <button v-if="!showReturnForm" class="ie-btn ie-btn-ghost ie-btn-sm" @click="showReturnForm = true">
          <i class="fa-solid fa-rotate-left"></i> Déclarer un retour
        </button>
        <div v-else style="margin-top: 10px;">
          <label class="ie-label">Motif</label>
          <select v-model="returnForm.reason" class="ie-select">
            <option v-for="r in RETURN_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
          <label class="ie-label" style="margin-top: 10px;">Constat / notes</label>
          <textarea v-model="returnForm.condition_notes" class="ie-input" rows="2"></textarea>
          <div class="ie-form-row" style="margin-top: 10px;">
            <div>
              <label class="ie-label">Statut du remboursement</label>
              <select v-model="returnForm.refund_status" class="ie-select">
                <option value="none">Aucun remboursement</option>
                <option value="pending">Remboursement en attente</option>
                <option value="done">Remboursé</option>
              </select>
            </div>
            <div>
              <label class="ie-label">Montant remboursé (XAF)</label>
              <input v-model.number="returnForm.refund_amount" type="number" min="0" class="ie-input" />
            </div>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 12px;">
            <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="returnSubmitting" @click="submitReturn">Confirmer le retour</button>
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="showReturnForm = false">Annuler</button>
          </div>
        </div>
      </div>

      <div v-if="delivery.return_record" class="ie-card ie-card-body" style="margin-top: 20px;">
        <h3>Retour enregistré</h3>
        <p><strong>Motif :</strong> {{ delivery.return_record.reason_display }}</p>
        <p v-if="delivery.return_record.condition_notes"><strong>Notes :</strong> {{ delivery.return_record.condition_notes }}</p>
        <p><strong>Remboursement :</strong> {{ delivery.return_record.refund_status_display }}
          <span v-if="delivery.return_record.refund_amount"> — {{ Number(delivery.return_record.refund_amount).toLocaleString('fr-FR') }} XAF</span>
        </p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-delivery-map { width: 100%; height: 220px; border-radius: 10px; border: 1px solid var(--ie-border); z-index: 0; }
.ie-signature-pad { border: 1px dashed var(--ie-border); border-radius: 8px; background: #fafbfc; touch-action: none; max-width: 100%; cursor: crosshair; }
.ie-proof-thumb { width: 140px; height: 100px; object-fit: cover; border-radius: 8px; border: 1px solid var(--ie-border); }
.ie-detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.ie-detail-grid h3 { margin: 0 0 10px; font-size: 15px; color: var(--ie-navy); }
.ie-detail-grid p { margin: 4px 0; font-size: 14px; }
.ie-plain-list { list-style: none; padding: 0; margin: 0; font-size: 14px; }
.ie-plain-list li { padding: 4px 0; border-bottom: 1px solid var(--ie-border); }
.ie-timeline { display: flex; flex-wrap: wrap; gap: 14px; }
.ie-timeline-step { display: flex; align-items: center; gap: 8px; opacity: 0.4; font-size: 13px; }
.ie-timeline-step.is-done { opacity: 1; }
.ie-timeline-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--ie-border); flex-shrink: 0; }
.ie-timeline-step.is-done .ie-timeline-dot { background: var(--ie-red); }
@media (max-width: 720px) {
  .ie-detail-grid { grid-template-columns: 1fr; }
}
</style>
