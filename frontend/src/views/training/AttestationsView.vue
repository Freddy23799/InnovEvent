<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();

const auth = useAuthStore();
const STATUS_LABELS = { pending: "En attente", validated: "Validé", rejected: "Rejeté" };
const STATUS_BADGE = { pending: "ie-badge-warning", validated: "ie-badge-success", rejected: "ie-badge-danger" };
const SCHEDULE_LABELS = { day: "Cours du jour", evening: "Cours du soir" };

const enrollments = ref([]);
const trainings = ref([]);
const users = ref([]);
const badges = ref([]);
const loading = ref(true);

const showEnrollForm = ref(false);
const enrollForm = reactive({ training: "", formula: "", schedule: "", participant: "" });
const enrollPhotoFile = ref(null);

const selectedTraining = computed(() => trainings.value.find((t) => t.id === enrollForm.training) || null);
const availableFormulas = computed(() => (selectedTraining.value?.formulas || []).filter((f) => f.is_active));
const scheduleChoices = computed(() => {
  const opts = selectedTraining.value?.schedule_options || [];
  return Object.entries(SCHEDULE_LABELS).map(([value, label]) => {
    const match = opts.find((o) => o.label === label);
    return { value, label, hours: match?.hours || "" };
  });
});

function onTrainingChange() {
  enrollForm.formula = "";
  enrollForm.schedule = "";
}

const settlementFormFor = ref(null);
const settlementAmount = ref(0);

const payFormFor = ref(null);
const payAmount = ref(0);
const payProvider = ref("mobile_money");
const paying = ref(false);
const payError = ref("");

const PAYMENT_PROVIDERS = [
  { value: "mobile_money", label: "Orange Money / Mobile Money" },
  { value: "paypal", label: "Carte bancaire (PayPal)" },
  { value: "demo", label: "Mode démonstration" },
];

const showBadgeForm = ref(false);
const badgeForm = reactive({ user: "", matricule: "", purpose: "training", valid_from: "", valid_until: "" });

async function loadData() {
  loading.value = true;
  try {
    const requests = [
      api.get("/training/enrollments/"),
      api.get("/training/"),
      api.get("/training/badges/"),
    ];
    if (auth.role === "admin") requests.push(api.get("/auth/users/"));
    const results = await Promise.all(requests);
    enrollments.value = results[0].data.results || results[0].data;
    trainings.value = results[1].data.results || results[1].data;
    badges.value = results[2].data.results || results[2].data;
    if (results[3]) users.value = results[3].data.results || results[3].data;
  } finally {
    loading.value = false;
  }
}

function onEnrollPhotoChange(e) {
  enrollPhotoFile.value = e.target.files[0] || null;
}

async function submitEnrollment() {
  const cleanFields = Object.fromEntries(
    Object.entries(enrollForm).filter(([, value]) => value !== "" && value !== null)
  );
  let payload = cleanFields;
  if (enrollPhotoFile.value) {
    payload = new FormData();
    Object.entries(cleanFields).forEach(([key, value]) => payload.append(key, value));
    payload.append("photo", enrollPhotoFile.value);
  }
  await api.post("/training/enrollments/", payload);
  showEnrollForm.value = false;
  Object.assign(enrollForm, { training: "", formula: "", schedule: "", participant: "" });
  enrollPhotoFile.value = null;
  await loadData();
}

function openPayment(enrollment) {
  payFormFor.value = enrollment.id;
  payAmount.value = enrollment.balance;
  payProvider.value = "mobile_money";
  payError.value = "";
}

async function confirmPayment(enrollment) {
  paying.value = true;
  payError.value = "";
  try {
    await api.post(`/training/enrollments/${enrollment.id}/pay/`, { amount: payAmount.value, payment_provider: payProvider.value });
    payFormFor.value = null;
    await loadData();
  } catch (e) {
    payError.value = e?.response?.data?.detail || "Le paiement a échoué.";
  } finally {
    paying.value = false;
  }
}

async function validateEnrollment(enrollment) {
  await api.post(`/training/enrollments/${enrollment.id}/validate/`);
  await loadData();
}

function openSettlement(enrollment) {
  settlementFormFor.value = enrollment.id;
  settlementAmount.value = enrollment.balance;
}

async function recordSettlement(enrollment) {
  await api.post("/training/settlements/", { enrollment: enrollment.id, amount: settlementAmount.value, method: "espèces" });
  settlementFormFor.value = null;
  await loadData();
}

async function issueCertificate(enrollment) {
  await api.post("/training/certificates/", { enrollment: enrollment.id });
  await loadData();
}

