<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const VEHICLE_TYPES = [
  { value: "", label: "Tous les véhicules" }, { value: "moto", label: "Moto" }, { value: "tricycle", label: "Tricycle" },
  { value: "car", label: "Voiture" }, { value: "pickup", label: "Pickup" }, { value: "van", label: "Camionnette" },
  { value: "truck", label: "Camion" }, { value: "other", label: "Autre" },
];
const PRIORITIES = [
  { value: "", label: "Toutes priorités" }, { value: "normal", label: "Normale" }, { value: "urgent", label: "Urgente" },
];

const rules = ref([]);
const zones = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = {
  label: "", zone: "", vehicle_type: "", priority: "", min_weight_kg: null, max_weight_kg: null,
  extra_fee: 0, multiplier_percent: 0, order: 0, is_active: true,
};
const form = reactive({ ...emptyForm });

async function loadData() {
  loading.value = true;
  try {
    const [rulesRes, zonesRes] = await Promise.all([
      api.get("/deliveries/pricing-rules/"), api.get("/deliveries/zones/"),
    ]);
    rules.value = rulesRes.data.results || rulesRes.data;
    zones.value = zonesRes.data.results || zonesRes.data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(rule) {
  Object.assign(form, { ...emptyForm, ...rule, zone: rule.zone || "" });
  editingId.value = rule.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = { ...form, zone: form.zone || null };
    if (editingId.value) {
      await api.patch(`/deliveries/pricing-rules/${editingId.value}/`, payload);
    } else {
      await api.post("/deliveries/pricing-rules/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Règle mise à jour." : "Règle créée.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette règle.";
  } finally {
    submitting.value = false;
  }
}

async function deleteRule(rule) {
  if (!confirm(`Supprimer la règle « ${rule.label} » ?`)) return;
  await api.delete(`/deliveries/pricing-rules/${rule.id}/`);
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-sliders" style="color: var(--ie-red); margin-right: 8px;"></i>Règles de tarification avancées</h1>
        <p class="ie-page-subtitle">S'ajoutent en cascade au tarif de zone selon le véhicule, la priorité ou le poids — transparentes et cumulables.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle règle" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <label class="ie-label">Libellé</label>
        <input v-model="form.label" class="ie-input" required placeholder="Ex : Supplément camion hors zone" />
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Zone (optionnel)</label>
            <select v-model="form.zone" class="ie-select">
              <option value="">Toutes les zones</option>
              <option v-for="z in zones" :key="z.id" :value="z.id">{{ z.name }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Type de véhicule</label>
            <select v-model="form.vehicle_type" class="ie-select">
              <option v-for="t in VEHICLE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Priorité</label>
            <select v-model="form.priority" class="ie-select">
              <option v-for="p in PRIORITIES" :key="p.value" :value="p.value">{{ p.label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Ordre d'application</label>
            <input v-model.number="form.order" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Poids min (kg)</label>
            <input v-model.number="form.min_weight_kg" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Poids max (kg)</label>
            <input v-model.number="form.max_weight_kg" type="number" min="0" class="ie-input" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Supplément fixe (XAF)</label>
            <input v-model.number="form.extra_fee" type="number" min="0" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Majoration (%)</label>
            <input v-model.number="form.multiplier_percent" type="number" class="ie-input" />
          </div>
        </div>
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Règle active
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger" style="margin-top: 12px;">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="rules.length">
        <table class="ie-table">
          <thead>
            <tr><th>Libellé</th><th>Zone</th><th>Véhicule</th><th>Priorité</th><th>Supplément</th><th>Majoration</th><th>Active</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="r in rules" :key="r.id">
              <td><strong>{{ r.label }}</strong></td>
              <td>{{ r.zone_name || "Toutes" }}</td>
              <td>{{ VEHICLE_TYPES.find((t) => t.value === r.vehicle_type)?.label || "Tous" }}</td>
              <td>{{ PRIORITIES.find((p) => p.value === r.priority)?.label || "Toutes" }}</td>
              <td class="ie-num">{{ Number(r.extra_fee).toLocaleString('fr-FR') }} XAF</td>
              <td class="ie-num">{{ r.multiplier_percent > 0 ? '+' : '' }}{{ r.multiplier_percent }}%</td>
              <td><span class="ie-badge" :class="r.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ r.is_active ? "Oui" : "Non" }}</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(r)">Modifier</button>
                <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteRule(r)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-sliders" text="Aucune règle de tarification avancée pour le moment." />
    </div>
  </div>
</template>
