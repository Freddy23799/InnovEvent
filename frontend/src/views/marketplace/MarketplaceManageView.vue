<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import { SALE_CATEGORIES } from "../../data/saleCategories";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const MARKETPLACE_TYPES = [
  { value: "sale", label: "Marketplace vente" },
  { value: "interior_design", label: "Décoration & design intérieur" },
  { value: "actors", label: "Marketplace des acteurs" },
];

const listings = ref([]);
const providers = ref([]);
const inventory = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);
// Boutique : photos supplémentaires (galerie de la fiche produit).
const extraPhotos = ref([]);
const extraPhotoFiles = ref([]);

const emptyForm = {
  marketplace_type: "sale", provider: "", title: "", description: "",
  price: 0, currency: "XAF", is_active: true, requires_subscription: false, order: 0,
  category: "", subcategory: "", stock: null,
  is_for_sale: true, is_for_rent: true, rental_price_per_day: null, equipment: "",
};
const form = reactive({ ...emptyForm });
// Même règle que le serveur : 10 % du prix d'achat, arrondi à 50 FCFA.
const autoRentalPrice = computed(() => Math.max(Math.round((Number(form.price) || 0) * 0.1 / 50) * 50, 50));
const subcategoryOptions = computed(() => SALE_CATEGORIES.find((c) => c.value === form.category)?.subcategories || []);

// Par défaut, la Marketplace vente est en accès libre (mode client simple) ; les
// deux autres nécessitent un abonnement — l'administrateur peut toujours changer
// ce réglage pour chaque annonce individuellement.
function onTypeChange() {
  form.requires_subscription = form.marketplace_type !== "sale";
}

async function loadData() {
  loading.value = true;
  try {
    const [listingsRes, providersRes, inventoryRes] = await Promise.all([
      api.get("/marketplace/listings/"),
      api.get("/providers/"),
      api.get("/equipment/").catch(() => ({ data: [] })),
    ]);
    listings.value = listingsRes.data.results || listingsRes.data;
    providers.value = providersRes.data.results || providersRes.data;
    inventory.value = inventoryRes.data.results || inventoryRes.data;
  } finally {
    loading.value = false;
  }
}

function typeLabel(value) {
  return MARKETPLACE_TYPES.find((t) => t.value === value)?.label || value;
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  photoFile.value = null;
  extraPhotos.value = [];
  extraPhotoFiles.value = [];
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(listing) {
  Object.assign(form, { ...listing, provider: listing.provider || "", category: listing.category || "", subcategory: listing.subcategory || "", equipment: listing.equipment || "" });
  editingId.value = listing.id;
  photoFile.value = null;
  extraPhotos.value = [...(listing.photos || [])];
  extraPhotoFiles.value = [];
  errorMessage.value = "";
  showForm.value = true;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  // Champs calculés renvoyés par l'API : jamais renvoyés au serveur.
  const { photos, photo, category_display, provider_name, created_by_name, is_owner, equipment_name, available_stock, ...fields } = form;
  const base = {
    ...fields, provider: form.provider || null, stock: form.stock === "" ? null : form.stock,
    equipment: form.equipment || null,
    rental_price_per_day: form.is_for_rent && form.rental_price_per_day !== "" ? form.rental_price_per_day : null,
  };
  if (!photoFile.value) return base;
  const payload = new FormData();
  Object.entries(base).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    payload.append(key, value);
  });
  payload.append("photo", photoFile.value);
  return payload;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    let listingId = editingId.value;
    if (editingId.value) {
      await api.patch(`/marketplace/listings/${editingId.value}/`, payload);
    } else {
      const { data } = await api.post("/marketplace/listings/", payload);
      listingId = data.id;
    }
    for (const [index, file] of extraPhotoFiles.value.entries()) {
      const photoPayload = new FormData();
      photoPayload.append("listing", listingId);
      photoPayload.append("image", file);
      photoPayload.append("order", extraPhotos.value.length + index);
      await api.post("/marketplace/listing-photos/", photoPayload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Annonce enregistrée.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette annonce.";
  } finally {
    submitting.value = false;
  }
}

