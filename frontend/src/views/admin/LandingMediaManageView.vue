<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const router = useRouter();

const toast = useToastStore();
const CATEGORIES = [
  { value: "deco", label: "Décoration" },
  { value: "formation", label: "Formation (Academy)" },
  { value: "realisation", label: "Réalisations (portfolio)" },
  { value: "accessoire", label: "Location de matériel" },
  { value: "pack", label: "Nos packs (offres tarifées)" },
];

const SCOPES = [
  { value: "", label: "—" },
  { value: "prive", label: "Événements privés" },
  { value: "public", label: "Événements grand public" },
];

const TIERS = [
  { value: "", label: "—" },
  { value: "haut", label: "Haut de gamme" },
  { value: "moyen", label: "Moyenne gamme" },
  { value: "petit", label: "Petite gamme" },
];

const items = ref([]);
const loading = ref(true);
const activeCategory = ref("deco");
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = { category: "deco", scope: "", tag: "", tier: "", label: "", caption: "", price_label: "", budget_label: "", order: 0, is_active: true };
const form = reactive({ ...emptyForm });

const filteredItems = computed(() => items.value.filter((i) => i.category === activeCategory.value));

// Types déjà utilisés par l'administrateur pour le scope choisi, suggérés via <datalist> ;
// il reste libre d'en taper un nouveau pour créer un type de réalisation à la volée.
const existingTags = computed(() => {
  const tags = items.value
    .filter((i) => i.category === "realisation" && i.tag && (!form.scope || i.scope === form.scope))
    .map((i) => i.tag);
  return [...new Set(tags)];
});

function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label || value;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  const payload = new FormData();
  Object.entries(form).forEach(([key, value]) => payload.append(key, value));
  if (photoFile.value) payload.append("photo", photoFile.value);
  return payload;
}

