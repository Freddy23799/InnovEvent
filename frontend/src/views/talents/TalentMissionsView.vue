<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import SubscriptionCheckoutModal from "../../components/SubscriptionCheckoutModal.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const router = useRouter();
const contactingMissionId = ref(null);
const missions = ref([]);
const plans = ref([]);
const tiers = ref([]);
const loading = ref(true);
const subscription = ref(null);
const checkoutOpen = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const { data: subscriptionInfo } = await api.get("/marketplace/subscriptions/", { params: { marketplace_type: "talent_missions" } });
    plans.value = subscriptionInfo.plans || [];
    tiers.value = subscriptionInfo.tiers || [];
    subscription.value = subscriptionInfo.marketplaces.find((item) => item.marketplace_type === "talent_missions");
    const { data } = await api.get("/talents/missions/");
    missions.value = data;
  } catch (e) {
    error.value = e?.response?.data?.detail || "Impossible de charger les missions.";
  } finally { loading.value = false; }
}

const subscriptionPrice = computed(() => plans.value[0] || null);
function formatPrice(price) {
  return Number(price || 0).toLocaleString("fr-FR");
}

async function openCheckout() {
  if (!plans.value.length) {
    toast.error("Aucune formule n’est configurée pour les missions talent. Contactez l’administration.");
    return;
  }
  checkoutOpen.value = true;
}

async function onSubscribed() {
  checkoutOpen.value = false;
  await load();
  toast.success("Votre accès aux missions est activé.");
}

async function contactProvider(mission) {
  contactingMissionId.value = mission.id;
  try {
    const { data } = await api.post(`/talents/missions/${mission.id}/contact/`);
    await router.push({ name: "messaging", query: { conversation: data.id } });
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d’ouvrir la conversation.");
  } finally { contactingMissionId.value = null; }
}
onMounted(load);
</script>

<template>
  <section class="talent-page">
    <header class="talent-hero">
      <div><span class="hero-kicker"><i class="fa-solid fa-sparkles"></i> Espace talents</span><h1>La prochaine mission commence ici.</h1><p>Découvrez les opportunités publiées par les prestataires de l’événementiel.</p></div>
      <div v-if="subscriptionPrice" class="hero-price"><i class="fa-solid fa-lock"></i><strong>{{ formatPrice(subscriptionPrice.price) }} FCFA</strong><span>/ {{ subscriptionPrice.duration_days }} jours</span></div>
    </header>
    <div class="page-toolbar"><div><h2>Missions à saisir</h2><p>Offres proposées par des prestataires au Cameroun.</p></div><span class="demo-label"><i class="fa-solid fa-circle-info"></i> Annonces de démonstration</span></div>
    <div v-if="loading" class="ie-card ie-card-body">Chargement des missions…</div>
    <div v-else-if="error && !missions.length" class="access-card ie-card">
      <div class="lock-icon"><i class="fa-solid fa-lock"></i></div><p class="access-kicker">Accès premium</p><h2>Débloquez toutes les opportunités</h2><p>{{ error }}</p>
      <div class="included"><span><i class="fa-solid fa-check"></i> Missions de prestataires vérifiés</span><span><i class="fa-solid fa-check"></i> Nouvelles annonces chaque semaine</span><span><i class="fa-solid fa-check"></i> 30 jours d’accès complet</span></div>
      <button class="ie-btn ie-btn-primary" :disabled="!plans.length" @click="openCheckout">
        {{ plans.length ? `S’abonner · ${formatPrice(subscriptionPrice.price)} FCFA` : "Aucune formule disponible" }}
      </button>
      <small v-if="!plans.length">Le tarif doit être configuré par l’administration depuis la gestion des abonnements.</small>
      <small>Paiement sécurisé via les moyens disponibles sur InnovEvent.</small>
    </div>
    <div v-else class="mission-grid">
      <article v-for="mission in missions" :key="mission.id" class="ie-card mission-card">
        <div class="card-top"><span class="mission-type">{{ mission.mission_type_display }}</span><i class="fa-solid fa-arrow-up-right-from-square"></i></div>
        <h3>{{ mission.title }}</h3><p class="provider"><i class="fa-solid fa-building"></i> {{ mission.provider_name }} <span>· {{ mission.city || "Cameroun" }}</span></p>
        <p class="description">{{ mission.description }}</p><div class="skills"><span v-for="skill in mission.skills.split(',').map(s => s.trim()).filter(Boolean)" :key="skill">{{ skill }}</span></div>
        <div class="card-bottom"><span><i class="fa-solid fa-coins"></i> {{ mission.compensation || "À discuter" }}</span><span v-if="mission.starts_at"><i class="fa-regular fa-calendar"></i> {{ new Date(mission.starts_at).toLocaleDateString('fr-FR') }}</span></div>
        <button class="ie-btn ie-btn-primary contact-button" :disabled="contactingMissionId === mission.id" @click="contactProvider(mission)"><i class="fa-solid fa-message"></i> {{ contactingMissionId === mission.id ? "Ouverture…" : "Participer à la mission" }}</button>
      </article>
    </div>
    <SubscriptionCheckoutModal v-if="checkoutOpen" marketplace-type="talent_missions" marketplace-label="Missions pour talents" :plans="plans" :tiers="tiers" @close="checkoutOpen = false" @subscribed="onSubscribed" />
  </section>
