<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

// Le contact WhatsApp passe par le numéro d'InnovEvent : la plateforme
// reste l'intermédiaire et met ensuite le prestataire en relation.
const WHATSAPP_CONTACT = "237673003993";

const route = useRoute();
const router = useRouter();
const toast = useToastStore();
const lightbox = useLightboxStore();
const talent = ref(null);
const loading = ref(true);
const notFound = ref(false);
const contacting = ref(false);

const skills = computed(() => (talent.value?.competences || "").split(",").map((s) => s.trim()).filter(Boolean));
const facts = computed(() => {
  if (!talent.value) return [];
  return [
    { icon: "fa-solid fa-location-dot", label: "Ville", value: talent.value.city || "Cameroun" },
    { icon: "fa-solid fa-briefcase", label: "Recherche", value: talent.value.opportunity_type_display },
    { icon: "fa-regular fa-clock", label: "Disponibilité", value: talent.value.disponibilite_display },
    { icon: "fa-regular fa-images", label: "Réalisations", value: String(talent.value.portfolio_items.length) },
  ];
});

function openPortfolio(index) {
  const items = talent.value.portfolio_items.map((item) => ({ url: item.image, caption: item.caption }));
  lightbox.openGallery(items, index);
}

const whatsappUrl = computed(() => {
  if (!talent.value) return "";
  const message = `Bonjour InnovEvent, je souhaite être mis en relation avec le talent ${talent.value.full_name} (profil n° ${talent.value.id}).`;
  return `https://wa.me/${WHATSAPP_CONTACT}?text=${encodeURIComponent(message)}`;
});

async function loadTalent() {
  loading.value = true;
  try {
    const { data } = await api.get(`/talents/${route.params.id}/`);
    talent.value = data;
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
    else throw e;
  } finally {
    loading.value = false;
  }
}

async function contactByMessaging() {
  contacting.value = true;
  try {
    const { data } = await api.post(`/talents/${talent.value.id}/contact/`);
    await router.push({ name: "messaging", query: { conversation: data.id } });
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d'ouvrir la conversation.");
  } finally {
    contacting.value = false;
  }
}

onMounted(loadTalent);
</script>

<template>
  <section class="talent-detail">
    <router-link :to="{ name: 'talents-directory' }" class="back-link"><i class="fa-solid fa-arrow-left"></i> Tous les talents</router-link>

    <div v-if="loading" class="ie-skeleton" style="height: 320px; border-radius: 18px;" aria-busy="true"></div>
    <EmptyState v-else-if="notFound" icon="fa-solid fa-user-slash" text="Ce profil n'est plus visible." />

    <template v-else-if="talent">
      <header class="ie-card profile-head">
        <div class="profile-banner"></div>
        <div class="profile-main">
          <div class="avatar">
            <img v-if="talent.photo" v-img.eager="talent.photo" :alt="talent.full_name" />
            <i v-else class="fa-solid fa-user"></i>
          </div>
          <div class="identity">
            <h1>{{ talent.full_name }}</h1>
            <p class="headline">
              {{ talent.opportunity_type_display }} · <i class="fa-solid fa-location-dot"></i> {{ talent.city || "Cameroun" }}
            </p>
            <span class="verification" :class="{ ok: talent.is_verified }">
              <i class="fa-solid" :class="talent.is_verified ? 'fa-circle-check' : 'fa-shield-halved'"></i> {{ talent.verification_status_display }}
            </span>
          </div>
          <div class="contact-actions">
            <button class="ie-btn ie-btn-primary" :disabled="contacting" @click="contactByMessaging">
              <i class="fa-solid fa-message"></i> {{ contacting ? "Ouverture…" : "Contacter via la messagerie" }}
            </button>
            <a class="ie-btn ie-btn-ghost whatsapp" :href="whatsappUrl" target="_blank" rel="noopener">
              <i class="fa-brands fa-whatsapp"></i> Contacter par WhatsApp
            </a>
            <small>Le contact WhatsApp passe par l'équipe InnovEvent, qui vous met en relation.</small>
          </div>
        </div>
      </header>

      <div class="facts">
        <div v-for="fact in facts" :key="fact.label" class="ie-card fact">
          <span class="fact-icon"><i :class="fact.icon"></i></span>
          <div>
            <small>{{ fact.label }}</small>
            <strong>{{ fact.value }}</strong>
          </div>
        </div>
      </div>

      <div class="ie-card ie-card-body section">
        <h2><span class="section-icon"><i class="fa-solid fa-wand-magic-sparkles"></i></span>Compétences</h2>
        <div v-if="skills.length" class="skills"><span v-for="skill in skills" :key="skill">{{ skill }}</span></div>
        <p v-else class="muted">Non renseignées.</p>
      </div>

      <div class="columns">
        <div class="ie-card ie-card-body section">
          <h2><span class="section-icon"><i class="fa-solid fa-graduation-cap"></i></span>Formation</h2>
          <p class="text">{{ talent.formation || "Non renseignée." }}</p>
        </div>
        <div class="ie-card ie-card-body section">
          <h2><span class="section-icon"><i class="fa-solid fa-briefcase"></i></span>Expérience</h2>
          <p class="text">{{ talent.experience || "Non renseignée." }}</p>
        </div>
      </div>

      <div class="ie-card ie-card-body section">
        <h2>
          <span class="section-icon"><i class="fa-solid fa-images"></i></span>Réalisations
          <span v-if="talent.portfolio_items.length" class="count">{{ talent.portfolio_items.length }}</span>
        </h2>
        <div v-if="talent.portfolio_items.length" class="portfolio">
          <button v-for="(item, index) in talent.portfolio_items" :key="item.id" type="button" class="portfolio-item" @click="openPortfolio(index)">
            <img v-img="item.image" :alt="item.caption || talent.full_name" />
            <span v-if="item.caption">{{ item.caption }}</span>
          </button>
        </div>
        <p v-else class="muted">Aucune réalisation publiée pour le moment.</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.talent-detail{max-width:1100px;margin:0 auto;min-width:0;display:grid;gap:16px}
