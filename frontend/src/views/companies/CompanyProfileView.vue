<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const loading = ref(true);
const notFound = ref(false);
const companyId = ref(null);
const submitting = ref(false);
const errorMessage = ref("");
const documents = ref([]);
const documentFile = ref(null);
const documentLabel = ref("");
const uploadingDocument = ref(false);

const VERIFICATION_LABELS = {
  not_verified: "Non vérifié", profile_verified: "Profil vérifié", identity_verified: "Identité vérifiée",
  company_verified: "Entreprise vérifiée", portfolio_verified: "Portfolio vérifié", professional_partner: "Partenaire professionnel",
};

const form = reactive({
  raison_sociale: "", activite: "", rccm: "", niu: "", adresse: "", representant: "", phone: "", email: "",
});
const verificationStatus = ref("not_verified");

async function loadData() {
  loading.value = true;
  notFound.value = false;
  try {
    const { data } = await api.get("/companies/me/");
    companyId.value = data.id;
    Object.assign(form, {
      raison_sociale: data.raison_sociale, activite: data.activite, rccm: data.rccm, niu: data.niu,
      adresse: data.adresse, representant: data.representant, phone: data.phone, email: data.email,
    });
    verificationStatus.value = data.verification_status;
    documents.value = data.documents;
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
    await api.patch(`/companies/${companyId.value}/`, form);
    toast.success("Profil entreprise mis à jour.");
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ces modifications.";
  } finally {
    submitting.value = false;
  }
}

async function addDocument() {
  if (!documentFile.value) return;
  uploadingDocument.value = true;
  try {
    const payload = new FormData();
    payload.append("profile", companyId.value);
    payload.append("file", documentFile.value);
    payload.append("label", documentLabel.value);
    const { data } = await api.post("/companies/documents/", payload);
    documents.value.unshift(data);
    documentFile.value = null;
    documentLabel.value = "";
    toast.success("Document ajouté.");
  } finally {
    uploadingDocument.value = false;
  }
}

async function removeDocument(doc) {
  await api.delete(`/companies/documents/${doc.id}/`);
  documents.value = documents.value.filter((d) => d.id !== doc.id);
}

onMounted(loadData);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-building" style="color: var(--ie-red); margin-right: 8px;"></i>Mon profil entreprise</h1>
    <p class="ie-page-subtitle">Informations légales et documents justificatifs utilisés par l'administration pour la vérification.</p>

    <div v-if="loading" class="ie-card ie-card-body" style="margin-top: 16px;">Chargement…</div>
    <EmptyState
      v-else-if="notFound" icon="fa-solid fa-building"
      text="Aucun profil entreprise n'est lié à votre compte."
    />

    <template v-else>
      <p class="ie-alert" style="margin-top: 16px;" :class="verificationStatus === 'not_verified' ? 'ie-alert-warning' : 'ie-alert-success'">
        <i class="fa-solid fa-shield-halved"></i> Statut de vérification : <strong>{{ VERIFICATION_LABELS[verificationStatus] }}</strong>
      </p>

      <div class="ie-card ie-card-body" style="margin-top: 16px;">
        <form @submit.prevent="submitForm">
          <label class="ie-label">Raison sociale</label>
          <input v-model="form.raison_sociale" class="ie-input" required />
          <label class="ie-label" style="margin-top: 14px;">Activité</label>
          <input v-model="form.activite" class="ie-input" />
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">RCCM</label>
              <input v-model="form.rccm" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">NIU</label>
              <input v-model="form.niu" class="ie-input" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Adresse</label>
          <input v-model="form.adresse" class="ie-input" />
          <label class="ie-label" style="margin-top: 14px;">Représentant légal</label>
          <input v-model="form.representant" class="ie-input" />
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Téléphone</label>
              <input v-model="form.phone" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Email</label>
              <input v-model="form.email" type="email" class="ie-input" />
            </div>
          </div>

          <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
          <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
            {{ submitting ? "Enregistrement…" : "Enregistrer" }}
          </button>
        </form>
      </div>

      <div class="ie-card ie-card-body" style="margin-top: 16px;">
        <h3 class="ie-doc-section-title">Documents justificatifs</h3>
        <ul class="ie-document-list">
          <li v-for="doc in documents" :key="doc.id">
            <a :href="doc.file" target="_blank" rel="noopener"><i class="fa-solid fa-file-lines"></i> {{ doc.label || "Document" }}</a>
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="removeDocument(doc)"><i class="fa-solid fa-trash"></i></button>
          </li>
        </ul>
        <div class="ie-form-row" style="margin-top: 12px;">
          <div>
            <label class="ie-label">Fichier (RCCM, NIU, statuts...)</label>
            <input type="file" class="ie-input" @change="documentFile = $event.target.files[0] || null" />
          </div>
          <div>
            <label class="ie-label">Libellé (optionnel)</label>
            <input v-model="documentLabel" class="ie-input" placeholder="Ex : Attestation RCCM" />
          </div>
        </div>
        <button class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 10px;" :disabled="!documentFile || uploadingDocument" @click="addDocument">
          <i class="fa-solid fa-plus"></i> Ajouter le document
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-doc-section-title { font-size: 13px; color: var(--ie-navy); margin: 0 0 12px; font-weight: 700; }
.ie-document-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.ie-document-list li { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border: 1px solid var(--ie-border); border-radius: 8px; font-size: 13px; }
.ie-document-list a { color: var(--ie-navy); font-weight: 600; }
</style>
