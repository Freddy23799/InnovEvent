<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const loading = ref(true);
const notFound = ref(false);
const driverId = ref(null);
const submitting = ref(false);
const errorMessage = ref("");

const current = reactive({ photo: "", id_card_photo: "", license_photo: "" });
const photoFile = ref(null);
const idCardFile = ref(null);
const licenseFile = ref(null);

const form = reactive({
  full_name: "", phone: "", whatsapp: "", email: "", address: "",
  license_number: "", license_category: "", license_expiry: "",
});

async function loadData() {
  loading.value = true;
  notFound.value = false;
  try {
    const { data } = await api.get("/deliveries/drivers/me/");
    driverId.value = data.id;
    Object.assign(form, {
      full_name: data.full_name, phone: data.phone, whatsapp: data.whatsapp, email: data.email, address: data.address,
      license_number: data.license_number, license_category: data.license_category, license_expiry: data.license_expiry || "",
    });
    Object.assign(current, { photo: data.photo, id_card_photo: data.id_card_photo, license_photo: data.license_photo });
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
  } finally {
    loading.value = false;
  }
}

const documentsComplete = () => current.photo && current.id_card_photo && current.license_photo;

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = new FormData();
    Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ""));
    if (photoFile.value) payload.append("photo", photoFile.value);
    if (idCardFile.value) payload.append("id_card_photo", idCardFile.value);
    if (licenseFile.value) payload.append("license_photo", licenseFile.value);
    const { data } = await api.patch(`/deliveries/drivers/${driverId.value}/`, payload);
    Object.assign(current, { photo: data.photo, id_card_photo: data.id_card_photo, license_photo: data.license_photo });
    photoFile.value = null;
    idCardFile.value = null;
    licenseFile.value = null;
    toast.success("Profil chauffeur mis à jour.");
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
    <h1><i class="fa-solid fa-id-card" style="color: var(--ie-red); margin-right: 8px;"></i>Mon profil chauffeur</h1>
    <p class="ie-page-subtitle">Vos coordonnées et documents (CNI, permis) utilisés par l'administration et votre transporteur.</p>

    <div v-if="loading" class="ie-card ie-card-body" style="margin-top: 16px;">Chargement…</div>
    <EmptyState
      v-else-if="notFound" icon="fa-solid fa-id-card"
      text="Aucune fiche chauffeur n'est liée à votre compte. Contactez l'administration ou votre transporteur."
    />

    <template v-else>
      <div v-if="!documentsComplete()" class="ie-alert ie-alert-warning" style="margin-top: 16px;">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Votre profil est incomplet — merci de fournir votre photo, la photo de votre CNI et celle de votre permis de conduire.
      </div>

      <div class="ie-card ie-card-body" style="margin-top: 16px;">
        <form @submit.prevent="submitForm">
          <div class="ie-form-row">
            <div>
              <label class="ie-label">Nom complet</label>
              <input v-model="form.full_name" class="ie-input" required />
            </div>
            <div>
              <label class="ie-label">Téléphone</label>
              <input v-model="form.phone" class="ie-input" required />
            </div>
          </div>
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">WhatsApp</label>
              <input v-model="form.whatsapp" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Email</label>
              <input v-model="form.email" type="email" class="ie-input" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Adresse</label>
          <input v-model="form.address" class="ie-input" />
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Numéro de permis</label>
              <input v-model="form.license_number" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Expiration du permis</label>
              <input v-model="form.license_expiry" type="date" class="ie-input" />
            </div>
          </div>

          <h3 class="ie-doc-section-title">Documents obligatoires</h3>
          <div class="ie-form-row">
            <div>
              <label class="ie-label">Votre photo <span class="ie-required">*</span></label>
              <input type="file" accept="image/*" class="ie-input" @change="photoFile = $event.target.files[0] || null" />
              <img v-if="current.photo && !photoFile" :src="current.photo" alt="Photo actuelle" class="ie-doc-thumb" />
            </div>
            <div>
              <label class="ie-label">Photo de la CNI <span class="ie-required">*</span></label>
              <input type="file" accept="image/*" class="ie-input" @change="idCardFile = $event.target.files[0] || null" />
              <img v-if="current.id_card_photo && !idCardFile" :src="current.id_card_photo" alt="CNI actuelle" class="ie-doc-thumb" />
            </div>
          </div>
          <div style="margin-top: 14px; max-width: 240px;">
            <label class="ie-label">Photo du permis de conduire <span class="ie-required">*</span></label>
            <input type="file" accept="image/*" class="ie-input" @change="licenseFile = $event.target.files[0] || null" />
            <img v-if="current.license_photo && !licenseFile" :src="current.license_photo" alt="Permis actuel" class="ie-doc-thumb" />
          </div>

          <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
          <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
            {{ submitting ? "Enregistrement…" : "Enregistrer" }}
          </button>
        </form>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-doc-section-title { font-size: 13px; color: var(--ie-navy); margin: 20px 0 12px; font-weight: 700; }
.ie-doc-thumb { width: 90px; height: 60px; object-fit: cover; border-radius: 6px; border: 1px solid var(--ie-border); margin-top: 6px; }
.ie-required { color: var(--ie-red); }
</style>
