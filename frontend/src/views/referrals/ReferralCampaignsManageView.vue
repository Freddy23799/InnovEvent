<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const campaigns = ref([]);
const categoryChoices = ref([]);
const providers = ref([]);
const professionalProfiles = ref([]);
const services = ref([]);
const loading = ref(true);
const showForm = ref(false);
const editingId = ref(null);
const submitting = ref(false);

function emptyForm() {
  return {
    name: "", slug: "", description: "", terms_text: "", active: true, is_default: false,
    category: "", providers: [], professional_profiles: [], services: [], marketplace_type: "",
    min_purchase_amount: 0, coupon_validity_days: 30, max_uses_per_coupon: 1,
    valid_from: "", valid_until: "",
    tiers: [{ threshold_referrals: 5, discount_percent: 5, max_discount_amount: null, label: "" }],
  };
}
const form = reactive(emptyForm());

function resetForm() {
  Object.assign(form, emptyForm());
  editingId.value = null;
}

function addTier() {
  form.tiers.push({ threshold_referrals: 10, discount_percent: 10, max_discount_amount: null, label: "" });
}
function removeTier(index) {
  form.tiers.splice(index, 1);
}

async function loadOptions() {
  const [optionsRes, providersRes, profilesRes, servicesRes] = await Promise.all([
    api.options("/referrals/campaigns/"),
    api.get("/providers/"),
    api.get("/marketplace/profiles/"),
    api.get("/marketplace/services/"),
  ]);
  categoryChoices.value = optionsRes.data?.actions?.POST?.category?.choices || [];
  providers.value = providersRes.data.results || providersRes.data;
  professionalProfiles.value = profilesRes.data.results || profilesRes.data;
  services.value = servicesRes.data.results || servicesRes.data;
}

async function loadCampaigns() {
  const { data } = await api.get("/referrals/campaigns/");
  campaigns.value = data.results || data;
}

async function loadAll() {
  loading.value = true;
  try {
    await Promise.all([loadOptions(), loadCampaigns()]);
  } finally {
    loading.value = false;
  }
}

function editCampaign(campaign) {
  editingId.value = campaign.id;
  Object.assign(form, {
    name: campaign.name, slug: campaign.slug, description: campaign.description, terms_text: campaign.terms_text,
    active: campaign.active, is_default: campaign.is_default, category: campaign.category,
    providers: campaign.providers, professional_profiles: campaign.professional_profiles, services: campaign.services,
    marketplace_type: campaign.marketplace_type, min_purchase_amount: campaign.min_purchase_amount,
    coupon_validity_days: campaign.coupon_validity_days, max_uses_per_coupon: campaign.max_uses_per_coupon,
    valid_from: campaign.valid_from || "", valid_until: campaign.valid_until || "",
    tiers: campaign.tiers.length ? campaign.tiers.map((t) => ({ ...t })) : emptyForm().tiers,
  });
  showForm.value = true;
}

