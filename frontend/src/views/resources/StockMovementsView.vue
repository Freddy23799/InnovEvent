<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const MOVEMENT_LABELS = { in: "Entrée", out: "Sortie" };
const MOVEMENT_BADGE = { in: "ie-badge-success", out: "ie-badge-danger" };
const REASON_LABELS = {
  restock: "Réapprovisionnement / achat",
  event_use: "Utilisation pour un événement",
  damage: "Endommagé",
  loss: "Perdu / volé",
  return: "Retour en stock",
  disposal: "Mise au rebut",
  other: "Autre",
};

const movements = ref([]);
const equipmentList = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const equipmentFilter = ref("");

const emptyForm = { equipment: "", movement_type: "in", reason: "restock", quantity: 1, notes: "" };
const form = reactive({ ...emptyForm });

const selectedEquipment = computed(() => equipmentList.value.find((e) => e.id === form.equipment) || null);

async function loadData() {
  loading.value = true;
  try {
    const params = {};
    if (equipmentFilter.value) params.equipment = equipmentFilter.value;
    const [movementsRes, equipmentRes] = await Promise.all([
      api.get("/equipment/stock-movements/", { params }),
      api.get("/equipment/", { params: { is_active: true } }),
    ]);
    movements.value = movementsRes.data.results || movementsRes.data;
    equipmentList.value = equipmentRes.data.results || equipmentRes.data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    await api.post("/equipment/stock-movements/", form);
    showForm.value = false;
    toast.success("Mouvement de stock enregistré.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || e?.response?.data?.non_field_errors?.[0] || "Impossible d'enregistrer ce mouvement.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-right-left" style="color: var(--ie-red); margin-right: 8px;"></i>Mouvements de stock</h1>
        <p class="ie-page-subtitle">Historique complet des entrées et sorties de matériel, avec mise à jour automatique du stock.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau mouvement" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Matériel</label>
            <select v-model="form.equipment" class="ie-select" required>
              <option value="" disabled>Choisir un matériel</option>
              <option v-for="e in equipmentList" :key="e.id" :value="e.id">{{ e.name }} (stock actuel : {{ e.quantity_total }})</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Type de mouvement</label>
            <select v-model="form.movement_type" class="ie-select">
              <option value="in">Entrée (réapprovisionnement)</option>
              <option value="out">Sortie</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Motif</label>
            <select v-model="form.reason" class="ie-select">
              <option v-for="(label, value) in REASON_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Quantité</label>
            <input
              v-model.number="form.quantity" type="number" min="1"
              :max="form.movement_type === 'out' && selectedEquipment ? selectedEquipment.quantity_total : undefined"
              class="ie-input" required
            />
            <p v-if="form.movement_type === 'out' && selectedEquipment" class="ie-field-hint">
              Stock actuel disponible : {{ selectedEquipment.quantity_total }} unité(s)
            </p>
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Notes (optionnel)</label>
        <textarea v-model="form.notes" class="ie-input" rows="2" placeholder="Ex: Sortie pour l'événement « Gala annuel InnovEvent »"></textarea>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : "Enregistrer le mouvement" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-clock-rotate-left"></i>Historique</h2>
        <select v-model="equipmentFilter" class="ie-select" style="width: 240px;" @change="loadData">
          <option value="">Tout le matériel</option>
          <option v-for="e in equipmentList" :key="e.id" :value="e.id">{{ e.name }}</option>
        </select>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="movements.length">
        <table class="ie-table">
          <thead>
            <tr><th>Date</th><th>Matériel</th><th>Type</th><th>Motif</th><th class="ie-num">Quantité</th><th class="ie-num">Stock résultant</th><th>Enregistré par</th></tr>
          </thead>
          <tbody>
            <tr v-for="m in movements" :key="m.id">
              <td>{{ new Date(m.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) }}</td>
              <td><strong>{{ m.equipment_name }}</strong></td>
              <td><span class="ie-badge" :class="MOVEMENT_BADGE[m.movement_type]">{{ MOVEMENT_LABELS[m.movement_type] }}</span></td>
              <td>{{ REASON_LABELS[m.reason] || m.reason }}</td>
              <td class="ie-num">{{ m.movement_type === 'out' ? '-' : '+' }}{{ m.quantity }}</td>
              <td class="ie-num"><strong>{{ m.resulting_quantity }}</strong></td>
              <td>{{ m.recorded_by_name || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-right-left" text="Aucun mouvement de stock enregistré." />
    </div>
  </div>
</template>

<style scoped>
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }
</style>
