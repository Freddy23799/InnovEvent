<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const loading = ref(true);
const notFound = ref(false);
const talentId = ref(null);
const submitting = ref(false);
const errorMessage = ref("");
const currentPhoto = ref("");
const photoFile = ref(null);
const portfolioItems = ref([]);
const portfolioFile = ref(null);
const portfolioCaption = ref("");
const uploadingPortfolio = ref(false);

const VERIFICATION_LABELS = {
  not_verified: "Non vérifié", profile_verified: "Profil vérifié", identity_verified: "Identité vérifiée",
  company_verified: "Entreprise vérifiée", portfolio_verified: "Portfolio vérifié", professional_partner: "Partenaire professionnel",
};

const form = reactive({
  full_name: "", formation: "", competences: "", experience: "", city: "", disponibilite: "to_define", opportunity_type: "one_off",
});
const verificationStatus = ref("not_verified");

async function loadData() {
  loading.value = true;
  notFound.value = false;
  try {
    const { data } = await api.get("/talents/me/");
    talentId.value = data.id;
    Object.assign(form, {
      full_name: data.full_name, formation: data.formation, competences: data.competences, experience: data.experience,
      city: data.city, disponibilite: data.disponibilite, opportunity_type: data.opportunity_type,
    });
    currentPhoto.value = data.photo;
    verificationStatus.value = data.verification_status;
    portfolioItems.value = data.portfolio_items;
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
    const payload = new FormData();
    Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ""));
    if (photoFile.value) payload.append("photo", photoFile.value);
    const { data } = await api.patch(`/talents/${talentId.value}/`, payload);
    currentPhoto.value = data.photo;
    photoFile.value = null;
    toast.success("Profil talent mis à jour.");
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ces modifications.";
  } finally {
    submitting.value = false;
  }
}

async function addPortfolioItem() {
  if (!portfolioFile.value) return;
  uploadingPortfolio.value = true;
  try {
    const payload = new FormData();
    payload.append("profile", talentId.value);
    payload.append("image", portfolioFile.value);
    payload.append("caption", portfolioCaption.value);
    const { data } = await api.post("/talents/portfolio/", payload);
    portfolioItems.value.unshift(data);
    portfolioFile.value = null;
    portfolioCaption.value = "";
    toast.success("Élément de portfolio ajouté.");
  } finally {
    uploadingPortfolio.value = false;
  }
}

async function removePortfolioItem(item) {
  await api.delete(`/talents/portfolio/${item.id}/`);
  portfolioItems.value = portfolioItems.value.filter((i) => i.id !== item.id);
}

onMounted(loadData);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-star" style="color: var(--ie-red); margin-right: 8px;"></i>Mon profil talent</h1>
    <p class="ie-page-subtitle">Vos informations, visibles dans l'annuaire public « Talents » de la page d'accueil.</p>

    <div v-if="loading" class="ie-card ie-card-body" style="margin-top: 16px;">Chargement…</div>
    <EmptyState
      v-else-if="notFound" icon="fa-solid fa-star"
      text="Aucun profil talent n'est lié à votre compte."
    />

    <template v-else>
      <p class="ie-alert" style="margin-top: 16px;" :class="verificationStatus === 'not_verified' ? 'ie-alert-warning' : 'ie-alert-success'">
        <i class="fa-solid fa-shield-halved"></i> Statut de vérification : <strong>{{ VERIFICATION_LABELS[verificationStatus] }}</strong>
      </p>

      <div class="ie-card ie-card-body" style="margin-top: 16px;">
        <form @submit.prevent="submitForm">
          <div class="ie-form-row">
            <div>
              <label class="ie-label">Nom complet</label>
              <input v-model="form.full_name" class="ie-input" required />
            </div>
            <div>
              <label class="ie-label">Ville</label>
              <input v-model="form.city" class="ie-input" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 14px;">Formation</label>
          <input v-model="form.formation" class="ie-input" />
          <label class="ie-label" style="margin-top: 14px;">Compétences</label>
          <input v-model="form.competences" class="ie-input" placeholder="Séparées par des virgules" />
          <label class="ie-label" style="margin-top: 14px;">Expérience</label>
          <textarea v-model="form.experience" class="ie-input" rows="3"></textarea>
          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Disponibilité</label>
              <select v-model="form.disponibilite" class="ie-select">
                <option value="immediate">Immédiate</option>
                <option value="within_month">Sous 1 mois</option>
                <option value="to_define">À définir</option>
              </select>
            </div>
            <div>
              <label class="ie-label">Type d'opportunité recherché</label>
              <select v-model="form.opportunity_type" class="ie-select">
                <option value="one_off">Mission ponctuelle</option>
                <option value="fixed_term">CDD</option>
                <option value="permanent">CDI</option>
                <option value="internship">Stage</option>
                <option value="freelance">Freelance</option>
              </select>
            </div>
          </div>

          <label class="ie-label" style="margin-top: 14px;">Photo</label>
          <input type="file" accept="image/*" class="ie-input" @change="photoFile = $event.target.files[0] || null" />
          <img v-if="currentPhoto && !photoFile" :src="currentPhoto" alt="Photo actuelle" class="ie-doc-thumb" />

          <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
          <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
            {{ submitting ? "Enregistrement…" : "Enregistrer" }}
          </button>
        </form>
      </div>

      <div class="ie-card ie-card-body" style="margin-top: 16px;">
        <h3 class="ie-doc-section-title">Portfolio</h3>
        <div class="ie-portfolio-grid">
          <div v-for="item in portfolioItems" :key="item.id" class="ie-portfolio-item">
            <img :src="item.image" :alt="item.caption" />
            <button type="button" class="ie-portfolio-remove" @click="removePortfolioItem(item)"><i class="fa-solid fa-xmark"></i></button>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 12px;">
          <div>
            <label class="ie-label">Image</label>
            <input type="file" accept="image/*" class="ie-input" @change="portfolioFile = $event.target.files[0] || null" />
          </div>
          <div>
            <label class="ie-label">Légende (optionnel)</label>
            <input v-model="portfolioCaption" class="ie-input" />
          </div>
        </div>
        <button class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 10px;" :disabled="!portfolioFile || uploadingPortfolio" @click="addPortfolioItem">
          <i class="fa-solid fa-plus"></i> Ajouter au portfolio
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-doc-section-title { font-size: 13px; color: var(--ie-navy); margin: 0 0 12px; font-weight: 700; }
.ie-doc-thumb { width: 90px; height: 90px; object-fit: cover; border-radius: 8px; border: 1px solid var(--ie-border); margin-top: 8px; }
.ie-portfolio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 10px; }
.ie-portfolio-item { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; border: 1px solid var(--ie-border); }
.ie-portfolio-item img { width: 100%; height: 100%; object-fit: cover; }
.ie-portfolio-remove {
  position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; border-radius: 50%; border: 0;
  background: rgba(0, 0, 0, 0.6); color: #fff; cursor: pointer; font-size: 11px;
}
</style>
