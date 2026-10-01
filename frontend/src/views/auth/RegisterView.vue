<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import logo from "../../assets/images/logo-mark.png";
import { ACTOR_CATEGORY_GROUPS } from "../../data/actorCategories";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const heroPhoto = ref(null);

// Les 4 profils d'inscription (section 5 du CDC) — Professionnel, Entreprise
// et Talent sont tous les 3 des comptes `role="partner"` côté backend (aucun
// nouveau rôle applicatif) : c'est `profileType` seul qui détermine quel
// profil dédié est créé en plus du compte.
const PROFILES = [
  {
    value: "client",
    role: "client",
    icon: "fa-solid fa-champagne-glasses",
    title: "Client",
    description: "J'organise mon propre événement (mariage, anniversaire, séminaire...) : salles, prestataires, budget.",
  },
  {
    value: "professionnel",
    role: "partner",
    icon: "fa-solid fa-handshake",
    title: "Professionnel",
    description: "Je propose un service (décoration, DJ, traiteur...) : je publie mon profil dans le Marketplace InnovEvent.",
  },
  {
    value: "entreprise",
    role: "partner",
    icon: "fa-solid fa-building",
    title: "Entreprise",
    description: "Je représente une société (raison sociale, RCCM/NIU) proposant des services à la plateforme.",
  },
  {
    value: "talent",
    role: "partner",
    icon: "fa-solid fa-star",
    title: "Talent",
    description: "Je recherche une mission, un stage ou une opportunité dans l'événementiel.",
  },
  {
    value: "participant",
    role: "participant",
    icon: "fa-solid fa-user-group",
    title: "Participant",
    description: "Je participe à des événements ou formations : billets, invitations, suivi de mes inscriptions.",
  },
];

const CATEGORY_OPTIONS = ACTOR_CATEGORY_GROUPS.flatMap((group) => group.items);

// Permet un lien direct depuis la page d'accueil (ex : « Je suis professionnel »
// → ?profile=professionnel) sans repasser par la sélection manuelle du profil.
// `?role=` (ancien lien : client/participant/partner) reste accepté — un
// ancien `?role=partner` pointe vers « Professionnel », le plus courant des
// 3 profils partenaires.
const PROFILE_VALUES = PROFILES.map((p) => p.value);
let initialProfile = "participant";
if (PROFILE_VALUES.includes(route.params.profile)) {
  initialProfile = route.params.profile;
} else if (PROFILE_VALUES.includes(route.query.profile)) {
  initialProfile = route.query.profile;
} else if (route.query.role === "partner") {
  initialProfile = "professionnel";
} else if (route.query.role === "client") {
  initialProfile = "client";
}

// Code de parrainage : capturé depuis ?ref=CODE (même mécanisme que ?role=
// ci-dessus), avec une persistance de secours en localStorage pour survivre
// à une navigation multi-pages avant l'inscription (ex : lien partagé qui
// atterrit sur la page d'accueil avant que le visiteur clique sur « Créer un
// compte »).
const REFERRAL_STORAGE_KEY = "ie_referral_code";
let initialReferralCode = typeof route.query.ref === "string" ? route.query.ref.trim() : "";
if (initialReferralCode) {
  try {
    localStorage.setItem(REFERRAL_STORAGE_KEY, initialReferralCode);
  } catch {
    // stockage indisponible (navigation privée...) — le code reste utilisable
    // pour cette inscription immédiate, seule la persistance est perdue.
  }
} else {
  try {
    initialReferralCode = localStorage.getItem(REFERRAL_STORAGE_KEY) || "";
  } catch {
    initialReferralCode = "";
  }
}

const form = reactive({
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  phone: "",
  city: "",
  password: "",
  password_confirm: "",
  profile: initialProfile,
  referral_code: initialReferralCode,
  // Professionnel
  business_name: "", category: "", description: "", price_range: "",
  // Entreprise
  raison_sociale: "", activite: "", rccm: "", niu: "", adresse: "", representant: "",
  // Talent
  formation: "", competences: "", experience: "", disponibilite: "immediate", opportunity_type: "one_off",
});

