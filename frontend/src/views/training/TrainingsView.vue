<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const lightbox = useLightboxStore();
const toast = useToastStore();

const trainings = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);
const photoFile = ref(null);

const emptyForm = { name: "", specialty: "", level: "", session_label: "", description: "", fee_amount: 0, start_date: "", end_date: "", is_active: true };
const form = reactive({ ...emptyForm });

async function loadTrainings() {
  loading.value = true;
  try {
    const { data } = await api.get("/training/");
    trainings.value = data.results || data;
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

function startEdit(training) {
  Object.assign(form, {
    name: training.name, specialty: training.specialty, level: training.level,
    session_label: training.session_label, description: training.description,
    fee_amount: training.fee_amount, start_date: training.start_date, end_date: training.end_date,
    is_active: training.is_active,
  });
  editingId.value = training.id;
  photoFile.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function onPhotoChange(e) {
  photoFile.value = e.target.files[0] || null;
}

function buildPayload() {
  if (!photoFile.value) return form;
  const payload = new FormData();
  Object.entries(form).forEach(([key, value]) => payload.append(key, value ?? ""));
  payload.append("photo", photoFile.value);
  return payload;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    const payload = buildPayload();
    if (editingId.value) {
      await api.patch(`/training/${editingId.value}/`, payload);
    } else {
      await api.post("/training/", payload);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Formation enregistrée.");
    await loadTrainings();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer cette formation.";
  } finally {
    submitting.value = false;
  }
}

// --- Formules (durée + tarification) par filière ---
const expandedFormulasId = ref(null);
const formulaSubmitting = ref(false);
const formulaError = ref("");
const emptyFormulaForm = { id: null, label: "", duration_months: 1, registration_fee: 10000, tuition_fee: 100000, is_active: true };
const formulaForm = reactive({ ...emptyFormulaForm });

function toggleFormulas(training) {
  expandedFormulasId.value = expandedFormulasId.value === training.id ? null : training.id;
  Object.assign(formulaForm, emptyFormulaForm);
  formulaError.value = "";
}

function startCreateFormula() {
  Object.assign(formulaForm, emptyFormulaForm);
  formulaError.value = "";
}

function startEditFormula(formula) {
  Object.assign(formulaForm, formula);
}

async function submitFormula(training) {
  formulaError.value = "";
  formulaSubmitting.value = true;
  try {
    const payload = {
      training: training.id,
      label: formulaForm.label,
      duration_months: formulaForm.duration_months,
      registration_fee: formulaForm.registration_fee,
      tuition_fee: formulaForm.tuition_fee,
      is_active: formulaForm.is_active,
    };
    if (formulaForm.id) {
      await api.patch(`/training/formulas/${formulaForm.id}/`, payload);
    } else {
      await api.post("/training/formulas/", payload);
    }
    toast.success(formulaForm.id ? "Modifications enregistrées." : "Formule enregistrée.");
    Object.assign(formulaForm, emptyFormulaForm);
    await loadTrainings();
  } catch (e) {
    formulaError.value = e?.response?.data?.detail || "Impossible d'enregistrer cette formule.";
  } finally {
    formulaSubmitting.value = false;
  }
}

async function deleteFormula(formula) {
  if (!confirm(`Supprimer la formule « ${formula.label} » ?`)) return;
  await api.delete(`/training/formulas/${formula.id}/`);
  await loadTrainings();
}

onMounted(loadTrainings);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-graduation-cap" style="color: var(--ie-red); margin-right: 8px;"></i>Formations</h1>
        <p class="ie-page-subtitle">Filières, formules de durée/tarification et rentrées académiques.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouvelle filière" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Nom de la filière</label>
            <input v-model="form.name" class="ie-input" required placeholder="Ex: Décoration Événementielle" />
          </div>
          <div>
            <label class="ie-label">Rentrée / Session</label>
            <input v-model="form.session_label" class="ie-input" placeholder="Ex: Rentrée académique 2026" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Spécialité</label>
            <input v-model="form.specialty" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Niveau</label>
            <input v-model="form.level" class="ie-input" placeholder="Débutant, Avancé…" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Début des cours</label>
            <input v-model="form.start_date" type="date" class="ie-input" />
          </div>
          <div>
            <label class="ie-label">Fin</label>
            <input v-model="form.end_date" type="date" class="ie-input" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 14px;">Tarif de repli (XAF)</label>
        <input v-model.number="form.fee_amount" type="number" min="0" class="ie-input" />
        <p class="ie-field-hint">Utilisé uniquement si aucune formule (durée) n'est définie ci-dessous pour cette filière.</p>
        <label class="ie-label" style="margin-top: 14px;">Description</label>
        <textarea v-model="form.description" class="ie-input" rows="3"></textarea>
        <label class="ie-label" style="margin-top: 14px;">Photo</label>
        <input type="file" accept="image/*" class="ie-input" @change="onPhotoChange" />
        <label style="display:flex; align-items:center; gap:8px; margin-top:14px; font-size:14px;">
          <input v-model="form.is_active" type="checkbox" /> Visible dans le catalogue d'inscription
        </label>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="trainings.length">
        <table class="ie-table">
          <thead>
            <tr><th></th><th>Filière</th><th>Rentrée</th><th>Niveau</th><th class="ie-num">Inscrits</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <template v-for="training in trainings" :key="training.id">
              <tr>
                <td>
                  <div class="ie-training-thumb">
                    <img v-if="training.photo" :src="training.photo" :alt="training.name" class="ie-zoomable" @click="lightbox.open(training.photo, training.name)" />
                    <i v-else class="fa-solid fa-graduation-cap"></i>
                  </div>
                </td>
                <td><strong>{{ training.name }}</strong></td>
                <td>{{ training.session_label || "—" }}</td>
                <td>{{ training.level || "—" }}</td>
                <td class="ie-num">{{ training.enrolled_count }}</td>
                <td><span class="ie-badge" :class="training.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ training.is_active ? "Ouverte" : "Fermée" }}</span></td>
                <td class="ie-table-actions">
                  <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(training)">Modifier</button>
                  <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="toggleFormulas(training)">
                    <i class="fa-solid fa-layer-group"></i> Formules ({{ training.formulas.length }})
                  </button>
                </td>
              </tr>
              <tr v-if="expandedFormulasId === training.id">
                <td colspan="7" style="background:#fafbfc;">
                  <div class="ie-formulas-panel">
                    <table class="ie-table ie-table-compact" v-if="training.formulas.length">
                      <thead>
                        <tr><th>Formule</th><th class="ie-num">Durée</th><th class="ie-num">Inscription</th><th class="ie-num">Formation</th><th class="ie-num">Total</th><th>Statut</th><th></th></tr>
                      </thead>
                      <tbody>
                        <tr v-for="f in training.formulas" :key="f.id">
                          <td>{{ f.label }}</td>
                          <td class="ie-num">{{ f.duration_months }} mois</td>
                          <td class="ie-num">{{ Number(f.registration_fee).toLocaleString('fr-FR') }} XAF</td>
                          <td class="ie-num">{{ Number(f.tuition_fee).toLocaleString('fr-FR') }} XAF</td>
                          <td class="ie-num"><strong>{{ Number(f.total_fee).toLocaleString('fr-FR') }} XAF</strong></td>
                          <td><span class="ie-badge" :class="f.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">{{ f.is_active ? "Active" : "Inactive" }}</span></td>
                          <td class="ie-table-actions">
                            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEditFormula(f)">Modifier</button>
                            <button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteFormula(f)">Supprimer</button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <p v-else style="font-size:12.5px; color: var(--ie-muted); margin: 0 0 12px;">Aucune formule définie — le tarif de repli de la filière s'applique.</p>

                    <form class="ie-formula-form" @submit.prevent="submitFormula(training)">
                      <div>
                        <label class="ie-label">Libellé</label>
                        <input v-model="formulaForm.label" class="ie-input" required placeholder="Ex: Formation accélérée" />
                      </div>
                      <div>
                        <label class="ie-label">Durée (mois)</label>
                        <input v-model.number="formulaForm.duration_months" type="number" min="1" class="ie-input" required style="width:90px;" />
                      </div>
                      <div>
                        <label class="ie-label">Inscription (XAF)</label>
                        <input v-model.number="formulaForm.registration_fee" type="number" min="0" class="ie-input" style="width:130px;" />
                      </div>
                      <div>
                        <label class="ie-label">Formation (XAF)</label>
                        <input v-model.number="formulaForm.tuition_fee" type="number" min="0" class="ie-input" style="width:130px;" />
                      </div>
                      <label style="display:flex; align-items:center; gap:6px; font-size:12.5px; white-space:nowrap;">
                        <input v-model="formulaForm.is_active" type="checkbox" /> Active
                      </label>
                      <button class="ie-btn ie-btn-primary ie-btn-sm" type="submit" :disabled="formulaSubmitting">
                        {{ formulaForm.id ? "Mettre à jour" : "Ajouter" }}
                      </button>
                      <button v-if="formulaForm.id" type="button" class="ie-btn ie-btn-ghost ie-btn-sm" @click="startCreateFormula">Annuler</button>
                    </form>
                    <p v-if="formulaError" class="ie-alert ie-alert-danger" style="margin-top:8px;">{{ formulaError }}</p>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-graduation-cap" text="Aucune formation créée pour le moment." />
    </div>
  </div>
</template>

<style scoped>
.ie-training-thumb {
  width: 40px; height: 40px; border-radius: 8px; overflow: hidden;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-training-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-training-thumb i { color: var(--ie-navy); opacity: 0.4; font-size: 14px; }
.ie-field-hint { font-size: 11.5px; color: var(--ie-muted); margin: 4px 0 0; }

.ie-formulas-panel { padding: 14px 4px; }
.ie-table-compact th, .ie-table-compact td { padding: 6px 10px; font-size: 12.5px; }
.ie-formula-form {
  display: flex; align-items: end; gap: 12px; flex-wrap: wrap;
  margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--ie-line);
}
</style>
