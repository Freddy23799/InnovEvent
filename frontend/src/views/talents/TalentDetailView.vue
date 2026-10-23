<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

// Le contact WhatsApp passe par le numéro d'InnovEvent : la plateforme
// reste l'intermédiaire et met ensuite le prestataire en relation.
const WHATSAPP_CONTACT = "237673003993";

const route = useRoute();
const router = useRouter();
const toast = useToastStore();
const talent = ref(null);
const loading = ref(true);
const notFound = ref(false);
const contacting = ref(false);
const lightboxItem = ref(null);

const skills = computed(() => (talent.value?.competences || "").split(",").map((s) => s.trim()).filter(Boolean));
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
        <div class="avatar">
          <img v-if="talent.photo" v-img.eager="talent.photo" :alt="talent.full_name" />
          <i v-else class="fa-solid fa-user"></i>
        </div>
        <div class="identity">
          <h1>{{ talent.full_name }}</h1>
          <p class="meta">
            <span><i class="fa-solid fa-location-dot"></i> {{ talent.city || "Cameroun" }}</span>
            <span><i class="fa-solid fa-briefcase"></i> {{ talent.opportunity_type_display }}</span>
            <span><i class="fa-regular fa-clock"></i> Disponibilité : {{ talent.disponibilite_display }}</span>
          </p>
          <span class="verification" :class="{ ok: talent.is_verified }">
            <i class="fa-solid fa-shield-halved"></i> {{ talent.verification_status_display }}
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
      </header>

      <div class="columns">
        <div class="ie-card ie-card-body">
          <h2>Compétences</h2>
          <div v-if="skills.length" class="skills"><span v-for="skill in skills" :key="skill">{{ skill }}</span></div>
          <p v-else class="muted">Non renseignées.</p>
          <h2>Formation</h2>
          <p class="text">{{ talent.formation || "Non renseignée." }}</p>
        </div>
        <div class="ie-card ie-card-body">
          <h2>Expérience</h2>
          <p class="text">{{ talent.experience || "Non renseignée." }}</p>
        </div>
      </div>

      <div class="ie-card ie-card-body">
        <h2>Réalisations</h2>
        <div v-if="talent.portfolio_items.length" class="portfolio">
          <button v-for="item in talent.portfolio_items" :key="item.id" type="button" class="portfolio-item" @click="lightboxItem = item">
            <img v-img="item.image" :alt="item.caption || talent.full_name" />
            <span v-if="item.caption">{{ item.caption }}</span>
          </button>
        </div>
        <p v-else class="muted">Aucune réalisation publiée pour le moment.</p>
      </div>
    </template>

    <div v-if="lightboxItem" class="lightbox" @click="lightboxItem = null">
      <img v-img="lightboxItem.image" :alt="lightboxItem.caption" />
      <p v-if="lightboxItem.caption">{{ lightboxItem.caption }}</p>
    </div>
  </section>
</template>

<style scoped>
.talent-detail{max-width:1100px;margin:0 auto;min-width:0;display:grid;gap:16px}.back-link{color:var(--ie-muted);font-size:13px;text-decoration:none}.back-link:hover{color:var(--ie-ink)}.profile-head{display:flex;align-items:center;gap:22px;padding:24px;border-radius:18px}.avatar{display:grid;place-items:center;width:120px;height:120px;flex:0 0 120px;overflow:hidden;border-radius:50%;background:#eef0f2;color:#9aa3ac;font-size:42px}.avatar img{width:100%;height:100%;object-fit:cover}.identity{flex:1;min-width:0}.identity h1{margin:0;color:var(--ie-ink);font-size:clamp(24px,3vw,32px)}.meta{display:flex;flex-wrap:wrap;gap:6px 16px;margin:8px 0 10px;color:var(--ie-muted);font-size:13px}.verification{display:inline-flex;gap:6px;align-items:center;padding:5px 10px;border-radius:20px;background:#eef0f2;color:#66717e;font-size:11px;font-weight:700}.verification.ok{background:#e9f6ef;color:#28734f}.contact-actions{display:flex;flex-direction:column;gap:8px;width:260px;flex-shrink:0}.contact-actions .ie-btn{justify-content:center}.whatsapp i{color:#25d366}.contact-actions small{color:var(--ie-muted);font-size:11px;line-height:1.4}.columns{display:grid;grid-template-columns:1fr 1fr;gap:16px}h2{margin:0 0 10px;color:var(--ie-ink);font-size:15px}h2:not(:first-child){margin-top:20px}.text{margin:0;color:#3c4b5b;font-size:14px;line-height:1.6;white-space:pre-line}.muted{margin:0;color:var(--ie-muted);font-size:13px}.skills{display:flex;flex-wrap:wrap;gap:6px}.skills span{font-size:12px;padding:6px 10px;border-radius:20px;background:#f0f3f7;color:#39495b}.portfolio{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}.portfolio-item{position:relative;aspect-ratio:4/3;padding:0;overflow:hidden;border:1px solid var(--ie-border);border-radius:10px;background:none;cursor:zoom-in}.portfolio-item img{width:100%;height:100%;object-fit:cover}.portfolio-item span{position:absolute;inset:auto 0 0;padding:6px 8px;background:linear-gradient(transparent,#000a);color:#fff;font-size:11px;text-align:left}.lightbox{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:16px;background:#000d;cursor:zoom-out}.lightbox img{max-width:100%;max-height:85vh;border-radius:8px}.lightbox p{margin:0;color:#fff}@media(max-width:860px){.profile-head{flex-direction:column;text-align:center}.meta{justify-content:center}.contact-actions{width:100%}.columns{grid-template-columns:1fr}}
</style>
