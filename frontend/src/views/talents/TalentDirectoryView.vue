<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";

// Annuaire réservé aux prestataires (consultation gratuite) : seuls les
// talents dont l'abonnement « Visibilité talent » est actif y apparaissent.
const talents = ref([]);
const loading = ref(true);
const filters = reactive({ search: "", city__icontains: "", opportunity_type: "", disponibilite: "" });

async function loadTalents() {
  loading.value = true;
  try {
    const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
    const { data } = await api.get("/talents/", { params });
    talents.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

let searchTimer = null;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadTalents, 300);
}

function skillsOf(talent) {
  return (talent.competences || "").split(",").map((s) => s.trim()).filter(Boolean).slice(0, 4);
}

onMounted(loadTalents);
</script>

<template>
  <section class="talent-directory">
    <header class="page-hero">
      <div>
        <span class="eyebrow"><i class="fa-solid fa-users"></i> Talents de l'événementiel</span>
        <h1>Trouvez le talent qu'il vous faut</h1>
        <p>Consultez les profils, les réalisations et contactez directement les talents disponibles.</p>
      </div>
    </header>

    <div class="ie-card filters">
      <div class="search">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="filters.search" class="ie-input" placeholder="Nom, compétence, ville…" @input="onSearchInput" />
      </div>
      <input v-model="filters.city__icontains" class="ie-input" placeholder="Ville" @input="onSearchInput" />
      <select v-model="filters.opportunity_type" class="ie-select" @change="loadTalents">
        <option value="">Tous les contrats</option>
        <option value="one_off">Mission ponctuelle</option>
        <option value="fixed_term">CDD</option>
        <option value="permanent">CDI</option>
        <option value="internship">Stage</option>
        <option value="freelance">Freelance</option>
      </select>
      <select v-model="filters.disponibilite" class="ie-select" @change="loadTalents">
        <option value="">Toute disponibilité</option>
        <option value="immediate">Immédiate</option>
        <option value="within_month">Sous 1 mois</option>
        <option value="to_define">À définir</option>
      </select>
    </div>

    <div v-if="loading" class="talent-grid" aria-busy="true"><div v-for="i in 6" :key="i" class="ie-skeleton ie-skeleton-card"></div></div>
    <div v-else-if="talents.length" class="talent-grid">
      <router-link v-for="talent in talents" :key="talent.id" :to="{ name: 'talent-detail', params: { id: talent.id } }" class="ie-card talent-card">
        <div class="talent-photo">
          <img v-if="talent.photo" v-img="talent.photo" :alt="talent.full_name" />
          <i v-else class="fa-solid fa-user"></i>
        </div>
        <div class="talent-body">
          <h3>{{ talent.full_name }} <i v-if="talent.is_verified" class="fa-solid fa-circle-check verified" :title="talent.verification_status_display"></i></h3>
          <p class="meta"><i class="fa-solid fa-location-dot"></i> {{ talent.city || "Cameroun" }} · {{ talent.opportunity_type_display }}</p>
          <div class="skills"><span v-for="skill in skillsOf(talent)" :key="skill">{{ skill }}</span></div>
          <div class="card-bottom">
            <span><i class="fa-regular fa-clock"></i> {{ talent.disponibilite_display }}</span>
            <span><i class="fa-regular fa-images"></i> {{ talent.portfolio_items.length }} réalisation{{ talent.portfolio_items.length > 1 ? "s" : "" }}</span>
          </div>
        </div>
      </router-link>
    </div>
    <EmptyState v-else icon="fa-solid fa-users" text="Aucun talent ne correspond à votre recherche pour le moment." />
  </section>
</template>

<style scoped>
.talent-directory{max-width:1200px;margin:0 auto;min-width:0}.page-hero{padding:32px 36px;border-radius:20px;color:#fff;background:radial-gradient(ellipse at 90% 15%,#dd595c 0,transparent 38%),linear-gradient(120deg,#172638,#30485e 70%,#742b31);box-shadow:0 16px 40px #18283b20}.eyebrow{display:inline-flex;gap:7px;align-items:center;color:#ffd4d4;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.page-hero h1{font-size:clamp(28px,4vw,40px);margin:12px 0 8px;line-height:1.08}.page-hero p{margin:0;color:#e2e8ef;font-size:14px}.filters{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px;margin:20px 0;padding:14px;border-radius:14px}.search{position:relative}.search i{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--ie-muted);font-size:13px}.search .ie-input{padding-left:34px}.talent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,270px),1fr));gap:16px}.talent-card{display:flex;flex-direction:column;overflow:hidden;border-radius:16px;color:inherit;text-decoration:none;transition:transform .2s,box-shadow .2s}.talent-card:hover{transform:translateY(-3px);box-shadow:0 15px 35px #18283b18}.talent-photo{display:grid;place-items:center;height:190px;background:#eef0f2;color:#9aa3ac;font-size:42px}.talent-photo img{width:100%;height:100%;object-fit:cover}.talent-body{display:flex;flex:1;flex-direction:column;padding:16px 18px}.talent-body h3{margin:0;color:var(--ie-ink);font-size:17px}.verified{color:#28734f;font-size:14px}.meta{margin:6px 0 0;color:var(--ie-muted);font-size:12px}.skills{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.skills span{font-size:11px;padding:5px 8px;border-radius:20px;background:#f0f3f7;color:#39495b}.card-bottom{display:flex;justify-content:space-between;gap:8px;margin-top:auto;padding-top:12px;border-top:1px solid #edf0f3;color:#34465a;font-size:12px}@media(max-width:760px){.page-hero{padding:25px 22px}.filters{grid-template-columns:1fr 1fr}.search{grid-column:1/-1}}@media(max-width:480px){.filters{grid-template-columns:1fr}}
</style>
