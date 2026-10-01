<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const TYPES = [
  { value: "company", label: "Entreprise" },
  { value: "partner", label: "Partenaire" },
  { value: "independent", label: "Indépendant" },
  { value: "internal", label: "Interne" },
];

const loading = ref(true);
const notFound = ref(false);
const carrierId = ref(null);
const zones = ref([]);
const submitting = ref(false);
const errorMessage = ref("");

const form = reactive({
  name: "", company_name: "", carrier_type: "independent", phone: "", whatsapp: "", email: "",
  address: "", service_zone: "", transport_type: "", id_number: "",
});

async function loadData() {
  loading.value = true;
  notFound.value = false;
  try {
    const [carrierRes, zonesRes] = await Promise.all([
      api.get("/deliveries/carriers/me/"), api.get("/deliveries/zones/"),
    ]);
    zones.value = zonesRes.data.results || zonesRes.data;
    const carrier = carrierRes.data;
    carrierId.value = carrier.id;
    Object.assign(form, {
      name: carrier.name, company_name: carrier.company_name, carrier_type: carrier.carrier_type,
      phone: carrier.phone, whatsapp: carrier.whatsapp, email: carrier.email, address: carrier.address,
      service_zone: carrier.service_zone || "", transport_type: carrier.transport_type, id_number: carrier.id_number,
    });
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
  } finally {
    loading.value = false;
  }
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = { ...form, service_zone: form.service_zone || null };
    await api.patch(`/deliveries/carriers/${carrierId.value}/`, payload);
    toast.success("Profil transporteur mis à jour.");
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ces modifications.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-truck-fast" style="color: var(--ie-red); margin-right: 8px;"></i>Mon profil transporteur</h1>
    <p class="ie-page-subtitle">Les informations affichées à l'administration et utilisées pour l'affectation de vos livraisons.</p>

    <div v-if="loading" class="ie-card ie-card-body" style="margin-top: 16px;">Chargement…</div>
    <EmptyState
      v-else-if="notFound" icon="fa-solid fa-truck-fast"
      text="Aucun profil transporteur n'est lié à votre compte. Contactez l'administration."
    />

    <div v-else class="ie-card ie-card-body" style="margin-top: 16px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom du transporteur</label>
            <input v-model="form.name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Type</label>
            <select v-model="form.carrier_type" class="ie-select">
              <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Nom de l'entreprise</label>
        <input v-model="form.company_name" class="ie-input" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Téléphone</label>
            <input v-model="form.phone" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">WhatsApp</label>
            <input v-model="form.whatsapp" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Email</label>
            <input v-model="form.email" type="email" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Zone de service</label>
            <select v-model="form.service_zone" class="ie-select">
              <option value="">—</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Adresse</label>
        <input v-model="form.address" class="ie-input" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Type de transport</label>
            <input v-model="form.transport_type" class="ie-input" placeholder="Ex : moto, camion, mixte..." />
          </div>
          <div>
            <label class="ie-label">Numéro d'identification / RCCM</label>
            <input v-model="form.id_number" class="ie-input" />
          </div>
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : "Enregistrer" }}
        </button>
      </form>
    </div>
  </div>
</template>
