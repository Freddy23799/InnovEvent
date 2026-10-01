<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const missions = ref([]);
const loading = ref(true);
const submitting = ref(false);
const editingId = ref(null);
const formVisible = ref(false);
const error = ref("");
const emptyForm = { title: "", city: "", description: "", mission_type: "one_off", starts_at: "", compensation: "", skills: "", is_active: true };
const form = reactive({ ...emptyForm });

async function loadMissions() {
  loading.value = true;
  try {
    const { data } = await api.get("/talents/missions/manage/");
    missions.value = data.results || data;
  } catch (e) { toast.error(e?.response?.data?.detail || "Impossible de charger vos missions."); }
  finally { loading.value = false; }
}
function createMission() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  error.value = "";
  formVisible.value = true;
}
function editMission(mission) {
  Object.assign(form, { ...mission, starts_at: mission.starts_at || "" });
  editingId.value = mission.id;
  error.value = "";
  formVisible.value = true;
}
async function saveMission() {
  submitting.value = true;
  error.value = "";
  const payload = { ...form, starts_at: form.starts_at || null };
  try {
    if (editingId.value) await api.patch(`/talents/missions/manage/${editingId.value}/`, payload);
    else await api.post("/talents/missions/manage/", payload);
    toast.success(editingId.value ? "Mission mise à jour." : "Mission publiée.");
    formVisible.value = false;
    await loadMissions();
  } catch (e) {
    error.value = e?.response?.data?.detail || Object.values(e?.response?.data || {}).flat().join(" ") || "Impossible d’enregistrer la mission.";
  } finally { submitting.value = false; }
}
async function deleteMission(mission) {
  if (!window.confirm(`Retirer la mission « ${mission.title} » ?`)) return;
  try {
    await api.delete(`/talents/missions/manage/${mission.id}/`);
    toast.success("Mission retirée.");
    await loadMissions();
  } catch (e) { toast.error(e?.response?.data?.detail || "Impossible de retirer cette mission."); }
}
onMounted(loadMissions);
</script>

<template>
  <section class="provider-missions">
    <header class="page-hero">
      <div><span class="eyebrow"><i class="fa-solid fa-bullhorn"></i> Recrutement événementiel</span><h1>Publiez une mission</h1><p>Présentez vos besoins aux talents disponibles sur InnovEvent.</p></div>
      <button class="ie-btn ie-btn-primary" @click="formVisible ? (formVisible = false) : createMission()"><i class="fa-solid" :class="formVisible ? 'fa-xmark' : 'fa-plus'"></i>{{ formVisible ? "Fermer" : "Nouvelle mission" }}</button>
    </header>

    <form v-if="formVisible" class="ie-card mission-form" @submit.prevent="saveMission">
      <div class="form-heading"><div><span class="eyebrow">Nouvelle annonce</span><h2>{{ editingId ? "Modifier la mission" : "Détails de la mission" }}</h2></div><span class="visibility-pill"><i class="fa-solid fa-eye"></i> Visible par les talents abonnés</span></div>
      <label class="ie-label">Intitulé du poste ou de la mission *</label><input v-model="form.title" class="ie-input" required maxlength="180" placeholder="Ex. Assistant·e de coordination événementielle" />
      <div class="ie-form-row form-grid">
        <div><label class="ie-label">Ville</label><input v-model="form.city" class="ie-input" placeholder="Douala" /></div>
        <div><label class="ie-label">Type de contrat *</label><select v-model="form.mission_type" class="ie-select"><option value="one_off">Mission ponctuelle</option><option value="fixed_term">CDD</option><option value="permanent">CDI</option><option value="internship">Stage</option><option value="freelance">Freelance</option></select></div>
      </div>
      <div class="ie-form-row form-grid">
        <div><label class="ie-label">Date de début</label><input v-model="form.starts_at" type="date" class="ie-input" /></div>
        <div><label class="ie-label">Rémunération</label><input v-model="form.compensation" class="ie-input" placeholder="Ex. 50 000 FCFA / journée" /></div>
      </div>
      <label class="ie-label">Description *</label><textarea v-model="form.description" class="ie-input" rows="4" required placeholder="Décrivez le contexte, les tâches et le profil recherché…"></textarea>
      <label class="ie-label">Compétences recherchées</label><input v-model="form.skills" class="ie-input" placeholder="Séparées par des virgules : coordination, accueil…" />
      <label class="active-switch"><input v-model="form.is_active" type="checkbox" /><span>Publier immédiatement</span></label>
      <p v-if="error" class="ie-alert ie-alert-danger">{{ error }}</p>
      <div class="form-actions"><button type="button" class="ie-btn ie-btn-ghost" @click="formVisible = false">Annuler</button><button class="ie-btn ie-btn-primary" :disabled="submitting">{{ submitting ? "Enregistrement…" : editingId ? "Enregistrer les changements" : "Publier la mission" }}</button></div>
    </form>

    <div class="list-heading"><div><h2>Vos annonces</h2><p>{{ missions.length }} mission{{ missions.length > 1 ? "s" : "" }} publiée{{ missions.length > 1 ? "s" : "" }}</p></div></div>
    <div v-if="loading" class="ie-card ie-card-body">Chargement…</div>
    <div v-else-if="missions.length" class="mission-list">
      <article v-for="mission in missions" :key="mission.id" class="ie-card mission-row">
        <div class="mission-icon"><i class="fa-solid fa-briefcase"></i></div><div class="mission-info"><div class="mission-title-row"><h3>{{ mission.title }}</h3><span class="status" :class="mission.is_active ? 'published' : 'paused'">{{ mission.is_active ? "Publiée" : "En pause" }}</span></div><p>{{ mission.city || "Lieu à préciser" }} · {{ mission.mission_type_display }}<span v-if="mission.starts_at"> · {{ new Date(mission.starts_at).toLocaleDateString('fr-FR') }}</span></p><small>{{ mission.compensation || "Rémunération à discuter" }}</small></div><div class="mission-actions"><button class="ie-btn ie-btn-ghost ie-btn-sm" @click="editMission(mission)"><i class="fa-solid fa-pen"></i><span>Modifier</span></button><button class="ie-btn ie-btn-danger ie-btn-sm" @click="deleteMission(mission)" aria-label="Retirer la mission"><i class="fa-solid fa-trash"></i></button></div>
      </article>
    </div>
    <EmptyState v-else icon="fa-solid fa-briefcase" text="Vous n’avez publié aucune mission. Créez votre première annonce pour rencontrer des talents." />
  </section>
