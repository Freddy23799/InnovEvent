<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import { citiesForCountry } from "../../data/countries";
import api from "../../services/api";

// Annuaire réservé aux prestataires (consultation gratuite) : seuls les
// talents dont l'abonnement « Visibilité talent » est actif y apparaissent.
const CITY_NAMES = citiesForCountry("CM").map((c) => c.name);
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
  return (talent.competences || "").split(",").map((s) => s.trim()).filter(Boolean).slice(0, 3);
}

function extraSkillsCount(talent) {
  return Math.max((talent.competences || "").split(",").map((s) => s.trim()).filter(Boolean).length - 3, 0);
}

// Les villes saisies avant la liste déroulante peuvent être en minuscules.
function cityOf(talent) {
  const city = (talent.city || "").trim();
  return city ? city.charAt(0).toUpperCase() + city.slice(1) : "Cameroun";
}

function initialsOf(talent) {
  return (talent.full_name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
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
      <select v-model="filters.city__icontains" class="ie-select" @change="loadTalents">
        <option value="">Toutes les villes</option>
        <option v-for="city in CITY_NAMES" :key="city" :value="city">{{ city }}</option>
      </select>
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
          <span v-else class="talent-initials">{{ initialsOf(talent) || "?" }}</span>
          <span class="availability" :class="talent.disponibilite">
            <i class="fa-solid fa-circle"></i> {{ talent.disponibilite_display }}
          </span>
        </div>
        <div class="talent-body">
          <h3>
            <span class="name">{{ talent.full_name }}</span>
            <i v-if="talent.is_verified" class="fa-solid fa-circle-check verified" :title="talent.verification_status_display"></i>
          </h3>
          <div class="meta">
            <span><i class="fa-solid fa-location-dot"></i> {{ cityOf(talent) }}</span>
            <span><i class="fa-solid fa-briefcase"></i> {{ talent.opportunity_type_display }}</span>
          </div>
          <div class="skills">
            <span v-for="skill in skillsOf(talent)" :key="skill">{{ skill }}</span>
            <span v-if="extraSkillsCount(talent)" class="more">+{{ extraSkillsCount(talent) }}</span>
            <span v-if="!skillsOf(talent).length" class="empty">Compétences non renseignées</span>
          </div>
          <div class="card-bottom">
            <span class="works"><i class="fa-regular fa-images"></i> {{ talent.portfolio_items.length }} réalisation{{ talent.portfolio_items.length > 1 ? "s" : "" }}</span>
            <span class="cta">Voir le profil <i class="fa-solid fa-arrow-right"></i></span>
          </div>
        </div>
      </router-link>
    </div>
    <EmptyState v-else icon="fa-solid fa-users" text="Aucun talent ne correspond à votre recherche pour le moment." />
  </section>
</template>

<style scoped>
.talent-directory{max-width:1200px;margin:0 auto;min-width:0}.page-hero{padding:32px 36px;border-radius:20px;color:#fff;background: var(--ie-hero-gradient);box-shadow:0 16px 40px #18283b20}.eyebrow{display:inline-flex;gap:7px;align-items:center;color:#ffd4d4;font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.page-hero h1{font-size:clamp(28px,4vw,40px);margin:12px 0 8px;line-height:1.08}.page-hero p{margin:0;color:#e2e8ef;font-size:14px}.filters{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px;margin:20px 0;padding:14px;border-radius:14px}.search{position:relative}.search i{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--ie-muted);font-size:13px}.search .ie-input{padding-left:34px}
.talent-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr));gap:18px}
.talent-card{display:flex;flex-direction:column;overflow:hidden;border-radius:16px;color:inherit;text-decoration:none;transition:transform .2s,box-shadow .2s}
.talent-card:hover{transform:translateY(-3px);box-shadow:0 15px 35px #18283b18}
.talent-photo{position:relative;display:grid;place-items:center;aspect-ratio:4/3;background:linear-gradient(135deg,#23364b,#4a5f75);overflow:hidden}
.talent-photo img{width:100%;height:100%;object-fit:cover;transition:transform .3s ease}.talent-card:hover .talent-photo img{transform:scale(1.04)}
.talent-initials{display:grid;place-items:center;width:84px;height:84px;border-radius:50%;background:#ffffff1f;border:2px solid #ffffff40;color:#fff;font-size:28px;font-weight:800;letter-spacing:.04em}
.availability{position:absolute;top:12px;left:12px;display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:20px;background:#fffffff0;color:#39495b;font-size:11px;font-weight:700;box-shadow:0 2px 8px #0002}
.availability i{font-size:7px;color:#9aa3ac}.availability.immediate i{color:#22a05b}.availability.within_month i{color:#e0a100}
.talent-body{display:flex;flex:1;flex-direction:column;gap:10px;padding:16px 18px 14px}
.talent-body h3{display:flex;align-items:center;gap:6px;margin:0;color:var(--ie-ink);font-size:17px;line-height:1.25;text-transform:capitalize}
.talent-body h3 .name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.verified{flex-shrink:0;color:#28734f;font-size:14px}
.meta{display:flex;flex-wrap:wrap;gap:6px}
.meta span{display:inline-flex;align-items:center;gap:5px;padding:4px 9px;border-radius:8px;background:#f5f7fa;color:#4b5a6a;font-size:12px;font-weight:600}
.meta i{color:var(--ie-red);font-size:11px}
.skills{display:flex;flex-wrap:wrap;gap:6px;min-height:26px}
.skills span{font-size:11.5px;font-weight:600;padding:5px 10px;border-radius:20px;background:var(--ie-red-soft);color:var(--ie-red);text-transform:capitalize}
.skills .more{background:#eef0f2;color:#5d6771}.skills .empty{background:none;padding:5px 0;color:var(--ie-muted);font-weight:500;text-transform:none}
.card-bottom{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:auto;padding-top:12px;border-top:1px solid #edf0f3;font-size:12px}
.works{color:#4b5a6a}.works i{margin-right:4px}
.cta{color:var(--ie-red);font-weight:700}.cta i{font-size:11px;margin-left:3px;transition:transform .2s}.talent-card:hover .cta i{transform:translateX(3px)}
@media(max-width:760px){.page-hero{padding:25px 22px}.filters{grid-template-columns:1fr 1fr}.search{grid-column:1/-1}}@media(max-width:480px){.filters{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.talent-card,.talent-photo img,.cta i{transition:none}}
</style>