async function downloadCertificate(enrollment) {
  const certRes = await api.get("/training/certificates/", { params: { enrollment: enrollment.id } });
  const cert = (certRes.data.results || certRes.data)[0];
  if (!cert) return;
  const response = await api.get(`/training/certificates/${cert.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `attestation-${enrollment.matricule}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

async function submitBadge() {
  await api.post("/training/badges/", badgeForm);
  showBadgeForm.value = false;
  Object.assign(badgeForm, { user: "", matricule: "", purpose: "training", valid_from: "", valid_until: "" });
  await loadData();
}

async function downloadBadge(badge) {
  const response = await api.get(`/training/badges/${badge.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `badge-${badge.matricule}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-certificate" style="color: var(--ie-red); margin-right: 8px;"></i>Attestations</h1>
        <p class="ie-page-subtitle">Inscriptions, règlements, délivrance des attestations et badges.</p>
      </div>
      <div class="ie-page-header-actions" v-if="auth.role === 'admin'">
        <button class="ie-btn ie-btn-primary" @click="showEnrollForm = !showEnrollForm">
          <i class="fa-solid" :class="showEnrollForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showEnrollForm ? "Annuler" : "Inscrire un participant" }}
        </button>
      </div>
    </div>

    <div v-if="showEnrollForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form class="ie-form-row" style="align-items: end; flex-wrap: wrap;" @submit.prevent="submitEnrollment">
        <div>
          <label class="ie-label">Filière</label>
          <select v-model="enrollForm.training" class="ie-select" required @change="onTrainingChange">
            <option value="" disabled>Choisir une filière</option>
            <option v-for="t in trainings" :key="t.id" :value="t.id">{{ t.name }} — {{ t.session_label }}</option>
          </select>
        </div>
        <div v-if="selectedTraining">
          <label class="ie-label">Formule</label>
          <select v-model="enrollForm.formula" class="ie-select">
            <option value="">Tarif de repli ({{ Number(selectedTraining.fee_amount).toLocaleString('fr-FR') }} XAF)</option>
            <option v-for="f in availableFormulas" :key="f.id" :value="f.id">
              {{ f.label }} — {{ f.duration_months }} mois — {{ Number(f.total_fee).toLocaleString('fr-FR') }} XAF
            </option>
          </select>
        </div>
        <div v-if="selectedTraining">
          <label class="ie-label">Horaire</label>
          <select v-model="enrollForm.schedule" class="ie-select">
            <option value="">Non précisé</option>
            <option v-for="s in scheduleChoices" :key="s.value" :value="s.value">{{ s.label }}{{ s.hours ? ` (${s.hours})` : "" }}</option>
          </select>
        </div>
        <div>
          <label class="ie-label">Participant</label>
          <select v-model="enrollForm.participant" class="ie-select" required>
            <option value="" disabled>Choisir un participant</option>
            <option v-for="u in users" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
          </select>
        </div>
        <div>
          <label class="ie-label">Photo (pour le badge)</label>
          <input type="file" accept="image/*" class="ie-input" @change="onEnrollPhotoChange" />
        </div>
        <button class="ie-btn ie-btn-primary" type="submit">Inscrire</button>
      </form>
    </div>

    <div class="ie-card">
      <div class="ie-card-header"><h2><i class="fa-solid fa-id-badge"></i>Inscriptions</h2></div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="enrollments.length">
        <table class="ie-table">
          <thead>
            <tr><th></th><th>Matricule</th><th>Participant</th><th>Formation</th><th class="ie-num">Payé / Dû</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <template v-for="enrollment in enrollments" :key="enrollment.id">
              <tr>
                <td>
                  <div class="ie-enroll-photo">
                    <img v-if="enrollment.photo" :src="enrollment.photo" :alt="enrollment.participant_name" class="ie-zoomable" @click="lightbox.open(enrollment.photo, enrollment.participant_name)" />
                    <i v-else class="fa-solid fa-user"></i>
                  </div>
                </td>
                <td style="font-family: monospace; font-size: 12px;">{{ enrollment.matricule }}</td>
                <td>{{ enrollment.participant_name }}</td>
                <td>
                  {{ enrollment.training_name }}
                  <div v-if="enrollment.formula_label || enrollment.schedule_display" style="font-size:11px; color: var(--ie-muted);">
                    {{ [enrollment.formula_label, enrollment.schedule_display].filter(Boolean).join(" · ") }}
                  </div>
                </td>
                <td class="ie-num">
                  {{ Number(enrollment.amount_paid).toLocaleString('fr-FR') }} / {{ Number(enrollment.amount_due).toLocaleString('fr-FR') }} XAF
                  <div style="font-size:11px; color: var(--ie-muted);">Solde : {{ Number(enrollment.balance).toLocaleString('fr-FR') }} XAF</div>
                </td>
                <td><span class="ie-badge" :class="STATUS_BADGE[enrollment.status]">{{ STATUS_LABELS[enrollment.status] }}</span></td>
                <td class="ie-table-actions">
                  <button v-if="enrollment.status === 'pending' && auth.role === 'admin'" class="ie-btn ie-btn-ghost ie-btn-sm" @click="validateEnrollment(enrollment)">Valider</button>
                  <button v-if="enrollment.balance > 0" class="ie-btn ie-btn-primary ie-btn-sm" @click="openPayment(enrollment)">
                    <i class="fa-solid fa-credit-card"></i> Payer une tranche
                  </button>
                  <button v-if="auth.role === 'admin'" class="ie-btn ie-btn-secondary ie-btn-sm" @click="openSettlement(enrollment)">Règlement manuel</button>
                  <button v-if="enrollment.status === 'validated' && enrollment.balance <= 0 && auth.role === 'admin'" class="ie-btn ie-btn-secondary ie-btn-sm" @click="issueCertificate(enrollment)">Délivrer</button>
                  <button v-if="enrollment.status === 'validated'" class="ie-btn ie-btn-secondary ie-btn-sm" @click="downloadCertificate(enrollment)">
                    <i class="fa-solid fa-download"></i> Attestation
                  </button>
                </td>
              </tr>
              <tr v-if="payFormFor === enrollment.id">
                <td colspan="7" style="background:#fafbfc;">
                  <div style="display:flex; align-items:center; gap:10px; padding:6px 0; flex-wrap: wrap;">
                    <strong style="font-size:13px;">Régler une tranche (solde : {{ Number(enrollment.balance).toLocaleString('fr-FR') }} XAF)</strong>
                    <input v-model.number="payAmount" type="number" min="1" :max="enrollment.balance" class="ie-input" style="width:140px;" />
                    <select v-model="payProvider" class="ie-select" style="width:220px;">
                      <option v-for="p in PAYMENT_PROVIDERS" :key="p.value" :value="p.value">{{ p.label }}</option>
                    </select>
                    <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="paying" @click="confirmPayment(enrollment)">
                      {{ paying ? "Paiement…" : "Confirmer" }}
                    </button>
                    <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="payFormFor = null">Annuler</button>
                    <span v-if="payError" style="color: var(--ie-red); font-size: 12px;">{{ payError }}</span>
                  </div>
                </td>
              </tr>
              <tr v-if="settlementFormFor === enrollment.id">
                <td colspan="7" style="background:#fafbfc;">
                  <div style="display:flex; align-items:center; gap:10px; padding:6px 0;">
                    <label class="ie-label" style="margin:0;">Montant réglé (XAF)</label>
                    <input v-model.number="settlementAmount" type="number" min="0" class="ie-input" style="width:160px;" />
                    <button class="ie-btn ie-btn-primary ie-btn-sm" @click="recordSettlement(enrollment)">Enregistrer</button>
                    <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="settlementFormFor = null">Annuler</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-id-badge" text="Aucune inscription enregistrée." />
    </div>

    <div class="ie-card ie-section">
      <div class="ie-card-header">
        <h2><i class="fa-solid fa-id-card"></i>Badges</h2>
        <button v-if="auth.role === 'admin'" class="ie-btn ie-btn-ghost ie-btn-sm" @click="showBadgeForm = !showBadgeForm">
          <i class="fa-solid" :class="showBadgeForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showBadgeForm ? "Annuler" : "Nouveau badge" }}
        </button>
      </div>
      <div v-if="showBadgeForm" class="ie-card-body" style="border-bottom: 1px solid var(--ie-line);">
        <form class="ie-form-row" style="align-items: end; flex-wrap: wrap;" @submit.prevent="submitBadge">
          <div>
            <label class="ie-label">Titulaire</label>
            <select v-model="badgeForm.user" class="ie-select" required>
              <option value="" disabled>Choisir un utilisateur</option>
              <option v-for="u in users" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Matricule</label>
            <input v-model="badgeForm.matricule" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Type</label>
            <select v-model="badgeForm.purpose" class="ie-select">
              <option value="training">Formation</option>
              <option value="employment">Employé</option>
              <option value="event">Événement</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Valide du</label>
            <input v-model="badgeForm.valid_from" type="date" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Valide au</label>
            <input v-model="badgeForm.valid_until" type="date" class="ie-input" required />
          </div>
          <button class="ie-btn ie-btn-primary" type="submit">Créer</button>
        </form>
      </div>
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="badges.length">
        <table class="ie-table">
          <thead>
            <tr><th>Matricule</th><th>Titulaire</th><th>Type</th><th>Validité</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="badge in badges" :key="badge.id">
              <td style="font-family: monospace; font-size: 12px;">{{ badge.matricule }}</td>
              <td>{{ badge.holder_name }}</td>
              <td>{{ badge.purpose }}</td>
              <td>{{ badge.valid_from }} — {{ badge.valid_until }}</td>
              <td><span class="ie-badge" :class="badge.is_currently_valid ? 'ie-badge-success' : 'ie-badge-neutral'">{{ badge.is_currently_valid ? "Valide" : "Expiré" }}</span></td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="downloadBadge(badge)">
                  <i class="fa-solid fa-download"></i> PDF
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-id-card" text="Aucun badge créé." />
    </div>
  </div>
</template>

<style scoped>
.ie-enroll-photo {
  width: 34px; height: 34px; border-radius: 50%; overflow: hidden;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-enroll-photo img { width: 100%; height: 100%; object-fit: cover; }
.ie-enroll-photo i { color: var(--ie-navy); opacity: 0.4; font-size: 13px; }
</style>