const activeProfile = computed(() => PROFILES.find((p) => p.value === form.profile));
const selectedProfile = computed(() => PROFILE_VALUES.includes(route.params.profile) ? route.params.profile : PROFILE_VALUES.includes(route.query.profile) ? route.query.profile : null);
watch(selectedProfile, (profile) => { if (profile) form.profile = profile; });
function chooseProfile(profile) { router.push({ name: "register-profile", params: { profile }, query: route.query }); }

const errors = ref({});
const loading = ref(false);

onMounted(async () => {
  try {
    const { data } = await api.get("/public/landing-media/", { params: { category: "deco" } });
    heroPhoto.value = data.find((item) => item.photo)?.photo || null;
  } catch {
    heroPhoto.value = null;
  }
});

async function handleSubmit() {
  errors.value = {};
  loading.value = true;
  try {
    // `role` (accepté par le backend) et `profile_type` (détermine quel
    // profil dédié est créé en plus du compte) sont deux axes distincts —
    // dérivés ici de la seule carte choisie par l'utilisateur, pour ne pas
    // lui demander de comprendre cette distinction interne.
    const payload = {
      ...form,
      role: activeProfile.value.role,
      profile_type: ["professionnel", "entreprise", "talent"].includes(form.profile) ? form.profile : "none",
    };
    await auth.register(payload);
    try {
      localStorage.removeItem(REFERRAL_STORAGE_KEY);
    } catch {
      // pas grave si le stockage n'est pas disponible
    }
    await auth.login(form.username, form.password);
    // Préserve le contexte (ex : « Demander un devis pour ce pack ») au lieu
    // de toujours renvoyer vers un tableau de bord générique après inscription.
    router.push(route.query.next || (form.profile === "talent" ? { name: "talent-missions" } : { name: "dashboard" }));
  } catch (e) {
    errors.value = e?.response?.data?.errors || { detail: "Une erreur est survenue." };
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="ie-split">
    <!-- ======================= PANNEAU DE GAUCHE ======================= -->
    <aside class="ie-split-hero" :style="heroPhoto ? { backgroundImage: `url(${heroPhoto})` } : {}">
      <div class="ie-split-hero-scrim"></div>
      <div class="ie-split-hero-inner">
        <router-link :to="{ name: 'landing' }" class="ie-split-brand">
          <img :src="logo" alt="InnovEvent" class="ie-split-logo" />
          <span class="ie-split-brand-word">InnovEvent<span>Group</span></span>
        </router-link>

        <div class="ie-split-hero-body">
          <p class="ie-split-eyebrow">Créer un compte</p>
          <h1>Rejoignez-nous,<br />créez votre projet.</h1>
          <p class="ie-split-hero-lede">Un seul compte pour réserver vos salles, gérer vos prestataires, louer votre matériel et suivre votre formation.</p>

          <div class="ie-split-services">
            <div class="ie-split-service">
              <span class="ie-split-service-icon"><i class="fa-solid fa-calendar-week"></i></span>
              <div>
                <strong>Organisation d'événements</strong>
                <span>Salles, prestataires, billetterie et suivi budgétaire.</span>
              </div>
            </div>
            <div class="ie-split-service">
              <span class="ie-split-service-icon"><i class="fa-solid fa-sliders"></i></span>
              <div>
                <strong>Location de matériel</strong>
                <span>Mobilier, sonorisation, éclairage et chapiteaux.</span>
              </div>
            </div>
            <div class="ie-split-service">
              <span class="ie-split-service-icon"><i class="fa-solid fa-graduation-cap"></i></span>
              <div>
                <strong>InnovEvent Academy</strong>
                <span>Formations certifiantes aux métiers de l'événementiel.</span>
              </div>
            </div>
          </div>
        </div>

        <p class="ie-split-footer">© 2026 InnovEvent Group · Douala · Yaoundé · Bafoussam</p>
      </div>
    </aside>

    <!-- ======================= PANNEAU DE DROITE (FORMULAIRE) ======================= -->
    <main class="ie-split-form">
      <div class="ie-split-form-inner">
        <h2>{{ selectedProfile ? `Inscription ${activeProfile?.title || ""}` : "Choisissez votre profil" }}</h2>
        <p class="ie-split-lead">{{ selectedProfile ? "Complétez le formulaire pour créer votre compte InnovEvent." : "Sélectionnez votre profil pour ouvrir le formulaire d’inscription adapté." }}</p>

        <p v-if="form.referral_code" class="ie-referral-banner">
          <i class="fa-solid fa-user-plus"></i> Vous avez été invité·e avec le code <strong>{{ form.referral_code }}</strong>.
        </p>

        <div v-if="!selectedProfile" class="ie-role-picker">
          <button v-for="p in PROFILES" :key="p.value" type="button" class="ie-role-card" @click="chooseProfile(p.value)">
            <span class="ie-role-icon"><i :class="p.icon"></i></span><span class="ie-role-title">{{ p.title }}</span><span class="ie-role-desc">{{ p.description }}</span><span class="ie-role-continue">Continuer <i class="fa-solid fa-arrow-right"></i></span>
          </button>
        </div>

        <form v-else @submit.prevent="handleSubmit">
          <label class="ie-label">Je m'inscris en tant que</label>
          <div class="ie-selected-profile"><i :class="activeProfile?.icon"></i><strong>{{ activeProfile?.title }}</strong><button type="button" @click="router.push({ name: 'register' })">Changer</button></div>
          <div class="ie-form-row" style="margin-top: 18px;">
            <div>
              <label class="ie-label">Prénom</label>
              <input v-model="form.first_name" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Nom</label>
              <input v-model="form.last_name" class="ie-input" />
            </div>
          </div>

          <label class="ie-label" style="margin-top: 14px;">Identifiant</label>
          <input v-model="form.username" class="ie-input" required />
          <p v-if="errors.username" class="ie-auth-error">{{ errors.username[0] }}</p>

          <label class="ie-label" style="margin-top: 14px;">Email</label>
          <input v-model="form.email" type="email" class="ie-input" required />
          <p v-if="errors.email" class="ie-auth-error">{{ errors.email[0] }}</p>

          <div class="ie-form-row" style="margin-top: 14px;">
            <div>
              <label class="ie-label">Téléphone</label>
              <input v-model="form.phone" class="ie-input" />
            </div>
            <div>
              <label class="ie-label">Ville</label>
              <input v-model="form.city" class="ie-input" placeholder="Ex : Douala" />
            </div>
          </div>

          <!-- ======= Professionnel ======= -->
          <template v-if="form.profile === 'professionnel'">
            <div class="ie-profile-fields">
              <label class="ie-label">Nom de l'entreprise / activité <span class="ie-required">*</span></label>
              <input v-model="form.business_name" class="ie-input" placeholder="Ex : Marc Events" />
              <p v-if="errors.business_name" class="ie-auth-error">{{ errors.business_name[0] }}</p>

              <label class="ie-label" style="margin-top: 10px;">Catégorie</label>
              <select v-model="form.category" class="ie-input">
                <option value="">Non spécifiée</option>
                <option v-for="c in CATEGORY_OPTIONS" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>

              <label class="ie-label" style="margin-top: 10px;">Description</label>
              <textarea v-model="form.description" class="ie-input" rows="2" placeholder="Présentez votre activité en quelques mots..."></textarea>

              <label class="ie-label" style="margin-top: 10px;">Tarifs indicatifs</label>
              <select v-model="form.price_range" class="ie-input">
                <option value="">Non spécifié</option>
                <option value="€">€ — Accessible</option>
                <option value="€€">€€ — Intermédiaire</option>
                <option value="€€€">€€€ — Haut de gamme</option>
              </select>
              <p class="ie-field-hint">Photos, portfolio et services détaillés se complètent juste après, depuis votre tableau de bord.</p>
            </div>
          </template>

          <!-- ======= Entreprise ======= -->
          <template v-else-if="form.profile === 'entreprise'">
            <div class="ie-profile-fields">
              <label class="ie-label">Raison sociale <span class="ie-required">*</span></label>
              <input v-model="form.raison_sociale" class="ie-input" placeholder="Ex : ACME Events SARL" />
              <p v-if="errors.raison_sociale" class="ie-auth-error">{{ errors.raison_sociale[0] }}</p>

              <label class="ie-label" style="margin-top: 10px;">Activité</label>
              <input v-model="form.activite" class="ie-input" placeholder="Ex : Événementiel, traiteur..." />

              <div class="ie-form-row" style="margin-top: 10px;">
                <div>
                  <label class="ie-label">RCCM</label>
                  <input v-model="form.rccm" class="ie-input" />
                </div>
                <div>
                  <label class="ie-label">NIU</label>
                  <input v-model="form.niu" class="ie-input" />
                </div>
              </div>

              <label class="ie-label" style="margin-top: 10px;">Adresse</label>
              <input v-model="form.adresse" class="ie-input" />

              <label class="ie-label" style="margin-top: 10px;">Représentant légal</label>
              <input v-model="form.representant" class="ie-input" />
              <p class="ie-field-hint">Les documents justificatifs (RCCM, NIU...) se téléversent juste après, depuis votre tableau de bord.</p>
            </div>
          </template>

          <!-- ======= Talent ======= -->
          <template v-else-if="form.profile === 'talent'">
            <div class="ie-profile-fields">
              <label class="ie-label">Formation</label>
              <input v-model="form.formation" class="ie-input" placeholder="Ex : BTS Communication événementielle" />

              <label class="ie-label" style="margin-top: 10px;">Compétences</label>
              <input v-model="form.competences" class="ie-input" placeholder="Séparées par des virgules" />

              <label class="ie-label" style="margin-top: 10px;">Expérience</label>
              <textarea v-model="form.experience" class="ie-input" rows="2"></textarea>

              <div class="ie-form-row" style="margin-top: 10px;">
                <div>
                  <label class="ie-label">Disponibilité</label>
                  <select v-model="form.disponibilite" class="ie-input">
                    <option value="immediate">Immédiate</option>
                    <option value="within_month">Sous 1 mois</option>
                    <option value="to_define">À définir</option>
                  </select>
                </div>
                <div>
                  <label class="ie-label">Type d'opportunité</label>
                  <select v-model="form.opportunity_type" class="ie-input">
                    <option value="one_off">Mission ponctuelle</option>
                    <option value="fixed_term">CDD</option>
                    <option value="permanent">CDI</option>
                    <option value="internship">Stage</option>
                    <option value="freelance">Freelance</option>
                  </select>
                </div>
              </div>
              <p class="ie-field-hint">Photo et portfolio se complètent juste après, depuis votre tableau de bord.</p>
            </div>
          </template>

          <label class="ie-label" style="margin-top: 14px;">Mot de passe</label>
          <input v-model="form.password" type="password" class="ie-input" required />
          <p v-if="errors.password" class="ie-auth-error">{{ errors.password[0] }}</p>

          <label class="ie-label" style="margin-top: 14px;">Confirmation du mot de passe</label>
          <input v-model="form.password_confirm" type="password" class="ie-input" required />
          <p v-if="errors.password_confirm" class="ie-auth-error">{{ errors.password_confirm[0] }}</p>
          <p v-if="errors.detail" class="ie-auth-error">{{ errors.detail }}</p>

          <button class="ie-btn ie-btn-primary ie-split-submit" type="submit" :disabled="loading">
            {{ loading ? "Création en cours…" : "Créer mon compte" }} <i v-if="!loading" class="fa-solid fa-arrow-right"></i>
          </button>
        </form>

        <p class="ie-auth-footer">Déjà inscrit ? <router-link to="/login">Se connecter</router-link></p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.ie-split {
  min-height: 100vh; display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
.ie-split :is(h1, h2) { font-family: "Fraunces", Georgia, serif; text-wrap: balance; }

/* Panneau de gauche */
.ie-split-hero {
  position: relative; display: flex; background: #1c2530 center/cover no-repeat; color: #fff;
  padding: 52px 56px; overflow: hidden;
}
.ie-split-hero-scrim {
  position: absolute; inset: 0;
  background:
    radial-gradient(120% 90% at 100% 0%, rgba(192, 39, 45, 0.38), transparent 55%),
    linear-gradient(195deg, rgba(20, 27, 36, 0.97) 20%, rgba(30, 20, 26, 0.93) 75%, rgba(58, 16, 22, 0.9) 130%);
}
.ie-split-hero-inner { position: relative; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; animation: ie-rise 0.6s cubic-bezier(0.22, 0.68, 0, 1) both; }
.ie-split-brand { display: flex; align-items: center; gap: 11px; }
.ie-split-logo { height: 34px; width: auto; }
.ie-split-brand-word { font-size: 1.02rem; font-weight: 700; letter-spacing: -0.01em; }
.ie-split-brand-word span { color: var(--ie-red-soft); text-transform: uppercase; font-size: 0.6em; letter-spacing: 0.16em; margin-left: 4px; font-weight: 800; }

.ie-split-hero-body { max-width: 460px; margin: auto 0; padding: 48px 0; }
.ie-split-eyebrow {
  display: inline-flex; align-items: center; gap: 8px; font-size: 0.72rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.16em; color: rgba(255, 255, 255, 0.62); margin: 0 0 18px;
}
.ie-split-eyebrow::before { content: ""; width: 22px; height: 1.5px; background: var(--ie-red); display: inline-block; }
.ie-split-hero-body h1 { font-size: clamp(2rem, 3.4vw, 2.75rem); font-weight: 500; line-height: 1.14; letter-spacing: -0.01em; margin: 0 0 20px; color: #fff; }
.ie-split-hero-lede { color: rgba(255, 255, 255, 0.72); font-size: 1rem; line-height: 1.65; margin: 0 0 34px; }

.ie-split-services { display: flex; flex-direction: column; gap: 10px; }
.ie-split-service {
  display: flex; align-items: center; gap: 15px; background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 15px 17px;
  transition: background 0.25s ease, border-color 0.25s ease, transform 0.25s ease;
}
.ie-split-service:hover { background: rgba(255, 255, 255, 0.09); border-color: rgba(255, 255, 255, 0.2); transform: translateY(-1px); }
.ie-split-service-icon {
  width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
  background: linear-gradient(150deg, rgba(192, 39, 45, 0.35), rgba(192, 39, 45, 0.12));
  border: 1px solid rgba(192, 39, 45, 0.4); color: #f3b9bc;
  display: flex; align-items: center; justify-content: center; font-size: 15px;
}
.ie-split-service strong { display: block; font-size: 0.93rem; font-weight: 600; margin-bottom: 3px; letter-spacing: -0.005em; }
.ie-split-service span { display: block; font-size: 0.8rem; color: rgba(255, 255, 255, 0.62); line-height: 1.4; }

.ie-split-footer { font-size: 0.76rem; color: rgba(255, 255, 255, 0.4); letter-spacing: 0.01em; }

/* Panneau de droite */
.ie-split-form { display: flex; align-items: center; justify-content: center; padding: 40px 32px; background: var(--ie-white); overflow-y: auto; }
.ie-split-form-inner { width: 100%; max-width: 420px; animation: ie-rise 0.6s 0.08s cubic-bezier(0.22, 0.68, 0, 1) both; }
.ie-split-form-inner h2 { font-size: 1.85rem; font-weight: 500; color: var(--ie-ink); margin: 0 0 10px; letter-spacing: -0.01em; }
.ie-split-lead { color: var(--ie-muted); font-size: 0.93rem; line-height: 1.5; margin-bottom: 30px; }
.ie-form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.ie-role-picker { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 8px; }
.ie-role-card {
  text-align: left; background: #fff; border: 1.5px solid var(--ie-line); border-radius: 12px;
  padding: 14px; cursor: pointer; display: flex; flex-direction: column; gap: 6px;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}
.ie-role-card:hover { border-color: var(--ie-navy); transform: translateY(-1px); }
.ie-role-card.active { border-color: var(--ie-red); background: var(--ie-red-soft); }
.ie-role-icon {
  width: 34px; height: 34px; border-radius: 9px; background: var(--ie-navy-soft); color: var(--ie-navy);
  display: flex; align-items: center; justify-content: center; font-size: 14px; margin-bottom: 2px;
}
.ie-role-card.active .ie-role-icon { background: var(--ie-red); color: #fff; }
.ie-role-title { font-size: 0.92rem; font-weight: 700; color: var(--ie-ink); }
.ie-role-desc { font-size: 0.76rem; color: var(--ie-muted); line-height: 1.4; }
.ie-role-continue { margin-top: 8px; color: var(--ie-red); font-size: 0.8rem; font-weight: 700; }
.ie-selected-profile { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin: 8px 0 14px; background: var(--ie-navy-soft); border-radius: 10px; color: var(--ie-navy); }
.ie-selected-profile button { margin-left: auto; border: 0; background: transparent; color: var(--ie-red); font-weight: 700; cursor: pointer; }

@media (max-width: 480px) {
  .ie-role-picker { grid-template-columns: 1fr 1fr; }
}

.ie-profile-fields {
  margin-top: 16px; padding: 14px 16px; background: var(--ie-navy-soft, #f4f6f9); border-radius: 12px;
}
.ie-profile-fields select.ie-input { appearance: auto; }
.ie-required { color: var(--ie-red); }
.ie-field-hint { margin: 8px 0 0; font-size: 11.5px; color: var(--ie-muted); line-height: 1.4; }

.ie-input { border-radius: 10px; padding: 12px 14px; transition: border-color 0.2s ease, box-shadow 0.2s ease; }
.ie-input:focus { outline: none; border-color: var(--ie-navy); box-shadow: 0 0 0 3.5px rgba(57, 73, 91, 0.12); }

.ie-split-submit {
  width: 100%; margin-top: 24px; padding: 13px; border-radius: 10px; font-size: 0.95rem;
  display: flex; align-items: center; justify-content: center; gap: 9px;
  box-shadow: 0 10px 24px rgba(192, 39, 45, 0.22); transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.ie-split-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 30px rgba(192, 39, 45, 0.3); }
.ie-split-submit i { font-size: 13px; transition: transform 0.2s ease; }
.ie-split-submit:hover:not(:disabled) i { transform: translateX(3px); }

.ie-referral-banner {
  display: flex; align-items: center; gap: 8px; background: var(--ie-red-soft); color: var(--ie-red);
  border-radius: 10px; padding: 10px 14px; font-size: 0.86rem; margin: -12px 0 18px;
}
.ie-auth-error { color: var(--ie-red); font-size: 13px; margin-top: 6px; text-align: left; }
.ie-auth-footer { text-align: center; font-size: 0.86rem; color: var(--ie-muted); margin-top: 26px; }
.ie-auth-footer a { color: var(--ie-red); font-weight: 700; }

@keyframes ie-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .ie-split-hero-inner, .ie-split-form-inner { animation: none; } }

@media (max-width: 920px) {
  .ie-split { grid-template-columns: 1fr; }
  .ie-split-hero { padding: 32px 24px; min-height: 280px; }
  .ie-split-hero-body { padding: 24px 0; margin: 0; }
  .ie-split-hero-body h1 { font-size: 1.7rem; }
  .ie-split-hero-lede { margin-bottom: 20px; }
  .ie-split-services { display: none; }
  .ie-split-form { padding: 32px 24px 48px; }
}
</style>