</template>

<style scoped>
.provider-missions{max-width:1100px;margin:0 auto;min-width:0}.page-hero{display:flex;align-items:center;justify-content:space-between;gap:22px;padding:32px 36px;border-radius:20px;color:#fff;background:radial-gradient(ellipse at 90% 15%,#dd595c 0,transparent 38%),linear-gradient(120deg,#172638,#30485e 70%,#742b31);box-shadow:0 16px 40px #18283b20}.eyebrow{display:inline-flex;gap:7px;align-items:center;color:#ffd4d4;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.page-hero h1{font-size:clamp(28px,4vw,40px);margin:12px 0 8px;line-height:1.08}.page-hero p{margin:0;color:#e2e8ef;font-size:14px}.page-hero .ie-btn{flex-shrink:0}.mission-form{margin-top:20px;padding:26px;border-radius:17px}.form-heading{display:flex;justify-content:space-between;align-items:center;gap:14px;margin-bottom:22px}.form-heading h2,.list-heading h2{margin:5px 0;color:var(--ie-ink)}.visibility-pill{padding:8px 11px;border-radius:20px;background:#edf7f1;color:#28734f;font-size:11px;font-weight:700}.mission-form>.ie-label{display:block;margin:14px 0 7px}.form-grid{margin-top:12px}.active-switch{display:flex;align-items:center;gap:9px;margin-top:15px;color:#39495b;font-size:13px}.form-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:18px}.list-heading{margin:28px 2px 14px}.list-heading h2{margin:0}.list-heading p{margin:5px 0 0;color:var(--ie-muted);font-size:12px}.mission-list{display:grid;gap:11px}.mission-row{display:flex;align-items:center;gap:15px;padding:16px;border-radius:14px}.mission-icon{display:grid;place-items:center;width:42px;height:42px;flex:0 0 42px;border-radius:12px;background:#fff0f0;color:#b13238}.mission-info{flex:1;min-width:0}.mission-title-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.mission-title-row h3{margin:0;color:var(--ie-ink);font-size:15px}.mission-info p{margin:5px 0;color:var(--ie-muted);font-size:12px}.mission-info small{color:#3c4b5b;font-size:11px}.status{padding:4px 8px;border-radius:20px;font-size:10px;font-weight:800}.status.published{background:#e9f6ef;color:#28734f}.status.paused{background:#eef0f2;color:#66717e}.mission-actions{display:flex;gap:6px;flex-shrink:0}@media(max-width:760px){.page-hero{align-items:flex-start;flex-direction:column;padding:25px 22px}.form-heading{align-items:flex-start;flex-direction:column}.mission-row{align-items:flex-start}.mission-actions{flex-direction:column}}@media(max-width:560px){.mission-form{padding:18px 14px}.form-actions{flex-direction:column-reverse}.form-actions .ie-btn{width:100%;justify-content:center}.mission-row{position:relative;padding:14px;gap:10px}.mission-icon{width:36px;height:36px;flex-basis:36px}.mission-info{padding-right:0}.mission-title-row{align-items:flex-start;flex-direction:column;gap:6px}.mission-actions{flex-direction:row;margin-left:auto}.mission-actions .ie-btn span{display:none}.visibility-pill{white-space:normal}.page-hero>.ie-btn{width:100%;justify-content:center}}
</style>