async function loadItems() {
  loading.value = true;
  try {
    const { data } = await api.get("/public/landing-media/");
    items.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm, { category: activeCategory.value });
  editingId.value = null;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(item) {
  Object.assign(form, {
    category: item.category, scope: item.scope || "", tag: item.tag || "", tier: item.tier || "", label: item.label, caption: item.caption,
    price_label: item.price_label || "", budget_label: item.budget_label || "", order: item.order, is_active: item.is_active,
  });
  editingId.value = item.id;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  if (!editingId.value && !photoFile.value) {
    errorMessage.value = "Une photo est requise pour créer un média.";
    return;
  }
  submitting.value = true;
  try {
    const payload = buildPayload();
    let created = null;
    if (editingId.value) {
      await api.patch(`/public/landing-media/${editingId.value}/`, payload);
    } else {
      const { data } = await api.post("/public/landing-media/", payload);
      created = data;
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Élément enregistré.");
    await loadItems();
    // Un nouveau pack a besoin de ses composants : direction la page dédiée
    // plutôt que de laisser l'administrateur la retrouver dans la grille.
    if (created && created.category === "pack") {
      router.push({ name: "admin-pack-manage", params: { packId: created.id } });
    }
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce média.";
  } finally {
    submitting.value = false;
  }
}

async function deleteItem(item) {
  if (!confirm(`Supprimer « ${item.label} » ?`)) return;
  await api.delete(`/public/landing-media/${item.id}/`);
  await loadItems();
}

onMounted(() => {
  loadItems();
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-images" style="color: var(--ie-red); margin-right: 8px;"></i>Photothèque page d'accueil</h1>
        <p class="ie-page-subtitle">Gérez les photos affichées sur la page publique InnovEvent Group, par catégorie.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Ajouter une photo" }}
        </button>
      </div>
    </div>

    <div class="lm-tabs">
      <button
        v-for="c in CATEGORIES"
        :key="c.value"
        class="lm-tab"
        :class="{ 'is-active': activeCategory === c.value }"
        @click="activeCategory = c.value"
      >
        {{ c.label }}
        <span class="lm-tab-count">{{ items.filter((i) => i.category === c.value).length }}</span>
      </button>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Catégorie</label>
            <select v-model="form.category" class="ie-select">
              <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Ordre d'affichage</label>
            <input v-model.number="form.order" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <div v-if="form.category === 'realisation'" class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Scope</label>
            <select v-model="form.scope" class="ie-select">
              <option v-for="s in SCOPES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Gamme (ordre d'affichage : haut → moyen → petit)</label>
            <select v-model="form.tier" class="ie-select">
              <option v-for="t in TIERS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>
        <div v-if="form.category === 'realisation'" style="margin-top: 14px;">
          <label class="ie-label">Type d'événement</label>
          <input v-model="form.tag" class="ie-input" list="lm-tag-suggestions" placeholder="Ex : Mariages Modernes, Anniversaires Adultes, Salons…" />
          <datalist id="lm-tag-suggestions">
            <option v-for="t in existingTags" :key="t" :value="t"></option>
          </datalist>
          <p class="ie-field-hint">Tapez un type existant ou un nouveau : il apparaîtra automatiquement comme filtre sur la page d'accueil. Aucun prix n'est affiché dans les réalisations — les prix se gèrent dans la catégorie « Nos packs ».</p>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Libellé</label>
        <input v-model="form.label" class="ie-input" required placeholder="Ex : Arche florale & table d'honneur" />
        <label class="ie-label" style="margin-top: 14px;">Légende courte / description</label>
        <input v-model="form.caption" class="ie-input" placeholder="Ex : Cérémonie sous arche fleurie" />
        <div v-if="form.category === 'accessoire'" style="margin-top: 14px;">
          <label class="ie-label">Prix indicatif</label>
          <input v-model="form.price_label" class="ie-input" placeholder="Ex : 500 FCFA / chaise / jour" />
        </div>
        <div v-if="form.category === 'pack'" class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Gamme du pack</label>
            <select v-model="form.tier" class="ie-select">
              <option v-for="t in TIERS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Prix du pack</label>
            <input v-model="form.budget_label" class="ie-input" placeholder="Ex : 1 200 000 FCFA" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Photo{{ editingId ? " (laisser vide pour conserver l'actuelle)" : "" }}</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Visible sur la page d'accueil
        </label>
        <p v-if="errorMessage" style="color: var(--ie-red); font-size: 13px; margin-top: 10px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card ie-card-body" v-if="loading">
      <p class="ie-page-subtitle">Chargement…</p>
    </div>
    <div v-else-if="filteredItems.length" class="lm-grid">
      <div v-for="item in filteredItems" :key="item.id" class="lm-card" :class="{ 'is-inactive': !item.is_active }">
        <router-link
          v-if="item.category === 'pack'"
          :to="{ name: 'admin-pack-manage', params: { packId: item.id } }"
          class="lm-card-photo lm-card-photo-link"
        >
          <img :src="item.photo" :alt="item.label" />
          <span v-if="!item.is_active" class="lm-hidden-badge">Masqué</span>
          <span class="lm-manage-overlay"><i class="fa-solid fa-pen-to-square"></i> Gérer le pack</span>
        </router-link>
        <div v-else class="lm-card-photo">
          <img :src="item.photo" :alt="item.label" />
          <span v-if="!item.is_active" class="lm-hidden-badge">Masqué</span>
        </div>
        <div class="lm-card-body">
          <div v-if="item.scope || item.tag || item.tier" style="display: flex; gap: 4px; flex-wrap: wrap;">
            <span v-if="item.scope" class="ie-badge ie-badge-neutral">{{ SCOPES.find((s) => s.value === item.scope)?.label }}</span>
            <span v-if="item.tag" class="ie-badge ie-badge-neutral">{{ item.tag }}</span>
            <span v-if="item.tier" class="ie-badge ie-badge-neutral">{{ TIERS.find((t) => t.value === item.tier)?.label }}</span>
          </div>
          <strong>{{ item.label }}</strong>
          <p v-if="item.caption">{{ item.caption }}</p>
          <p v-if="item.price_label" class="lm-price">{{ item.price_label }}</p>
          <p v-if="item.budget_label" class="lm-price">{{ item.budget_label }}</p>
          <div class="lm-card-foot">
            <span class="ie-badge ie-badge-neutral">Ordre {{ item.order }}</span>
            <div class="lm-card-actions">
              <router-link
                v-if="item.category === 'pack'"
                :to="{ name: 'admin-pack-manage', params: { packId: item.id } }"
                class="ie-btn ie-btn-ghost ie-btn-sm"
              >
                <i class="fa-solid fa-boxes-stacked"></i> Gérer le pack
              </router-link>
              <button v-else class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(item)">Modifier</button>
              <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteItem(item)">Supprimer</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <EmptyState v-else icon="fa-solid fa-images" :text="`Aucune photo dans « ${categoryLabel(activeCategory)} ».`" />
  </div>
</template>

<style scoped>
.lm-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
.lm-tab {
  padding: 8px 16px; border-radius: 999px; border: 1px solid var(--ie-border, #e2e2e2); background: #fff;
  font-size: 13px; font-weight: 600; color: var(--ie-muted, #6b7280); cursor: pointer; display: flex; align-items: center; gap: 6px;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.lm-tab.is-active { background: var(--ie-red); border-color: var(--ie-red); color: #fff; }
.lm-tab-count { font-size: 11px; opacity: 0.75; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted, #6b7280); margin: 4px 0 0; }

.lm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.lm-card { background: #fff; border: 1px solid var(--ie-border, #e2e2e2); border-radius: 10px; overflow: hidden; }
.lm-card.is-inactive { opacity: 0.6; }
.lm-card-photo { aspect-ratio: 4/3; position: relative; background: #f2f2f2; overflow: hidden; }
.lm-card-photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
.lm-hidden-badge { position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.65); color: #fff; font-size: 10.5px; font-weight: 700; padding: 3px 8px; border-radius: 999px; }
.lm-card-body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 4px; }
.lm-card-body strong { font-size: 13.5px; }
.lm-card-body p { font-size: 12px; color: var(--ie-muted, #6b7280); margin: 0; }
.lm-price { font-weight: 700; color: var(--ie-red); }
.lm-card-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; flex-wrap: wrap; gap: 8px; }
.lm-card-actions { display: flex; gap: 6px; flex-wrap: wrap; }

.lm-card-photo-link { display: block; cursor: pointer; }
.lm-manage-overlay {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 8px;
  background: rgba(23, 27, 38, 0.55); color: #fff; font-size: 13px; font-weight: 700;
  opacity: 0; transition: opacity 0.15s ease;
}
.lm-card-photo-link:hover .lm-manage-overlay { opacity: 1; }
</style>
