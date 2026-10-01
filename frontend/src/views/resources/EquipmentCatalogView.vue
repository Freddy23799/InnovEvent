<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const lightbox = useLightboxStore();
const toast = useToastStore();
const router = useRouter();

const auth = useAuthStore();
const canManage = computed(() => auth.role === "admin");
// Bouton visible même sans connexion : la garde de navigation redirige alors vers la connexion
// (redirection automatique vers cette page après authentification).
const canBook = computed(() => !auth.isAuthenticated || auth.role === "client" || auth.role === "organizer");
const canReview = computed(() => auth.role === "client" || auth.role === "organizer");
const canContactAdmin = computed(() => auth.isAuthenticated && auth.role !== "admin");

const CATEGORIES = [
  { value: "sound", label: "Sonorisation" },
  { value: "lighting", label: "Éclairage" },
  { value: "furniture", label: "Mobilier" },
  { value: "video", label: "Vidéo" },
  { value: "other", label: "Autre" },
];
const CATEGORY_LABELS = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]));

const equipment = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = {
  name: "", category: "sound", quantity_total: 1, price_per_unit: 0, description: "", is_active: true,
  discount_percent: 0, discount_label: "", discount_valid_until: "",
};
const form = reactive({ ...emptyForm });

function formatSlot(slot) {
  const opts = { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
  const start = new Date(slot.start).toLocaleString("fr-FR", opts);
  const end = new Date(slot.end).toLocaleString("fr-FR", opts);
  return `${start} → ${end}`;
}

function goToBooking(item) {
  router.push({ name: "bookings", query: { resource_type: "equipment", resource_id: item.id, quantity: 1 } });
}

const contactingAdmin = ref(false);

async function contactAdmin() {
  contactingAdmin.value = true;
  try {
    const { data } = await api.post("/messaging/conversations/contact-admin/");
    router.push({ name: "messaging", query: { conversation: data.id } });
  } finally {
    contactingAdmin.value = false;
  }
}

const expandedReviewsId = ref(null);
const reviewsByEquipment = reactive({});
const reviewSubmitting = ref(false);
const reviewError = ref("");
const reviewForm = reactive({ rating: 5, comment: "" });
const RATING_OPTIONS = [5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5];

function starIcons(rating) {
  const value = Number(rating) || 0;
  const icons = [];
  for (let i = 1; i <= 5; i++) {
    if (value >= i) icons.push("fa-solid fa-star");
    else if (value >= i - 0.5) icons.push("fa-solid fa-star-half-stroke");
    else icons.push("fa-regular fa-star");
  }
  return icons;
}

function myReview(equipmentId) {
  const list = reviewsByEquipment[equipmentId] || [];
  return list.find((r) => r.author === auth.user?.id) || null;
}

async function toggleReviews(item) {
  if (expandedReviewsId.value === item.id) {
    expandedReviewsId.value = null;
    return;
  }
  expandedReviewsId.value = item.id;
  reviewError.value = "";
  if (!reviewsByEquipment[item.id]) {
    const { data } = await api.get("/reviews/equipment/", { params: { equipment: item.id } });
    reviewsByEquipment[item.id] = data.results || data;
  }
  const mine = myReview(item.id);
  reviewForm.rating = mine ? Number(mine.rating) : 5;
  reviewForm.comment = mine ? mine.comment : "";
}

async function submitReview(item) {
  reviewError.value = "";
  reviewSubmitting.value = true;
  try {
    const mine = myReview(item.id);
    if (mine) {
      await api.patch(`/reviews/equipment/${mine.id}/`, { rating: reviewForm.rating, comment: reviewForm.comment });
    } else {
      await api.post("/reviews/equipment/", { equipment: item.id, rating: reviewForm.rating, comment: reviewForm.comment });
    }
    const { data } = await api.get("/reviews/equipment/", { params: { equipment: item.id } });
    reviewsByEquipment[item.id] = data.results || data;
    await loadEquipment();
  } catch (e) {
    reviewError.value = e?.response?.data?.detail?.non_field_errors?.[0] || e?.response?.data?.detail || "Impossible d'enregistrer votre avis.";
  } finally {
    reviewSubmitting.value = false;
  }
}

async function deleteMyReview(item) {
  const mine = myReview(item.id);
  if (!mine || !confirm("Supprimer votre avis ?")) return;
  await api.delete(`/reviews/equipment/${mine.id}/`);
  reviewsByEquipment[item.id] = (reviewsByEquipment[item.id] || []).filter((r) => r.id !== mine.id);
  reviewForm.rating = 5;
  reviewForm.comment = "";
  await loadEquipment();
}

async function loadEquipment() {
  loading.value = true;
  try {
    const { data } = await api.get("/equipment/", { params: { is_active: true } });
    equipment.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(item) {
  Object.assign(form, item);
  editingId.value = item.id;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  // discount_valid_until est un DateField côté API : une chaîne vide est rejetée
  // (400), il faut soit null (JSON), soit omettre le champ (FormData).
  const base = { ...form, discount_valid_until: form.discount_valid_until || null };
  if (!photoFile.value) return base;
  const payload = new FormData();
  Object.entries(base).forEach(([key, value]) => {
    if (key === "discount_valid_until" && !value) return;
    payload.append(key, value ?? "");
  });
  payload.append("photo", photoFile.value);
  return payload;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/equipment/${editingId.value}/`, payload);
    } else {
      await api.post("/equipment/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Équipement enregistré.");
    await loadEquipment();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce matériel.";
  } finally {
    submitting.value = false;
  }
}

async function deleteEquipment(item) {
  if (!confirm(`Supprimer « ${item.name} » ?`)) return;
  await api.delete(`/equipment/${item.id}/`);
  await loadEquipment();
}

onMounted(loadEquipment);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-sliders" style="color: var(--ie-red); margin-right: 8px;"></i>Consulter équipements</h1>
        <p class="ie-page-subtitle">Catalogue du matériel disponible pour vos événements.</p>
      </div>
      <div class="ie-page-header-actions">
        <button v-if="canManage" class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom</label>
            <input v-model="form.name" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select">
              <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Quantité initiale</label>
            <input v-model.number="form.quantity_total" type="number" min="1" class="ie-input" required :disabled="!!editingId" />
            <p v-if="editingId" class="ie-field-hint">
              Le stock se modifie désormais via <router-link :to="{ name: 'stock-movements' }">Mouvements de stock</router-link>.
            </p>
          </div>
          <div>
            <label class="ie-label">Prix / unité (XAF)</label>
            <input v-model.number="form.price_per_unit" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Actif
        </label>
        <div class="ie-discount-fieldset">
          <p class="ie-discount-fieldset-title"><i class="fa-solid fa-tag"></i> Offre promotionnelle (optionnel)</p>
          <div class="ie-form-row">
            <div>
              <label class="ie-label">Réduction (%)</label>
              <input v-model.number="form.discount_percent" type="number" min="0" max="90" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Libellé de l'offre</label>
              <input v-model="form.discount_label" class="ie-input" placeholder="Ex: Offre de rentrée" />
            </div>
          </div>
          <label class="ie-label" style="margin-top: 10px;">Valable jusqu'au</label>
          <input v-model="form.discount_valid_until" type="date" class="ie-input" />
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div v-if="loading" class="ie-catalog-grid">
      <div v-for="i in 3" :key="i" class="ie-card ie-catalog-card">
        <div class="ie-skeleton" style="height: 140px; border-radius: 0;"></div>
        <div class="ie-card-body">
          <div class="ie-skeleton" style="height: 14px; width: 60%; margin-bottom: 8px;"></div>
          <div class="ie-skeleton" style="height: 12px; width: 90%;"></div>
        </div>
      </div>
    </div>

    <div v-else-if="equipment.length" class="ie-catalog-grid">
      <div v-for="item in equipment" :key="item.id" class="ie-card ie-catalog-card">
        <div class="ie-catalog-photo">
          <img v-if="item.photo" :src="item.photo" :alt="item.name" class="ie-zoomable" @click="lightbox.open(item.photo, item.name)" />
          <i v-else class="fa-solid fa-sliders"></i>
          <span class="ie-badge ie-catalog-availability" :class="item.is_available ? 'ie-badge-success' : 'ie-badge-danger'">
            {{ item.is_available ? "Disponible" : "Épuisé actuellement" }}
          </span>
          <div v-if="item.has_active_discount" class="ie-catalog-discount-badge">
            <span class="ie-catalog-discount-percent">-{{ item.discount_percent }}%</span>
            <span v-if="item.discount_label" class="ie-catalog-discount-label">{{ item.discount_label }}</span>
          </div>
        </div>
        <div class="ie-card-body">
          <h3 class="ie-catalog-title">{{ item.name }}</h3>
          <div class="ie-rating-line">
            <span class="ie-rating-stars">
              <i v-for="(icon, i) in starIcons(item.average_rating)" :key="i" :class="icon"></i>
            </span>
            <span v-if="item.review_count" class="ie-rating-count">{{ item.average_rating }} ({{ item.review_count }} avis)</span>
            <span v-else class="ie-rating-count">Aucun avis</span>
          </div>
          <p class="ie-catalog-desc">{{ item.description || "Aucune description fournie." }}</p>          <div class="ie-catalog-meta">
            <span><i class="fa-solid fa-tag"></i> {{ CATEGORY_LABELS[item.category] || item.category }}</span>
            <span v-if="!item.has_active_discount"><i class="fa-solid fa-coins"></i> {{ Number(item.price_per_unit).toLocaleString('fr-FR') }} XAF / unité</span>
            <span v-else class="ie-catalog-price-line">
              <i class="fa-solid fa-coins"></i>
              <span class="ie-catalog-price-original">{{ Number(item.price_per_unit).toLocaleString('fr-FR') }} XAF</span>
              <span class="ie-catalog-price-discounted">{{ Number(item.discounted_price_per_unit).toLocaleString('fr-FR') }} XAF / unité</span>
            </span>
            <span v-if="item.has_active_discount && item.discount_valid_until" class="ie-catalog-discount-until">
              <i class="fa-solid fa-hourglass-half"></i> Offre valable jusqu'au {{ new Date(item.discount_valid_until).toLocaleDateString('fr-FR') }}
            </span>
            <span><i class="fa-solid fa-cubes"></i> {{ item.quantity_total }} unité(s) au total</span>
          </div>
          <div v-if="item.upcoming_unavailability?.length" class="ie-catalog-unavail">
            <span class="ie-catalog-unavail-label"><i class="fa-solid fa-calendar-xmark"></i> Prochaines indisponibilités</span>
            <span v-for="(slot, i) in item.upcoming_unavailability" :key="i" class="ie-catalog-unavail-slot">{{ formatSlot(slot) }}</span>
          </div>
          <button v-if="canBook" class="ie-btn ie-btn-primary ie-btn-sm" style="width: 100%; margin-top: 10px;" @click="goToBooking(item)">
            <i class="fa-solid fa-calendar-plus"></i> Réserver ce matériel
          </button>
          <button v-if="auth.isAuthenticated" class="ie-btn ie-btn-ghost ie-btn-sm" style="width: 100%; margin-top: 6px;" @click="toggleReviews(item)">
            <i class="fa-solid fa-comment-dots"></i> {{ expandedReviewsId === item.id ? "Masquer les avis" : "Voir les avis" }}
          </button>
          <div v-if="expandedReviewsId === item.id" class="ie-reviews-panel">
            <div v-if="!(reviewsByEquipment[item.id] || []).length" class="ie-reviews-empty">Aucun avis pour le moment.</div>
            <div v-for="review in reviewsByEquipment[item.id] || []" :key="review.id" class="ie-review-item">
              <div class="ie-review-head">
                <strong>{{ review.author_name }}</strong>
                <span class="ie-rating-stars ie-rating-stars-sm">
                  <i v-for="(icon, i) in starIcons(review.rating)" :key="i" :class="icon"></i>
                </span>
              </div>
              <p v-if="review.comment" class="ie-review-comment">{{ review.comment }}</p>
              <span class="ie-review-date">{{ new Date(review.created_at).toLocaleDateString('fr-FR') }}</span>
            </div>

            <div v-if="canReview" class="ie-review-form">
              <label class="ie-label">{{ myReview(item.id) ? "Modifier mon avis" : "Laisser un avis" }}</label>
              <select v-model.number="reviewForm.rating" class="ie-select">
                <option v-for="opt in RATING_OPTIONS" :key="opt" :value="opt">{{ opt }} ★</option>
              </select>
              <textarea v-model="reviewForm.comment" class="ie-input" rows="2" placeholder="Votre commentaire (optionnel)" style="margin-top: 8px;"></textarea>
              <p v-if="reviewError" class="ie-alert ie-alert-danger" style="margin-top: 8px;">{{ reviewError }}</p>
              <div class="ie-table-actions" style="margin-top: 8px;">
                <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="reviewSubmitting" @click="submitReview(item)">
                  {{ reviewSubmitting ? "Envoi…" : myReview(item.id) ? "Mettre à jour" : "Publier" }}
                </button>
                <button v-if="myReview(item.id)" class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteMyReview(item)">Supprimer</button>
              </div>
            </div>
          </div>
          <button v-if="canContactAdmin" class="ie-btn ie-btn-ghost ie-btn-sm" style="width: 100%; margin-top: 6px;" :disabled="contactingAdmin" @click="contactAdmin">
            <i class="fa-solid fa-headset"></i> {{ contactingAdmin ? "Connexion…" : "Contacter l'administration" }}
          </button>
          <div v-if="canManage" class="ie-table-actions" style="margin-top: 14px;">
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(item)">Modifier</button>
            <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteEquipment(item)">Supprimer</button>
          </div>
        </div>
      </div>
    </div>
    <EmptyState v-else icon="fa-solid fa-sliders" text="Aucun équipement disponible." />
  </div>
</template>

<style scoped>
.ie-catalog-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 18px; }
.ie-catalog-card { overflow: hidden; display: flex; flex-direction: column; }
.ie-catalog-photo {
  height: 140px; background: var(--ie-navy-soft); position: relative;
  display: flex; align-items: center; justify-content: center;
}
.ie-catalog-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-catalog-photo i { font-size: 34px; color: var(--ie-navy); opacity: 0.35; }
.ie-catalog-availability { position: absolute; top: 10px; right: 10px; }
.ie-catalog-title { margin: 0 0 6px; font-size: 14.5px; color: var(--ie-navy); }
.ie-catalog-desc { font-size: 12.5px; color: var(--ie-muted); margin: 0 0 12px; line-height: 1.5; min-height: 36px; }
.ie-catalog-meta { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--ie-ink); }
.ie-catalog-meta i { color: var(--ie-red); width: 14px; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
.ie-field-hint a { color: var(--ie-red); font-weight: 600; }

.ie-rating-line { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ie-rating-stars { color: #F5A623; font-size: 13px; letter-spacing: 1px; }
.ie-rating-stars-sm { font-size: 11px; }
.ie-rating-count { font-size: 11.5px; color: var(--ie-muted); }

.ie-reviews-panel {
  margin-top: 10px; padding: 12px; border: 1px solid var(--ie-line); border-radius: 8px;
  background: #fafbfc; display: flex; flex-direction: column; gap: 10px;
}
.ie-reviews-empty { font-size: 12px; color: var(--ie-muted); }
.ie-review-item { border-bottom: 1px solid var(--ie-line); padding-bottom: 8px; }
.ie-review-item:last-of-type { border-bottom: none; padding-bottom: 0; }
.ie-review-head { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; }
.ie-review-comment { font-size: 12px; color: var(--ie-ink); margin: 4px 0; }
.ie-review-date { font-size: 10.5px; color: var(--ie-muted); }
.ie-review-form { border-top: 1px dashed var(--ie-line); padding-top: 10px; }
</style>