.back-link{color:var(--ie-muted);font-size:13px;text-decoration:none}.back-link:hover{color:var(--ie-ink)}
.profile-head{overflow:hidden;border-radius:18px;padding:0}
.profile-banner{height:96px;background:var(--ie-hero-gradient)}
.profile-main{display:flex;align-items:flex-end;gap:22px;padding:0 24px 22px}
.avatar{display:grid;place-items:center;width:124px;height:124px;flex:0 0 124px;margin-top:-56px;overflow:hidden;border:5px solid #fff;border-radius:50%;background:#eef0f2;color:#9aa3ac;font-size:42px;box-shadow:0 8px 22px #18283b26}
.avatar img{width:100%;height:100%;object-fit:cover}
.identity{flex:1;min-width:0;padding-top:12px}
.identity h1{margin:0;color:var(--ie-ink);font-size:clamp(22px,3vw,30px);line-height:1.15}
.headline{margin:6px 0 10px;color:var(--ie-muted);font-size:13.5px}.headline i{color:var(--ie-red)}
.verification{display:inline-flex;gap:6px;align-items:center;padding:5px 10px;border-radius:20px;background:#eef0f2;color:#66717e;font-size:11px;font-weight:700}.verification.ok{background:#e9f6ef;color:#28734f}
.contact-actions{display:flex;flex-direction:column;gap:8px;width:260px;flex-shrink:0}.contact-actions .ie-btn{justify-content:center}.whatsapp i{color:#25d366}.contact-actions small{color:var(--ie-muted);font-size:11px;line-height:1.4}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.fact{display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;min-width:0}
.fact-icon{display:grid;place-items:center;width:38px;height:38px;flex:0 0 38px;border-radius:11px;background:var(--ie-red-soft);color:var(--ie-red);font-size:15px}
.fact div{min-width:0}.fact small{display:block;color:var(--ie-muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.fact strong{display:block;color:var(--ie-ink);font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.section{border-radius:14px}
h2{display:flex;align-items:center;gap:10px;margin:0 0 14px;color:var(--ie-ink);font-size:15px}
.section-icon{display:grid;place-items:center;width:30px;height:30px;border-radius:9px;background:#f0f3f7;color:var(--ie-navy);font-size:13px}
.count{margin-left:auto;padding:2px 9px;border-radius:20px;background:#f0f3f7;color:#39495b;font-size:12px}
.text{margin:0;color:#3c4b5b;font-size:14px;line-height:1.65;white-space:pre-line}
.muted{margin:0;color:var(--ie-muted);font-size:13px}
.skills{display:flex;flex-wrap:wrap;gap:8px}.skills span{font-size:12.5px;font-weight:600;padding:7px 12px;border-radius:20px;background:#f0f3f7;color:#39495b}
.portfolio{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
.portfolio-item{position:relative;aspect-ratio:4/3;padding:0;overflow:hidden;border:1px solid var(--ie-border);border-radius:10px;background:none;cursor:zoom-in}
.portfolio-item img{width:100%;height:100%;object-fit:cover;transition:transform .25s ease}.portfolio-item:hover img{transform:scale(1.05)}
.portfolio-item span{position:absolute;inset:auto 0 0;padding:6px 8px;background:linear-gradient(transparent,#000a);color:#fff;font-size:11px;text-align:left}
@media(max-width:860px){.profile-main{flex-direction:column;align-items:center;text-align:center}.identity{padding-top:0}.contact-actions{width:100%}.facts{grid-template-columns:1fr 1fr}.columns{grid-template-columns:1fr}}
@media(max-width:420px){.facts{gap:8px}.fact{padding:12px;gap:10px}.portfolio{grid-template-columns:1fr 1fr;gap:8px}}
</style>