</template>

<style scoped>
.talent-page{max-width:1200px;margin:auto;min-width:0}.talent-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:34px 38px;border-radius:22px;color:#fff;background:radial-gradient(ellipse at 90% 20%,#e85f5b 0,transparent 35%),linear-gradient(120deg,#172638,#253d53 65%,#8f292e);box-shadow:0 18px 40px #18283b25}.hero-kicker{display:inline-flex;gap:8px;align-items:center;color:#ffd4d4;text-transform:uppercase;font-weight:800;font-size:11px;letter-spacing:.14em}.talent-hero h1{font-size:clamp(28px,4vw,42px);line-height:1.08;margin:14px 0 10px;max-width:660px}.talent-hero p{color:#e0e7ef;margin:0}.hero-price{display:flex;align-items:baseline;gap:6px;white-space:nowrap;padding:15px 18px;border:1px solid #ffffff45;border-radius:14px;background:#ffffff16}.hero-price i{align-self:center;margin-right:3px;color:#ffd1d1}.hero-price strong{font-size:20px}.hero-price span{font-size:12px;color:#d7e0e8}.page-toolbar{display:flex;justify-content:space-between;align-items:end;gap:12px;margin:30px 2px 16px}.page-toolbar h2{margin:0;color:var(--ie-ink)}.page-toolbar p{margin:5px 0 0;color:var(--ie-muted);font-size:13px}.demo-label{font-size:11px;color:#586779;background:#edf1f5;border-radius:20px;padding:8px 11px}.mission-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:16px}.mission-card{padding:21px;border-radius:16px;transition:transform .2s,box-shadow .2s}.mission-card:hover{transform:translateY(-3px);box-shadow:0 15px 35px #18283b18}.card-top{display:flex;justify-content:space-between;color:#c0393d}.mission-type{font-size:11px;font-weight:700;color:#994044;background:#fff0f0;padding:6px 9px;border-radius:20px}.mission-card h3{font-size:18px;color:var(--ie-ink);margin:16px 0 9px}.provider,.description{font-size:13px;color:var(--ie-muted);line-height:1.55}.provider{font-weight:700}.provider span{font-weight:400}.description{min-height:60px}.skills{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 17px}.skills span{font-size:11px;padding:5px 8px;border-radius:20px;background:#f0f3f7;color:#39495b}.card-bottom{border-top:1px solid #edf0f3;padding-top:13px;display:flex;justify-content:space-between;gap:8px;color:#34465a;font-size:12px}.contact-button{width:100%;margin-top:16px}.access-card{max-width:600px;margin:20px auto;padding:34px;text-align:center;border-radius:20px}.lock-icon{margin:auto;width:52px;height:52px;display:grid;place-items:center;color:#b02b31;background:#fff0f0;border-radius:15px;font-size:20px}.access-kicker{color:#a42f34;text-transform:uppercase;letter-spacing:.15em;font-size:10px;font-weight:800;margin:18px 0 6px}.access-card h2{margin:0 0 10px;color:var(--ie-ink)}.access-card>p{color:var(--ie-muted)}.included{display:grid;gap:10px;text-align:left;max-width:300px;margin:22px auto;color:#34465a;font-size:13px}.included i{color:#278060;margin-right:8px}.access-card small{display:block;color:var(--ie-muted);margin-top:12px}@media(max-width:760px){.talent-hero{align-items:flex-start;flex-direction:column;padding:28px}.hero-price{align-self:stretch;justify-content:center}.mission-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:650px){.talent-hero{padding:24px 20px}.page-toolbar{align-items:flex-start;flex-direction:column;margin-top:24px}.access-card{padding:25px 18px}.mission-grid{grid-template-columns:1fr}.description{min-height:0}}
@media(max-width:380px){.talent-hero h1{font-size:27px}.card-bottom{flex-direction:column;align-items:flex-start}.demo-label{white-space:normal}.access-card .ie-btn{width:100%;white-space:normal}}
</style>