function slugify(name) {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

async function submitForm() {
  submitting.value = true;
  try {
    const payload = { ...form, slug: form.slug || slugify(form.name) };
    if (editingId.value) {
      await api.patch(`/referrals/campaigns/${editingId.value}/`, payload);
      toast.success("Campagne mise à jour.");
    } else {
      await api.post("/referrals/campaigns/", payload);
      toast.success("Campagne créée.");
    }
    showForm.value = false;
    resetForm();
    await loadCampaigns();
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d'enregistrer cette campagne.");
  } finally {
    submitting.value = false;
  }
}

async function toggleActive(campaign) {
  await api.patch(`/referrals/campaigns/${campaign.id}/`, { active: !campaign.active });
  await loadCampaigns();
}

onMounted(loadAll);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-bullhorn" style="color: var(--ie-red); margin-right: 8px;"></i>Configuration des campagnes</h1>
        <p class="ie-page-subtitle">Définissez les règles de récompense du programme de parrainage.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm = !showForm; if (!showForm) resetForm()">
          <i class="fa-solid fa-plus"></i> {{ showForm ? "Annuler" : "Nouvelle campagne" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <h3>{{ editingId ? "Modifier la campagne" : "Nouvelle campagne" }}</h3>

      <div class="ie-form-row">
        <div>
          <label class="ie-label">Nom</label>
          <input v-model="form.name" class="ie-input" placeholder="Ex : Parrainage Mariage" />
        </div>
        <div>
          <label class="ie-label">Identifiant (slug)</label>
          <input v-model="form.slug" class="ie-input" :placeholder="slugify(form.name) || 'auto'" />
        </div>
      </div>

      <label class="ie-label" style="margin-top: 10px;">Description</label>
      <textarea v-model="form.description" class="ie-input" rows="2"></textarea>

      <label class="ie-label" style="margin-top: 10px;">Conditions d'utilisation</label>
      <textarea v-model="form.terms_text" class="ie-input" rows="2"></textarea>

      <div class="ie-form-row" style="margin-top: 10px;">
        <div>
          <label class="ie-label">Catégorie concernée</label>
          <select v-model="form.category" class="ie-select">
            <option value="">Toutes catégories</option>
            <option v-for="c in categoryChoices" :key="c.value" :value="c.value">{{ c.display_name }}</option>
          </select>
        </div>
        <div>
          <label class="ie-label">Marketplace concerné</label>
          <select v-model="form.marketplace_type" class="ie-select">
            <option value="">Tous</option>
            <option value="sale">Marketplace vente</option>
            <option value="interior_design">Décoration & design intérieur</option>
            <option value="actors">Marketplace des acteurs</option>
            <option value="venues">Salles de réception</option>
          </select>
        </div>
      </div>

      <div class="ie-form-row" style="margin-top: 10px;">
        <div>
          <label class="ie-label">Prestataires concernés (catalogue)</label>
          <select v-model="form.providers" class="ie-select" multiple size="4">
            <option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div>
          <label class="ie-label">Profils professionnels concernés</label>
          <select v-model="form.professional_profiles" class="ie-select" multiple size="4">
            <option v-for="p in professionalProfiles" :key="p.id" :value="p.id">{{ p.business_name }}</option>
          </select>
        </div>
      </div>

      <label class="ie-label" style="margin-top: 10px;">Services concernés</label>
      <select v-model="form.services" class="ie-select" multiple size="4">
        <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>

      <div class="ie-form-row" style="margin-top: 10px;">
        <div>
          <label class="ie-label">Montant minimum d'achat (XAF)</label>
          <input v-model.number="form.min_purchase_amount" type="number" min="0" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Nombre max. d'utilisations par coupon</label>
          <input v-model.number="form.max_uses_per_coupon" type="number" min="1" class="ie-input" />
        </div>
      </div>

      <div class="ie-form-row" style="margin-top: 10px;">
        <div>
          <label class="ie-label">Durée de validité du coupon (jours)</label>
          <input v-model.number="form.coupon_validity_days" type="number" min="1" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Active</label>
          <label style="display: flex; align-items: center; gap: 8px; margin-top: 10px;">
            <input type="checkbox" v-model="form.active" /> Campagne active
          </label>
        </div>
      </div>

      <div class="ie-form-row" style="margin-top: 10px;">
        <div>
          <label class="ie-label">Valide à partir du</label>
          <input v-model="form.valid_from" type="datetime-local" class="ie-input" />
        </div>
        <div>
          <label class="ie-label">Valide jusqu'au</label>
          <input v-model="form.valid_until" type="datetime-local" class="ie-input" />
        </div>
      </div>

      <h4 style="margin-top: 18px;">Paliers de récompense</h4>
      <div v-for="(tier, i) in form.tiers" :key="i" class="ie-tier-row">
        <input v-model.number="tier.threshold_referrals" type="number" min="1" class="ie-input" placeholder="Nb. filleuls" />
        <input v-model.number="tier.discount_percent" type="number" min="0" max="100" step="0.01" class="ie-input" placeholder="% réduction" />
        <input v-model.number="tier.max_discount_amount" type="number" min="0" class="ie-input" placeholder="Plafond (XAF, optionnel)" />
        <input v-model="tier.label" class="ie-input" placeholder="Libellé (optionnel)" />
        <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="removeTier(i)"><i class="fa-solid fa-trash"></i></button>
      </div>
      <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="addTier"><i class="fa-solid fa-plus"></i> Ajouter un palier</button>

      <button class="ie-btn ie-btn-primary" style="margin-top: 18px;" :disabled="submitting || !form.name" @click="submitForm">
        {{ submitting ? "Enregistrement…" : "Enregistrer la campagne" }}
      </button>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <div v-else-if="campaigns.length" style="display: flex; flex-direction: column; gap: 14px;">
      <div v-for="c in campaigns" :key="c.id" class="ie-card ie-card-body">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;">
          <div>
            <strong style="font-size: 14.5px; color: var(--ie-navy);">{{ c.name }}</strong>
            <p style="margin: 2px 0 0; font-size: 12.5px; color: var(--ie-muted);">{{ c.description || "—" }}</p>
            <p style="margin: 4px 0 0; font-size: 12px; color: var(--ie-ink);">
              Paliers : {{ c.tiers.map((t) => `${t.threshold_referrals} → ${t.discount_percent}%`).join(", ") }}
            </p>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="ie-badge" :class="c.active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ c.active ? "Active" : "Inactive" }}</span>
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="editCampaign(c)">Modifier</button>
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="toggleActive(c)">{{ c.active ? "Désactiver" : "Activer" }}</button>
          </div>
        </div>
      </div>
    </div>

    <EmptyState v-else icon="fa-solid fa-bullhorn" text="Aucune campagne configurée pour le moment." />
  </div>
</template>

<style scoped>
.ie-tier-row { display: grid; grid-template-columns: 1fr 1fr 1.4fr 1.4fr auto; gap: 8px; margin-top: 8px; align-items: center; }
@media (max-width: 720px) {
  .ie-tier-row { grid-template-columns: 1fr 1fr; }
}
</style>