function onExtraPhotosChange(e) {
  extraPhotoFiles.value = Array.from(e.target.files || []);
}

async function removeExtraPhoto(photo) {
  await api.delete(`/marketplace/listing-photos/${photo.id}/`);
  extraPhotos.value = extraPhotos.value.filter((p) => p.id !== photo.id);
  await loadData();
}

async function toggleActive(listing) {
  await api.patch(`/marketplace/listings/${listing.id}/`, { is_active: !listing.is_active });
  await loadData();
}

async function deleteListing(listing) {
  if (!confirm(`Supprimer définitivement « ${listing.title} » ? Préférez « Masquer » si vous pensez la republier un jour.`)) return;
  await api.delete(`/marketplace/listings/${listing.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-store" style="color: var(--ie-red); margin-right: 8px;"></i>Marketplaces Premium</h1>
        <p class="ie-page-subtitle">Annonces des 3 marketplaces réservés aux clients abonnés. Masquez une annonce plutôt que de la supprimer si vous comptez la republier.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle annonce" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Marketplace</label>
            <select v-model="form.marketplace_type" class="ie-select" @change="onTypeChange">
              <option v-for="t in MARKETPLACE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Prestataire associé (optionnel)</label>
            <select v-model="form.provider" class="ie-select">
              <option value="">— Aucun —</option>
              <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Titre</label>
        <input v-model="form.title" class="ie-input" required placeholder="Ex : Chaises Chiavari dorées (lot de 50)" />
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix</label>
            <input v-model.number="form.price" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Devise</label>
            <select v-model="form.currency" class="ie-select">
              <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
            </select>
          </div>
        </div>
        <div v-if="form.marketplace_type === 'sale'" class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Rayon de la boutique</label>
            <select v-model="form.category" class="ie-select" @change="form.subcategory = ''">
              <option value="">— Choisir —</option>
              <option v-for="c in SALE_CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.subcategory" class="ie-select" :disabled="!subcategoryOptions.length">
              <option value="">— {{ subcategoryOptions.length ? "Choisir" : "Aucune" }} —</option>
              <option v-for="sc in subcategoryOptions" :key="sc.value" :value="sc.value">{{ sc.label }}</option>
            </select>
          </div>
        </div>
        <div v-if="form.marketplace_type === 'sale'" class="ie-offer-box">
          <strong>Achat et location</strong>
          <div class="ie-form-row" style="margin-top: 10px;">
            <label class="ie-offer-check"><input v-model="form.is_for_sale" type="checkbox" /> Proposé à l'achat (au prix ci-dessus)</label>
            <label class="ie-offer-check"><input v-model="form.is_for_rent" type="checkbox" /> Proposé à la location</label>
          </div>
          <div v-if="form.is_for_rent" style="margin-top: 10px; max-width: 280px;">
            <label class="ie-label">Prix de location par jour et par pièce (facultatif)</label>
            <input v-model.number="form.rental_price_per_day" type="number" min="0" class="ie-input" :placeholder="`Auto : ${autoRentalPrice.toLocaleString('fr-FR')} FCFA`" />
            <p class="ie-field-hint">Vide = 10 % du prix d'achat par jour, calculé automatiquement.</p>
          </div>
          <div class="ie-form-row" style="margin-top: 12px;">
            <div>
              <label class="ie-label">Article d'inventaire lié (recommandé)</label>
              <select v-model="form.equipment" class="ie-select">
                <option value="">— Aucun : stock géré ici —</option>
                <option v-for="e in inventory" :key="e.id" :value="e.id">{{ e.name }} ({{ e.quantity_total }} en stock)</option>
              </select>
              <p class="ie-field-hint">Le stock suit alors la gestion de stock : ventes, casse et pertes y sont enregistrées automatiquement.</p>
            </div>
            <div v-if="!form.equipment">
              <label class="ie-label">Nombre de pièces en stock</label>
              <input v-model.number="form.stock" type="number" min="0" class="ie-input" placeholder="Vide = stock non suivi" />
              <p class="ie-field-hint">Diminue à chaque vente ; réservé pendant les locations.</p>
            </div>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">{{ form.marketplace_type === 'sale' ? "Photo principale" : "Photo" }}</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <template v-if="form.marketplace_type === 'sale'">
          <label class="ie-label" style="margin-top: 14px;">Photos supplémentaires (galerie du produit)</label>
          <div v-if="extraPhotos.length" class="ie-extra-photos">
            <div v-for="p in extraPhotos" :key="p.id" class="ie-extra-photo">
              <img v-img="p.image" alt="" />
              <button type="button" aria-label="Supprimer cette photo" @click="removeExtraPhoto(p)"><i class="fa-solid fa-xmark"></i></button>
            </div>
          </div>
          <input type="file" accept="image/*" multiple class="ie-input" @change="onExtraPhotosChange" />
          <p class="ie-field-hint">Plusieurs photos possibles — ajoutées à l'enregistrement.</p>
        </template>
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Annonce visible (décocher pour masquer sans supprimer)
        </label>
        <div v-if="form.marketplace_type !== 'sale'" class="ie-discount-fieldset">
          <label style="display:flex; align-items:center; gap:8px; font-size:14px;">
            <input v-model="form.requires_subscription" type="checkbox" />
            Réservée aux comptes abonnés à ce marketplace
          </label>
          <p class="ie-field-hint" style="margin-top: 8px;">
            Décoché = accès libre : visible par tout client connecté, sans abonnement (« mode client simple »).
            Coché = visible uniquement par les clients ayant souscrit un abonnement à « {{ MARKETPLACE_TYPES.find((t) => t.value === form.marketplace_type)?.label }} ».
          </p>
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="listings.length">
        <table class="ie-table">
          <thead>
            <tr>
              <th>Marketplace</th><th>Titre</th><th>Prestataire</th><th class="ie-num">Prix</th><th>Accès</th><th>Statut</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="listing in listings" :key="listing.id">
              <td>{{ typeLabel(listing.marketplace_type) }}</td>
              <td><strong>{{ listing.title }}</strong></td>
              <td>{{ listing.provider_name || listing.created_by_name || "—" }}</td>
              <td class="ie-num">{{ Number(listing.price).toLocaleString('fr-FR') }} {{ listing.currency }}</td>
              <td>
                <span class="ie-badge" :class="listing.requires_subscription && listing.marketplace_type !== 'sale' ? 'ie-badge-neutral' : 'ie-badge-success'">
                  {{ listing.marketplace_type === 'sale'
                    ? [listing.is_for_sale ? "Achat" : "", listing.is_for_rent ? "Location" : ""].filter(Boolean).join(" + ") + (listing.available_stock !== null ? ` · ${listing.available_stock} dispo.` : "")
                    : listing.requires_subscription ? "Abonnement requis" : "Libre" }}
                </span>
              </td>
              <td>
                <span class="ie-badge" :class="listing.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">
                  {{ listing.is_active ? "Visible" : "Masquée" }}
                </span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(listing)">Modifier</button>
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="toggleActive(listing)">
                  {{ listing.is_active ? "Masquer" : "Afficher" }}
                </button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteListing(listing)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-crown" text="Aucune annonce créée pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-extra-photos { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.ie-extra-photo { position: relative; width: 72px; height: 72px; overflow: hidden; border-radius: 8px; border: 1px solid var(--ie-border); }
.ie-extra-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-extra-photo button { position: absolute; top: 3px; right: 3px; width: 20px; height: 20px; border: 0; border-radius: 50%; background: rgba(0, 0, 0, 0.6); color: #fff; font-size: 10px; cursor: pointer; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
.ie-offer-box { margin-top: 14px; padding: 14px; border: 1px solid var(--ie-line); border-radius: 10px; background: #fafbfc; }
.ie-offer-box > strong { color: var(--ie-navy); font-size: 13.5px; }
.ie-offer-check { display: flex; align-items: center; gap: 8px; font-size: 14px; }
</style>
