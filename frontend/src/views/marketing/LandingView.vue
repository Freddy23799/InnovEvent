<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import logoMark from "../../assets/images/logo-mark.png";
import InstallPwaButton from "../../components/InstallPwaButton.vue";
import LandingChatbot from "../../components/LandingChatbot.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();
function openLightbox(item) {
  if (item?.photo) lightbox.open(item.photo, item.label);
}

const isScrolled = ref(false);
const navOpen = ref(false);

function onScroll() {
  isScrolled.value = window.scrollY > 8;
}
function toggleNav() {
  navOpen.value = !navOpen.value;
}
function closeNav() {
  navOpen.value = false;
}

// Chiffres clés : compteur animé (0 → valeur cible) déclenché à l'entrée dans le viewport.
const STATS = [
  { key: "years", target: 8, suffix: " ans", icon: "fa-award", label: "d'expérience dans l'événementiel" },
  { key: "events", target: 450, suffix: "+", icon: "fa-champagne-glasses", label: "événements réalisés" },
  { key: "satisfaction", target: 97, suffix: "%", icon: "fa-heart", label: "de clients satisfaits" },
];
const statsDisplay = reactive({ years: 0, events: 0, satisfaction: 0 });
const statsBandEl = ref(null);
let statsStarted = false;

function animateStats() {
  if (statsStarted) return;
  statsStarted = true;
  const duration = 1400;
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    STATS.forEach((s) => { statsDisplay[s.key] = Math.round(s.target * eased); });
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// Qui sommes-nous : contenu institutionnel fixe (brochure InnovEvent & ACAMED), pas de photothèque.
const VALUES = [
  { icon: "fa-award", title: "Professionnalisme", text: "Respect strict des procédures, des délais et des engagements contractuels." },
  { icon: "fa-lightbulb", title: "Innovation", text: "Intégration de concepts créatifs, modernes et adaptés aux enjeux actuels." },
  { icon: "fa-diagram-project", title: "Rigueur organisationnelle", text: "Planification méthodique et gestion efficace des ressources." },
  { icon: "fa-scale-balanced", title: "Éthique et transparence", text: "Gouvernance responsable, respect des partenaires et des clients." },
  { icon: "fa-leaf", title: "Impact et durabilité", text: "Des événements porteurs de sens et de valeur durable." },
  { icon: "fa-heart", title: "Satisfaction client", text: "Une approche orientée résultats et amélioration continue." },
];
// Marketplace InnovEvent : les 4 sous-marketplaces premium de la plateforme —
// présentés ici pour que le visiteur en découvre l'existence avant même de
// créer un compte. Les liens pointent vers l'espace connecté (redirection
// automatique vers la connexion, puis retour direct sur le marketplace choisi).
const MARKETPLACE_ITEMS = [
  { type: "actors", icon: "fa-people-group", title: "Marketplace des acteurs", text: "DJ, traiteurs, photographes, wedding planners... des dizaines de métiers, tous vérifiés par notre équipe." },
  { type: "interior_design", icon: "fa-couch", title: "Décoration & design intérieur", text: "Décorateurs et designers d'intérieur, pour vos espaces événementiels comme au-delà." },
  { type: "venues", icon: "fa-building-columns", title: "Salles de réception", text: "Un catalogue de salles avec disponibilités en temps réel, à réserver directement." },
  { type: "sale", icon: "fa-bag-shopping", title: "Marketplace vente", text: "Objets, mobilier et équipements événementiels à acheter directement, sans abonnement." },
];
const MARKETPLACE_BENEFITS = [
  { icon: "fa-shield-halved", text: "Prestataires vérifiés par notre équipe avant publication" },
  { icon: "fa-file-signature", text: "Devis structurés, signés et exportables en PDF avec code QR" },
  { icon: "fa-user-shield", text: "Coordonnées privées — toute la négociation passe par la plateforme" },
  { icon: "fa-rotate-left", text: "Sans engagement, résiliable à tout moment" },
];

// Volet prestataires : le Marketplace ci-dessus est présenté côté client
// (« consulter ») — ce volet s'adresse à l'autre face du marketplace, les
// professionnels qui veulent y publier leur profil et recevoir des demandes.
const PROVIDER_BENEFITS = [
  { icon: "fa-eye", text: "Une visibilité directe auprès de clients déjà engagés dans leur projet" },
  { icon: "fa-file-invoice-dollar", text: "Des demandes de devis structurées — plus d'échanges informels à relancer" },
  { icon: "fa-lock", text: "Un paiement sécurisé sur la plateforme, commission prélevée automatiquement" },
  { icon: "fa-comments", text: "Une messagerie intégrée, sans jamais partager votre numéro personnel" },
];

const WHY_US = [
  { icon: "fa-stamp", text: "Une structure professionnelle et légalement organisée" },
  { icon: "fa-layer-group", text: "Une expertise combinée : événementiel + formation" },
  { icon: "fa-puzzle-piece", text: "Des offres flexibles, modulables et personnalisées" },
  { icon: "fa-handshake", text: "Un réseau de prestataires qualifiés et certifiés" },
  { icon: "fa-chart-line", text: "Une capacité d'intervention sur des projets de toute envergure" },
  { icon: "fa-route", text: "Un accompagnement avant, pendant et après chaque événement" },
];

// Clés locales conservées pour ne pas toucher au template ; elles pointent vers
// les vraies catégories de la photothèque gérée par l'administrateur (LandingMedia).
const CATEGORY_MAP = { deco: "deco", academy: "formation", portfolio: "realisation", equipment: "accessoire", packs: "pack" };

const sections = reactive({
  deco: [],
  academy: [],
  portfolio: [],
  equipment: [],
  packs: [],
});
const loading = reactive({ deco: true, academy: true, portfolio: true, equipment: true, packs: true });

async function loadSection(key) {
  loading[key] = true;
  try {
    const { data } = await api.get("/public/landing-media/", { params: { category: CATEGORY_MAP[key] } });
    sections[key] = data;
  } finally {
    loading[key] = false;
  }
}

// « Nos packs » : la description est saisie en une phrase par l'administrateur
// (ex. "Décoration soignée, mobilier premium, éclairage d'ambiance") ; on la
// découpe ici en points listés avec une étoile, plutôt qu'un seul paragraphe.
function packFeatures(caption) {
  return caption
    .split(",")
    .map((f) => f.trim().replace(/\.$/, ""))
    .filter(Boolean)
    .map((f) => f.charAt(0).toUpperCase() + f.slice(1));
}

// Hero : plusieurs photos (réalisations, puis décoration en complément) qui
// défilent automatiquement en fondu — évite une page d'accueil figée sur une
// seule image alors que l'administrateur en publie plusieurs.
const HERO_INTERVAL_MS = 6000;
const heroPhotos = ref([]);
const heroIndex = ref(0);
let heroTimer = null;

function startHeroRotation() {
  clearInterval(heroTimer);
  if (heroPhotos.value.length < 2) return;
  heroTimer = setInterval(() => {
    heroIndex.value = (heroIndex.value + 1) % heroPhotos.value.length;
  }, HERO_INTERVAL_MS);
}

async function loadAll() {
  await Promise.all(["deco", "academy", "portfolio", "equipment", "packs"].map(loadSection));
  const pool = [...sections.portfolio, ...sections.deco].map((p) => p.photo).filter(Boolean);
  heroPhotos.value = [...new Set(pool)].slice(0, 8);
  heroIndex.value = 0;
  startHeroRotation();
}

// Galerie « Nos réalisations » : toutes les photos publiques sont affichées
// par défaut. Les filtres sont seulement des outils facultatifs de navigation,
// jamais une condition qui peut masquer une réalisation importée.
const SCOPES = [
  { value: "tous", label: "Toutes les réalisations" },
  { value: "prive", label: "Événements privés" },
  { value: "public", label: "Événements grand public" },
];
const activeScope = ref("tous");
// Les photos historiques n'ont pas nécessairement de scope. Elles restent
// visibles dans « Toutes les réalisations » et ne sont jamais considérées
// comme privées au sens des permissions.
const scopedPortfolio = computed(() => sections.portfolio.filter(
  (item) => activeScope.value === "tous" || item.scope === activeScope.value
));

const galleryFilters = computed(() => {
  const tags = [...new Set(scopedPortfolio.value.map((item) => item.tag).filter(Boolean))];
  return [{ value: "tous", label: "Tous" }, ...tags.map((t) => ({ value: t, label: t }))];
});
const activeFilter = ref("tous");
function selectScope(scope) {
  activeScope.value = scope;
  activeFilter.value = "tous";
  activeTier.value = "tous";
}

const TIER_ORDER = { haut: 0, moyen: 1, petit: 2 };
const TIER_LABELS = { haut: "Haut de gamme", moyen: "Moyenne gamme", petit: "Petite gamme" };
const TIER_FILTERS = [
  { value: "tous", label: "Toutes gammes" },
  { value: "haut", label: "Haut de gamme" },
  { value: "moyen", label: "Moyenne gamme" },
  { value: "petit", label: "Petite gamme" },
];
const activeTier = ref("tous");
const filteredPortfolio = computed(() => {
  let base = activeFilter.value === "tous" ? scopedPortfolio.value : scopedPortfolio.value.filter((item) => item.tag === activeFilter.value);
  if (activeTier.value !== "tous") base = base.filter((item) => item.tier === activeTier.value);
  return [...base].sort((a, b) => (TIER_ORDER[a.tier] ?? 3) - (TIER_ORDER[b.tier] ?? 3) || a.order - b.order);
});

// Révélation au défilement
const revealEls = ref([]);
let observer = null;

function registerReveal(el) {
  if (el && !revealEls.value.includes(el)) revealEls.value.push(el);
}

// Observe tout élément [data-reveal]/[data-reveal-group] > * pas encore révélé.
// Nécessaire non seulement au montage, mais aussi après chaque changement de filtre
// de la galerie : Vue détruit/recrée les cartes filtrées, et les nouveaux nœuds DOM
// ne sont jamais observés sinon — ils restent alors bloqués invisibles (opacity: 0).
function revealNewElements() {
  const els = document.querySelectorAll("[data-reveal], [data-reveal-group] > *");
  if (observer) {
    els.forEach((el) => { if (!el.classList.contains("is-visible")) observer.observe(el); });
  } else {
    els.forEach((el) => el.classList.add("is-visible"));
  }
}

onMounted(async () => {
  window.addEventListener("scroll", onScroll, { passive: true });
  await loadAll();
  await new Promise((r) => setTimeout(r, 0)); // laisse le DOM se peindre après le fetch
  if ("IntersectionObserver" in window) {
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    revealNewElements();

    if (statsBandEl.value) {
      const statsObserver = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            animateStats();
            statsObserver.disconnect();
          }
        },
        { threshold: 0.3 }
      );
      statsObserver.observe(statsBandEl.value);
    }
  } else {
    revealNewElements();
    animateStats();
  }
});

// Le filtrage de la galerie (scope/type/gamme) recrée les cartes affichées :
// on ré-observe les nouvelles cartes pour qu'elles ne restent pas invisibles.
watch(filteredPortfolio, () => {
  nextTick(revealNewElements);
});

onUnmounted(() => {
  window.removeEventListener("scroll", onScroll);
  if (observer) observer.disconnect();
  clearInterval(heroTimer);
});
</script>

<template>
  <div class="ie-land">
    <!-- ======================= HEADER ======================= -->
    <header class="site-header" :class="{ 'is-scrolled': isScrolled }">
      <div class="nav-row">
        <a href="#top" class="logo" aria-label="InnovEvent Group — Accueil">
          <img :src="logoMark" alt="InnovEvent" class="logo-icon" />
          <span class="logo-word">InnovEvent<span class="grp">Group</span></span>
        </a>

        <div class="nav-scrim" :class="{ 'is-open': navOpen }" @click="closeNav"></div>
        <nav class="nav-links" :class="{ 'is-open': navOpen }" aria-label="Navigation principale">
          <a href="#top" @click="closeNav">Accueil</a>
          <a href="#events" @click="closeNav">Événements</a>
          <a href="#location" @click="closeNav">Location</a>
          <a href="#prestataires" @click="closeNav">Prestataires</a>
          <a href="#marketplace" @click="closeNav">Marketplace</a>
          <a href="#design" @click="closeNav">Design</a>
          <a href="#homedesign" @click="closeNav">Home</a>
          <a href="#academy" @click="closeNav">Formation</a>
          <a href="#travel" @click="closeNav">Travel &amp; Hospitality</a>
          <a href="#experiences" @click="closeNav">Experiences</a>
          <div class="nav-links-mobile-actions">
            <InstallPwaButton />
            <router-link :to="{ name: 'login' }" class="btn btn-ghost btn-sm">Connexion</router-link>
            <router-link :to="{ name: 'register', query: { profile: 'client' } }" class="btn btn-primary btn-sm">Je cherche un service</router-link>
            <router-link :to="{ name: 'register', query: { profile: 'professionnel' } }" class="btn btn-ghost btn-sm">Je suis professionnel</router-link>
          </div>
        </nav>

        <div class="nav-actions">
          <InstallPwaButton label="Télécharger" />
          <router-link :to="{ name: 'login' }" class="btn btn-ghost btn-sm">Connexion</router-link>
          <router-link :to="{ name: 'register', query: { profile: 'client' } }" class="btn btn-primary btn-sm">Je cherche un service</router-link>
          <button class="nav-toggle" aria-label="Ouvrir le menu" :aria-expanded="navOpen" @click="toggleNav">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M3 12h18M3 18h18" /></svg>
          </button>
        </div>
      </div>
    </header>

    <!-- ======================= HERO ======================= -->
    <section class="hero" id="top">
      <div class="hero-media">
        <div
          v-for="(photo, i) in heroPhotos" :key="photo"
          class="hero-ph" :class="{ 'is-active': i === heroIndex }"
          :style="{ backgroundImage: `url(${photo})` }"
        ></div>
        <div class="hero-scrim"></div>
      </div>
      <div class="container hero-inner">
        <h1 data-reveal>Votre projet, du premier <em>devis</em> au jour J.</h1>
        <p class="lede" data-reveal>InnovEvent réunit salles, décoration, traiteurs, formation et location de matériel dans un seul projet, coordonné du début à la fin.</p>
        <div class="hero-ctas" data-reveal>
          <router-link :to="{ name: 'register', query: { profile: 'talent' } }" class="btn btn-primary">Je cherche une mission</router-link>
          <router-link :to="{ name: 'register', query: { profile: 'client' } }" class="btn btn-ghost-light">Je cherche un service</router-link>
          <router-link :to="{ name: 'register', query: { profile: 'professionnel' } }" class="btn btn-ghost-light">Je suis professionnel</router-link>
        </div>
        <div class="hero-stats" data-reveal>
          <div><strong>7</strong><span>pôles dans un seul écosystème</span></div>
          <div><strong>4</strong><span>gammes, de l'accessible au sur-mesure</span></div>
          <div><strong>1</strong><span>espace pour suivre tout le projet</span></div>
        </div>
      </div>
    </section>

    <!-- ======================= VALUE STRIP ======================= -->
    <section class="value-strip">
      <div class="container value-grid">
        <div class="value-item" data-reveal>
          <span class="num">Un</span>
          <h3>Un chef d'orchestre</h3>
          <p>Vous décrivez votre besoin, nous coordonnons salle, décoration, traiteur et animation pour vous.</p>
        </div>
        <div class="value-item" data-reveal>
          <span class="num">Deux</span>
          <h3>Un budget maîtrisé</h3>
          <p>Réservez salles, prestataires et matériel avec des tarifs et des offres visibles avant de vous engager.</p>
        </div>
        <div class="value-item" data-reveal>
          <span class="num">Trois</span>
          <h3>Un suivi transparent</h3>
          <p>Réservations, billetterie et paiements centralisés dans votre espace client, à chaque étape.</p>
        </div>
      </div>
    </section>

    <!-- ======================= CHIFFRES CLÉS ======================= -->
    <section class="stats-band" ref="statsBandEl">
      <div class="container stats-grid" data-reveal-group>
        <div v-for="s in STATS" :key="s.key" class="stats-item">
          <span class="stats-icon"><i class="fa-solid" :class="s.icon"></i></span>
          <strong>{{ statsDisplay[s.key] }}{{ s.suffix }}</strong>
          <span class="stats-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- ======================= MARKETPLACE INNOVEVENT (inclut les anciens "Nos services") ======================= -->
    <section class="section-pad marketplace-section" id="marketplace">
      <div class="container">
        <div class="section-head center" data-reveal style="max-width: 720px;">
          <p class="kicker">Réservation en ligne</p>
          <h2 class="h-section">Le Marketplace InnovEvent</h2>
          <p class="lede" style="margin: 0 auto;">
            Consultez la disponibilité et réservez directement salle, décoration, DJ, traiteur ou équipement — un
            abonnement, un accès direct à un réseau de prestataires événementiels vérifiés, avec devis structuré et
            échanges confidentiels, sans jamais quitter la plateforme.
          </p>
        </div>

        <div class="services-grid" data-reveal-group>
          <router-link
            v-for="m in MARKETPLACE_ITEMS" :key="m.type"
            :to="{ name: 'premium-marketplace', query: { type: m.type } }"
            class="service-card"
          >
            <span class="service-card-icon"><i class="fa-solid" :class="m.icon"></i></span>
            <h3>{{ m.title }}</h3>
            <p>{{ m.text }}</p>
            <span class="service-card-cta">Découvrir <i class="fa-solid fa-arrow-right"></i></span>
          </router-link>
        </div>

        <div class="marketplace-benefits" data-reveal-group>
          <div v-for="b in MARKETPLACE_BENEFITS" :key="b.text" class="marketplace-benefit">
            <span class="marketplace-benefit-icon"><i class="fa-solid" :class="b.icon"></i></span>
            <p>{{ b.text }}</p>
          </div>
        </div>

        <div class="marketplace-cta" data-reveal>
          <router-link :to="{ name: 'register' }" class="btn btn-primary">Créer mon compte gratuitement</router-link>
          <router-link :to="{ name: 'premium-marketplace' }" class="text-link">Voir les formules d'abonnement <i class="fa-solid fa-arrow-right"></i></router-link>
        </div>
      </div>
    </section>

    <!-- ======================= VOUS ÊTES PRESTATAIRE ? ======================= -->
    <section class="section-pad provider-section" id="prestataires">
      <div class="container provider-wrap">
        <div class="provider-text" data-reveal>
          <p class="kicker">Vous êtes prestataire ?</p>
          <h2 class="h-section">Publiez votre profil, recevez des demandes</h2>
          <p class="lede">
            DJ, traiteur, décorateur, salle de réception, vente d'équipements... rejoignez le Marketplace InnovEvent
            et faites-vous découvrir par des clients qui ont déjà un projet d'événement en cours.
          </p>
          <ul class="provider-benefits">
            <li v-for="b in PROVIDER_BENEFITS" :key="b.text"><i class="fa-solid" :class="b.icon"></i>{{ b.text }}</li>
          </ul>
          <router-link :to="{ name: 'register', query: { profile: 'professionnel' } }" class="btn btn-primary">Devenir prestataire</router-link>
        </div>
        <div class="provider-card" data-reveal>
          <span class="provider-card-icon"><i class="fa-solid fa-handshake"></i></span>
          <h3>Compte Prestataire</h3>
          <p>Un espace dédié pour gérer votre profil, vos services, vos devis et vos réservations — depuis un seul tableau de bord.</p>
          <ul class="provider-card-list">
            <li><i class="fa-solid fa-check"></i>Profil professionnel vérifié</li>
            <li><i class="fa-solid fa-check"></i>Gestion des devis &amp; réservations</li>
            <li><i class="fa-solid fa-check"></i>Suivi des paiements</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- ======================= QUI SOMMES-NOUS ======================= -->
    <section class="section-pad about-section" id="apropos">
      <div class="container">
        <div class="section-head center" data-reveal style="max-width: 720px;">
          <p class="kicker">Qui sommes-nous</p>
          <h2 class="h-section">InnovEvent &amp; ACAMED, une double expertise</h2>
          <p class="lede" style="margin: 0 auto;">
            INNOVEVENT, en collaboration avec ACAMED (Académie des Métiers de l'Événementiel et du Design), conçoit,
            planifie et organise des événements à forte valeur ajoutée pour les entreprises, institutions,
            associations et particuliers — et forme les talents de demain aux métiers de l'événementiel et du design.
          </p>
        </div>

        <div class="about-vision" data-reveal>
          <span class="about-vision-kicker">Notre vision</span>
          <p>Devenir une référence nationale et régionale dans l'événementiel, le design et la formation professionnelle, en créant des expériences uniques, durables et porteuses de valeur économique, sociale et humaine.</p>
        </div>

        <div class="about-values-grid" data-reveal-group>
          <div v-for="v in VALUES" :key="v.title" class="about-value-card">
            <span class="about-value-icon"><i class="fa-solid" :class="v.icon"></i></span>
            <h4>{{ v.title }}</h4>
            <p>{{ v.text }}</p>
          </div>
        </div>

      </div>
    </section>

    <!-- ======================= POURQUOI NOUS CHOISIR ======================= -->
    <section class="section-pad about-why-section">
      <div class="container">
        <div class="section-head center" data-reveal style="max-width: 620px;">
          <p class="kicker" style="color: var(--slate-light);">Notre différence</p>
          <h2 class="h-section" style="color: #fff;">Pourquoi choisir InnovEvent &amp; ACAMED ?</h2>
        </div>
        <div class="about-why-grid" data-reveal-group>
          <div v-for="reason in WHY_US" :key="reason.text" class="about-why-card">
            <span class="about-why-icon"><i class="fa-solid" :class="reason.icon"></i></span>
            <p>{{ reason.text }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= PÔLES ======================= -->
    <section class="section-pad" id="events">
      <div class="container">
        <div class="poles-feature">
          <div
            class="poles-feature-photo"
            data-reveal
            :class="{ 'is-clickable': sections.portfolio[0]?.photo }"
            @click="openLightbox(sections.portfolio[0])"
          >
            <img v-if="sections.portfolio[0]?.photo" :src="sections.portfolio[0].photo" :alt="sections.portfolio[0].label" />
            <div v-else class="poles-feature-photo-empty"><i class="fa-solid fa-calendar-week"></i></div>
          </div>
          <div class="poles-feature-text" data-reveal>
            <p class="kicker">Pôle Events</p>
            <h3>Événementiel corporate &amp; institutionnel</h3>
            <p>Nous accompagnons les entreprises, institutions publiques et privées dans l'organisation de leurs événements professionnels.</p>

            <div class="poles-feature-sublists">
              <div>
                <p class="poles-feature-sublabel">Prestations</p>
                <ul class="poles-feature-list">
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Conférences &amp; séminaires</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Forums, colloques &amp; congrès</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Lancements de produits et services</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Team building &amp; événements internes</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Cérémonies officielles et protocolaires</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Salons professionnels &amp; foires</li>
                </ul>
              </div>
              <div>
                <p class="poles-feature-sublabel">Notre approche</p>
                <ul class="poles-feature-list">
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Analyse des objectifs</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Conception du concept événementiel</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Planification logistique complète</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Coordination des prestataires</li>
                  <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5" /></svg>Gestion opérationnelle et suivi post-événement</li>
                </ul>
              </div>
            </div>

            <router-link :to="{ name: 'register', query: { role: 'client' } }" class="btn btn-primary btn-sm">Demander un devis</router-link>
          </div>
        </div>

        <div class="section-head" data-reveal>
          <p class="kicker">Six autres pôles, un seul écosystème</p>
          <h2 class="h-section">Tout ce qu'il faut autour de l'événement</h2>
        </div>

        <div class="poles-grid" data-reveal-group>
          <div class="pole-card">
            <div class="pole-card-photo" v-if="sections.deco[0]?.photo"><img :src="sections.deco[0].photo" :alt="sections.deco[0].label" /></div>
            <div class="pole-card-icon" v-else><i class="fa-solid fa-palette"></i></div>
            <h4>Home &amp; Design</h4>
            <p>Décoration événementielle et aménagement d'espaces, du DJ au traiteur en passant par la scénographie.</p>
            <a href="#homedesign" class="text-link">Voir le pôle</a>
          </div>
          <div class="pole-card" id="academy-card">
            <div class="pole-card-photo" v-if="sections.academy[0]?.photo"><img :src="sections.academy[0].photo" :alt="sections.academy[0].label" /></div>
            <div class="pole-card-icon" v-else><i class="fa-solid fa-graduation-cap"></i></div>
            <h4>Academy</h4>
            <p>Formations en décoration, wedding planning et gestion événementielle, attestation à la clé.</p>
            <a href="#academy" class="text-link">Voir les formations</a>
          </div>
          <div class="pole-card" id="shop">
            <div class="pole-card-icon"><i class="fa-solid fa-bag-shopping"></i></div>
            <h4>Shop</h4>
            <p>Objets déco, mobilier et équipements événementiels à commander en ligne.</p>
            <a href="#shop" class="text-link">Voir la boutique</a>
          </div>
          <div class="pole-card" id="travel">
            <div class="pole-card-icon"><i class="fa-solid fa-plane"></i></div>
            <h4>Travel</h4>
            <p>Circuits, excursions et expériences touristiques à associer à votre événement.</p>
            <a href="#travel" class="text-link">Voir les expériences</a>
          </div>
          <div class="pole-card" id="stay">
            <div class="pole-card-icon"><i class="fa-solid fa-bed"></i></div>
            <h4>Stay</h4>
            <p>Hébergements pour vos invités, avant, pendant et après l'événement.</p>
            <a href="#stay" class="text-link">Voir les hébergements</a>
          </div>
          <div class="pole-card" id="experiences">
            <div class="pole-card-icon"><i class="fa-solid fa-champagne-glasses"></i></div>
            <h4>Experiences</h4>
            <p>Moments immersifs et activités sur-mesure à intégrer à votre événement — bientôt disponible.</p>
            <a href="#experiences" class="text-link">En savoir plus</a>
          </div>
          <div class="pole-card" id="accessoire-card">
            <div class="pole-card-photo" v-if="sections.equipment[0]?.photo"><img :src="sections.equipment[0].photo" :alt="sections.equipment[0].label" /></div>
            <div class="pole-card-icon" v-else><i class="fa-solid fa-sliders"></i></div>
            <h4>Location de matériel</h4>
            <p>Chaises, chapiteaux, sonorisation et mobilier disponibles à la location.</p>
            <a href="#location" class="text-link">Voir le matériel</a>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= DÉCORATION (dossier deco) ======================= -->
    <section class="section-pad showcase" id="homedesign">
      <div class="container">
        <div class="showcase-head" data-reveal>
          <div class="section-head" style="margin-bottom: 0;">
            <p class="kicker" id="design">Home &amp; Design</p>
            <h2 class="h-section">Décoration &amp; scénographie</h2>
            <p class="lede">Une sélection de réalisations gérée depuis l'administration : chaque photo est ajoutée, remplacée ou retirée par l'équipe InnovEvent.</p>
          </div>
          <router-link :to="{ name: 'register', query: { role: 'client' } }" class="btn btn-ghost">Demander un devis déco</router-link>
        </div>
        <div class="media-grid" data-reveal-group>
          <template v-if="loading.deco">
            <div v-for="i in 4" :key="i" class="media-card media-skeleton"></div>
          </template>
          <template v-else-if="sections.deco.length">
            <div v-for="item in sections.deco" :key="item.id" class="media-card is-clickable" @click="openLightbox(item)">
              <div class="media-photo">
                <img v-if="item.photo" :src="item.photo" :alt="item.label" />
                <i v-else class="fa-solid fa-palette"></i>
                <span v-if="item.photo" class="media-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></span>
              </div>
              <span class="media-label">{{ item.label }}</span>
            </div>
          </template>
          <p v-else class="media-empty">Catalogue décoration bientôt en ligne.</p>
        </div>
      </div>
    </section>

    <!-- ======================= ACADEMY (dossier formation) ======================= -->
    <section class="section-pad" id="academy" style="background: var(--cream);">
      <div class="container">
        <div class="section-head" data-reveal>
          <p class="kicker">InnovEvent Academy</p>
          <h2 class="h-section">Se former aux métiers de l'événementiel</h2>
          <p class="lede">Sessions en présentiel, inscriptions et paiement en tranches en ligne, attestation délivrée en fin de formation.</p>
        </div>
        <div class="academy-grid" data-reveal-group>
          <template v-if="loading.academy">
            <div v-for="i in 4" :key="i" class="academy-card media-skeleton" style="height: 220px;"></div>
          </template>
          <template v-else-if="sections.academy.length">
            <div v-for="item in sections.academy" :key="item.id" class="academy-card">
              <div class="media-photo is-clickable" @click="openLightbox(item)">
                <img v-if="item.photo" :src="item.photo" :alt="item.label" />
                <i v-else class="fa-solid fa-graduation-cap"></i>
                <span v-if="item.photo" class="media-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></span>
              </div>
              <h4>{{ item.label }}</h4>
              <span>{{ item.caption }}</span>
            </div>
          </template>
          <p v-else class="media-empty">Formations bientôt en ligne.</p>
        </div>
      </div>
    </section>

    <!-- ======================= GALERIE / RÉALISATIONS (dossier gal) ======================= -->
    <section class="section-pad gallery" id="galerie">
      <div class="container">
        <div class="section-head center" data-reveal>
          <p class="kicker">Portfolio</p>
          <h2 class="h-section">Nos réalisations</h2>
          <p class="lede" style="margin: 0 auto;">Un aperçu de ce que nous avons déjà réalisé — sans prix, juste de quoi vous inspirer. Les tarifs sont détaillés dans nos packs.</p>
        </div>

        <div class="scope-row" data-reveal>
          <button
            v-for="s in SCOPES"
            :key="s.value"
            class="scope-btn"
            :class="{ 'is-active': activeScope === s.value }"
            @click="selectScope(s.value)"
          >{{ s.label }}</button>
        </div>

        <div class="filter-row" data-reveal>
          <button
            v-for="f in galleryFilters"
            :key="f.value"
            class="filter-btn"
            :class="{ 'is-active': activeFilter === f.value }"
            @click="activeFilter = f.value"
          >{{ f.label }}</button>
        </div>

        <div class="filter-row filter-row-tier" data-reveal>
          <button
            v-for="t in TIER_FILTERS"
            :key="t.value"
            class="filter-btn filter-btn-tier"
            :class="{ 'is-active': activeTier === t.value }"
            @click="activeTier = t.value"
          >{{ t.label }}</button>
        </div>

        <div class="gal-grid" data-reveal-group>
          <template v-if="loading.portfolio">
            <div v-for="i in 4" :key="i" class="media-skeleton" style="aspect-ratio: 4/3; border-radius: 10px;"></div>
          </template>
          <template v-else-if="filteredPortfolio.length">
            <div v-for="item in filteredPortfolio" :key="item.id" class="gal-item is-clickable" @click="openLightbox(item)">
              <div class="media-photo">
                <img v-if="item.photo" :src="item.photo" :alt="item.label" />
                <i v-else class="fa-solid fa-images"></i>
                <span v-if="item.photo" class="media-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></span>
                <span v-if="item.tier" class="gal-tier" :class="`is-${item.tier}`">{{ TIER_LABELS[item.tier] }}</span>
              </div>
            </div>
          </template>
          <p v-else class="media-empty">Aucune réalisation dans cette catégorie pour le moment.</p>
        </div>
      </div>
    </section>

    <!-- ======================= NOS PACKS (dossier pack, tarifs) ======================= -->
    <section class="section-pad" id="packs">
      <div class="container">
        <div class="section-head center" data-reveal>
          <p class="kicker">Nos packs</p>
          <h2 class="h-section">Des formules claires, pour chaque budget</h2>
          <p class="lede" style="margin: 0 auto;">Chaque pack précise le tarif et ce qui est inclus — géré et mis à jour par l'administration.</p>
        </div>
        <div class="pack-grid" data-reveal-group>
          <template v-if="loading.packs">
            <div v-for="i in 3" :key="i" class="pack-card media-skeleton" style="height: 340px;"></div>
          </template>
          <template v-else-if="sections.packs.length">
            <div v-for="item in sections.packs" :key="item.id" class="pack-card">
              <div class="media-photo is-clickable" @click="openLightbox(item)">
                <img v-if="item.photo" :src="item.photo" :alt="item.label" />
                <i v-else class="fa-solid fa-box-open"></i>
                <span v-if="item.photo" class="media-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></span>
              </div>
              <div class="pack-card-body">
                <h4>{{ item.label }}</h4>
                <ul v-if="item.caption" class="pack-features">
                  <li v-for="(feature, i) in packFeatures(item.caption)" :key="i">
                    <i class="fa-solid fa-star"></i>{{ feature }}
                  </li>
                </ul>
                <div class="pack-card-foot">
                  <strong v-if="item.budget_label" class="pack-price">{{ item.budget_label }}</strong>
                  <router-link :to="{ name: 'register', query: { role: 'client' } }" class="text-link">Demander un devis</router-link>
                </div>
                <router-link :to="{ name: 'public-pack-detail', params: { packId: item.id } }" class="pack-discover-btn">
                  <i class="fa-solid fa-magnifying-glass"></i> Découvrir le pack
                </router-link>
              </div>
            </div>
          </template>
          <p v-else class="media-empty">Nos packs arrivent bientôt.</p>
        </div>
      </div>
    </section>

    <!-- ======================= LOCATION MATÉRIEL (dossier accessoire) ======================= -->
    <section class="section-pad" id="location">
      <div class="container">
        <div class="section-head" data-reveal>
          <p class="kicker">Location de matériel</p>
          <h2 class="h-section">Location de matériel événementiel</h2>
          <p class="lede">Disponibilité vérifiée en temps réel au moment de la réservation, chaque référence est administrée indépendamment.</p>
        </div>
        <div class="equip-grid" data-reveal-group>
          <template v-if="loading.equipment">
            <div v-for="i in 3" :key="i" class="equip-card media-skeleton" style="height: 240px;"></div>
          </template>
          <template v-else-if="sections.equipment.length">
            <div v-for="item in sections.equipment" :key="item.id" class="equip-card">
              <div class="media-photo is-clickable" @click="openLightbox(item)">
                <img v-if="item.photo" :src="item.photo" :alt="item.label" />
                <i v-else class="fa-solid fa-sliders"></i>
                <span v-if="item.photo" class="media-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></span>
              </div>
              <div class="equip-card-body">
                <h4>{{ item.label }}</h4>
                <div class="equip-stars"><i class="fa-solid fa-star" v-for="n in 5" :key="n"></i></div>
                <p>{{ item.caption }}</p>
                <div class="equip-card-foot">
                  <span v-if="item.price_label" class="equip-price">{{ item.price_label }}</span>
                  <router-link :to="{ name: 'register' }" class="equip-reserve-btn">
                    Réserver <i class="fa-solid fa-arrow-right"></i>
                  </router-link>
                </div>
              </div>
            </div>
          </template>
          <p v-else class="media-empty">Catalogue matériel bientôt en ligne.</p>
        </div>
      </div>
    </section>

    <!-- ======================= MON PROJET ======================= -->
    <section class="section-pad project-section">
      <div class="container project-wrap">
        <div class="project-text" data-reveal>
          <p class="kicker">Le concept « projet client »</p>
          <h2>Construisez votre projet, étape par étape</h2>
          <p>Créez votre compte, renseignez la date, le lieu, le nombre d'invités et le budget prévisionnel, puis ajoutez les prestations une à une. Le coût estimatif se met à jour automatiquement.</p>
          <router-link :to="{ name: 'register' }" class="btn btn-primary">Créer mon projet</router-link>
        </div>
        <div class="project-card" data-reveal>
          <div class="project-card-head">
            <div><span>Projet client</span><strong>Mon mariage</strong></div>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" stroke-width="1.6"><circle cx="12" cy="12" r="9" /><path d="M12 8v4l3 2" /></svg>
          </div>
          <div class="project-meta">
            <div><span>Date</span><strong>20 décembre</strong></div>
            <div><span>Lieu</span><strong>Yaoundé</strong></div>
            <div><span>Invités</span><strong>250 personnes</strong></div>
            <div><span>Budget prévisionnel</span><strong>4 000 000 FCFA</strong></div>
          </div>
          <ul class="project-list">
            <li><span class="tag"><i class="fa-solid fa-building-columns"></i>Salle de réception</span><span class="amount">900 000 FCFA</span></li>
            <li><span class="tag"><i class="fa-solid fa-palette"></i>Décoration &amp; scénographie</span><span class="amount">650 000 FCFA</span></li>
            <li><span class="tag"><i class="fa-solid fa-utensils"></i>Traiteur — 250 couverts</span><span class="amount">1 500 000 FCFA</span></li>
            <li><span class="tag"><i class="fa-solid fa-music"></i>DJ &amp; animation</span><span class="amount">350 000 FCFA</span></li>
          </ul>
          <div class="project-total">
            <span>Coût estimatif du projet</span>
            <strong>3 400 000 FCFA</strong>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= GAMMES ======================= -->
    <section class="section-pad gammes">
      <div class="container">
        <div class="section-head center" data-reveal style="max-width: 560px;">
          <p class="kicker" style="color: var(--slate-light);">Quel que soit votre budget</p>
          <h2 class="h-section" style="color: #fff;">Quatre gammes, un même niveau d'exigence</h2>
        </div>
        <div class="gammes-grid" data-reveal-group>
          <div class="gamme-item">
            <h4>Accessible</h4>
            <p>L'essentiel pour organiser un événement réussi, sans dépasser un budget serré.</p>
          </div>
          <div class="gamme-item">
            <h4>Standard / Confort</h4>
            <p>Un bon équilibre entre qualité de prestation et maîtrise du budget.</p>
          </div>
          <div class="gamme-item">
            <h4>Premium</h4>
            <p>Des prestataires et un niveau de finition choisis pour les événements exigeants.</p>
          </div>
          <div class="gamme-item">
            <h4>Luxe / Sur mesure</h4>
            <p>Une conception entièrement personnalisée, sans compromis, pilotée de bout en bout.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= TÉMOIGNAGES ======================= -->
    <section class="section-pad testimonials">
      <div class="container">
        <div class="section-head center" data-reveal>
          <p class="kicker">Ils nous ont fait confiance</p>
          <h2 class="h-section">Ce que disent nos clients</h2>
        </div>
        <div class="testimonials-grid" data-reveal-group>
          <div class="testimonial-card">
            <div class="testimonial-stars"><i class="fa-solid fa-star" v-for="n in 5" :key="n"></i></div>
            <p class="testimonial-quote">« Une équipe à l'écoute du début à la fin. La décoration était exactement ce qu'on avait imaginé, et le suivi du budget nous a évité bien des surprises. »</p>
            <div class="testimonial-author">
              <span class="testimonial-name">Sandrine K.</span>
              <span class="testimonial-meta">Mariage — Yaoundé</span>
            </div>
          </div>
          <div class="testimonial-card">
            <div class="testimonial-stars"><i class="fa-solid fa-star" v-for="n in 5" :key="n"></i></div>
            <p class="testimonial-quote">« Nous avons confié l'organisation complète de notre séminaire à InnovEvent : salle, traiteur, sonorisation. Tout était prêt et coordonné, on a pu se concentrer sur nos invités. »</p>
            <div class="testimonial-author">
              <span class="testimonial-name">Cabinet Fotso &amp; Associés</span>
              <span class="testimonial-meta">Séminaire d'entreprise</span>
            </div>
          </div>
          <div class="testimonial-card">
            <div class="testimonial-stars"><i class="fa-solid fa-star" v-for="n in 5" :key="n"></i></div>
            <p class="testimonial-quote">« Le matériel loué était impeccable et livré à l'heure. La billetterie en ligne nous a aussi fait gagner un temps précieux pour l'anniversaire de notre fille. »</p>
            <div class="testimonial-author">
              <span class="testimonial-name">Arnaud &amp; Judith M.</span>
              <span class="testimonial-meta">Anniversaire — Douala</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= CONTACT / CARTE ======================= -->
    <section class="section-pad" id="contact">
      <div class="container">
        <div class="contact-wrap" data-reveal>
          <div class="contact-info">
            <h2>Nous trouver</h2>
            <div class="contact-row">
              <i class="fa-solid fa-location-dot"></i>
              <div><span>Adresse</span><strong>Rue Germaine Ahidjo, Yaoundé, Cameroun</strong></div>
            </div>
            <div class="contact-row">
              <i class="fa-solid fa-phone"></i>
              <div><span>Téléphone / WhatsApp</span><strong>+237 6 73 00 39 93</strong></div>
            </div>
            <div class="contact-row">
              <i class="fa-solid fa-clock"></i>
              <div><span>Disponibilité</span><strong>Lundi — samedi, 8h — 19h</strong></div>
            </div>

            <div>
              <span style="display: block; font-size: 0.76rem; color: var(--muted); margin-bottom: 10px;">Suivez InnovEvent</span>
              <div class="social-row">
                <a class="social-btn fb" href="https://www.facebook.com/share/1HCRvXkGCR/?mibextid=wwXIfr" target="_blank" rel="noopener" aria-label="Facebook InnovEvent"><i class="fa-brands fa-facebook-f"></i></a>
                <a class="social-btn tt" href="https://www.tiktok.com/@innovevent237?_r=1&_t=ZS-99WuwI1sCcH" target="_blank" rel="noopener" aria-label="TikTok InnovEvent"><i class="fa-brands fa-tiktok"></i></a>
                <a class="social-btn wa" href="https://wa.me/237673003993" target="_blank" rel="noopener" aria-label="Écrire sur WhatsApp"><i class="fa-brands fa-whatsapp"></i></a>
              </div>
            </div>
          </div>
          <div class="map-embed">
            <iframe
              title="Localisation InnovEvent — Rue Germaine Ahidjo, Yaoundé"
              src="https://www.google.com/maps?q=Rue+Germaine+Ahidjo,+Yaound%C3%A9,+Cameroun&output=embed"
              loading="lazy"
              referrerpolicy="no-referrer-when-downgrade"
            ></iframe>
          </div>
        </div>
      </div>
    </section>

    <!-- ======================= CTA BANNER ======================= -->
    <section class="cta-banner" id="projet">
      <h2 data-reveal>Prêt à donner vie à votre projet ?</h2>
      <p data-reveal>Créez votre compte gratuitement et recevez vos premiers devis en quelques heures.</p>
      <div class="hero-ctas" data-reveal>
        <router-link :to="{ name: 'register' }" class="btn" style="background: #fff; color: var(--wine);">Créer mon projet</router-link>
        <a href="https://wa.me/237673003993" target="_blank" rel="noopener" class="btn btn-ghost-light">Nous écrire sur WhatsApp</a>
      </div>
    </section>

    <!-- ======================= FOOTER ======================= -->
    <footer>
      <div class="container footer-top">
        <div class="footer-brand">
          <span class="logo" style="display: inline-flex;">
            <img :src="logoMark" alt="InnovEvent" class="logo-icon" />
            <span class="logo-word">InnovEvent<span class="grp">Group</span></span>
          </span>
          <p>Events · Home · Design · Academy · Shop · Travel · Stay — un seul écosystème pour organiser, décorer et vivre vos projets.</p>
          <div class="footer-social">
            <a class="social-btn fb" href="https://www.facebook.com/share/1HCRvXkGCR/?mibextid=wwXIfr" target="_blank" rel="noopener" aria-label="Facebook"><i class="fa-brands fa-facebook-f"></i></a>
            <a class="social-btn tt" href="https://www.tiktok.com/@innovevent237?_r=1&_t=ZS-99WuwI1sCcH" target="_blank" rel="noopener" aria-label="TikTok"><i class="fa-brands fa-tiktok"></i></a>
            <a class="social-btn wa" href="https://wa.me/237673003993" target="_blank" rel="noopener" aria-label="WhatsApp"><i class="fa-brands fa-whatsapp"></i></a>
          </div>
        </div>
        <div>
          <h5>Les 7 pôles</h5>
          <ul>
            <li><a href="#events">Events</a></li>
            <li><a href="#homedesign">Home &amp; Design</a></li>
            <li><a href="#academy">Academy</a></li>
            <li><a href="#shop">Shop</a></li>
            <li><a href="#travel">Travel &amp; Hospitality</a></li>
            <li><a href="#stay">Stay</a></li>
            <li><a href="#experiences">Experiences</a></li>
            <li><a href="#location">Location de matériel</a></li>
          </ul>
        </div>
        <div>
          <h5>Ressources</h5>
          <ul>
            <li><a href="#prestataires">Prestataires</a></li>
            <li><a href="#galerie">Réalisations</a></li>
            <li><a href="#academy">Formations</a></li>
            <li><a href="#contact">Devenir partenaire</a></li>
            <li><a href="#contact">FAQ</a></li>
          </ul>
        </div>
        <div>
          <h5>Contact</h5>
          <ul>
            <li><a href="#contact">Rue Germaine Ahidjo, Yaoundé</a></li>
            <li><a href="tel:+237673003993">+237 6 73 00 39 93</a></li>
            <li><a href="https://wa.me/237673003993" target="_blank" rel="noopener">Écrire sur WhatsApp</a></li>
          </ul>
        </div>
      </div>
      <div class="container footer-bottom">
        <span>© 2026 InnovEvent Group. Tous droits réservés.</span>
      </div>
    </footer>

    <!-- Bouton "Créer mon projet" flottant : mêmes comportement/position que le bouton WhatsApp -->
    <Transition name="float-in">
      <router-link v-if="isScrolled" :to="{ name: 'register' }" class="project-float" aria-label="Créer mon projet">
        <i class="fa-solid fa-arrow-right"></i>
        <span>Créer mon projet</span>
      </router-link>
    </Transition>

    <!-- Bouton WhatsApp flottant -->
    <a class="wa-float" href="https://wa.me/237673003993" target="_blank" rel="noopener" aria-label="Discuter sur WhatsApp">
      <i class="fa-brands fa-whatsapp"></i>
    </a>

    <!-- Assistant / chatbot InnovEvent (répond aux questions sur l'entreprise et ses services) -->
    <LandingChatbot />
  </div>
</template>

<style scoped>
.ie-land {
  --wine: #c0272d;
  --wine-dark: #8a0e16;
  --wine-tint: #f6e2e3;
  --slate: #39495b;
  --slate-light: #9db1c1;
  --ink: #1e2a33;
  --ink-soft: #4c5c68;
  --muted: #85939b;
  --cream: #fafaf9;
  --paper: #ffffff;
  --stone: #e4e7e9;
  --stone-line: #d7dbde;
  --whatsapp: #25a75b;
  --display: "Fraunces", Georgia, serif;
  --body: "Work Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --gutter: clamp(20px, 5vw, 64px);
  --ease: cubic-bezier(0.22, 0.68, 0, 1);

  font-family: var(--body);
  color: var(--ink);
  background: var(--cream);
  line-height: 1.55;
}
.ie-land img { max-width: 100%; display: block; }
.ie-land a { color: inherit; text-decoration: none; }
.ie-land ul { margin: 0; padding: 0; list-style: none; }
.ie-land h1, .ie-land h2, .ie-land h3, .ie-land h4 { font-family: var(--display); font-weight: 600; margin: 0; color: var(--ink); }
.ie-land p { margin: 0; }
.ie-land .container { max-width: 1200px; margin: 0 auto; padding: 0 var(--gutter); }
.ie-land section { position: relative; }
.section-pad { padding: 88px 0; }
@media (max-width: 720px) { .section-pad { padding: 56px 0; } }

.kicker { font-weight: 600; font-size: 0.82rem; color: var(--wine); margin: 0 0 14px; }
.h-section { font-size: clamp(1.7rem, 3vw, 2.5rem); font-weight: 500; letter-spacing: -0.01em; }
.lede { color: var(--ink-soft); font-size: 1.05rem; max-width: 56ch; }
.section-head { max-width: 640px; margin-bottom: 40px; }
.section-head.center { margin-left: auto; margin-right: auto; text-align: center; }

.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 13px 26px; border-radius: 2px; font-size: 0.95rem; font-weight: 600;
  border: 1px solid transparent; transition: background 0.25s var(--ease), color 0.25s var(--ease), border-color 0.25s var(--ease), transform 0.25s var(--ease);
  white-space: nowrap; cursor: pointer;
}
.btn-primary { background: var(--wine); color: #fff; }
.btn-primary:hover { background: var(--wine-dark); transform: translateY(-1px); }
.btn-ghost { background: transparent; color: var(--ink); border-color: rgba(30, 42, 51, 0.28); }
.btn-ghost:hover { border-color: var(--ink); }
.btn-ghost-light { background: transparent; color: #fff; border-color: rgba(255, 255, 255, 0.55); }
.btn-ghost-light:hover { border-color: #fff; background: rgba(255, 255, 255, 0.08); }
.btn-sm { padding: 9px 18px; font-size: 0.85rem; }
.text-link { font-weight: 600; color: var(--wine); border-bottom: 1px solid rgba(192, 39, 45, 0.35); padding-bottom: 2px; }
.text-link:hover { border-color: var(--wine); }

/* Header */
.site-header {
  position: sticky; top: 0; z-index: 80;
  background: rgba(251, 247, 240, 0.92); backdrop-filter: blur(8px);
  border-bottom: 1px solid transparent;
  transition: border-color 0.3s var(--ease), box-shadow 0.3s var(--ease);
}
.site-header.is-scrolled { border-color: var(--stone-line); box-shadow: 0 6px 24px rgba(30, 42, 51, 0.06); }
.nav-row {
  /* Trois zones équilibrées : logo à gauche, navigation réellement centrée,
     actions à droite. Les dix liens ne sont plus comprimés dans les 1200px
     réservés au contenu éditorial de la page. */
  display: grid; grid-template-columns: minmax(190px, 1fr) auto minmax(330px, 1fr);
  align-items: center; gap: clamp(16px, 2vw, 32px); padding: 16px var(--gutter);
  max-width: 1680px; margin: 0 auto;
}
.logo { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.logo-icon { height: 34px; width: auto; display: block; }
.logo-word { font-family: var(--display); font-size: 1.28rem; font-weight: 600; letter-spacing: -0.01em; color: var(--ink); }
.logo-word .grp { color: var(--wine); text-transform: uppercase; font-size: 0.62em; letter-spacing: 0.14em; vertical-align: middle; margin-left: 4px; font-weight: 700; }
.footer-brand .logo-word { color: #fff; }

.nav-links { display: flex; align-items: center; justify-self: center; gap: clamp(12px, 1.05vw, 22px); white-space: nowrap; }
.nav-links > a { font-size: clamp(0.78rem, 0.78vw, 0.92rem); font-weight: 500; color: var(--ink-soft); padding: 4px 0; transition: color 0.2s; }
.nav-links > a:hover { color: var(--wine); }
.nav-actions { display: flex; align-items: center; justify-self: end; gap: 12px; white-space: nowrap; }
.nav-toggle { display: none; width: 38px; height: 38px; border: 1px solid var(--stone-line); background: var(--paper); border-radius: 4px; align-items: center; justify-content: center; }
.nav-toggle svg { width: 18px; height: 18px; }
.nav-links-mobile-actions { display: none; }
.nav-scrim { display: none; }

/* Sous 1650px, l'ensemble logo + dix liens + actions serait trop dense : le
   panneau de navigation offre une lecture plus nette qu'une barre comprimée. */
@media (max-width: 1650px) {
  .nav-row { display: flex; justify-content: space-between; gap: 24px; max-width: 1200px; }
  .nav-links {
    position: fixed; inset: 0 0 0 auto; width: min(320px, 86vw); height: 100vh; height: 100dvh;
    background: var(--paper); flex-direction: column; align-items: flex-start; gap: 2px;
    padding: 96px 28px 28px; clip-path: inset(0 0 0 100%); visibility: hidden;
    transition: clip-path 0.35s var(--ease), visibility 0s linear 0.35s;
    box-shadow: -16px 0 40px rgba(0, 0, 0, 0.12); z-index: 75;
  }
  .nav-links.is-open { clip-path: inset(0); visibility: visible; transition-delay: 0s; }
  .nav-links > a { width: 100%; padding: 12px 0; border-bottom: 1px solid var(--stone); font-size: 1.02rem; }
  .nav-actions .btn-ghost, .nav-actions .btn-primary { display: none; }
  .nav-toggle { display: inline-flex; }
  .nav-links-mobile-actions { display: flex; flex-direction: column; gap: 10px; width: 100%; margin-top: 22px; }
  .nav-links-mobile-actions .btn { width: 100%; }
  .nav-links-mobile-actions :deep(.ie-pwa-install-wrap),
  .nav-links-mobile-actions :deep(.ie-pwa-install-btn) { width: 100%; justify-content: center; }
  .nav-scrim { display: none; position: fixed; inset: 0; background: rgba(30, 42, 51, 0.35); z-index: 70; }
  .nav-scrim.is-open { display: block; }
}

/* En dessous de 560px, le libellé complet ("Installer l'application") est
   remplacé par un libellé court ("Télécharger", voir le template) pour que
   le bouton reste toujours visible AVEC son texte à côté du logo et du
   bouton menu, sans déborder ; on resserre aussi les espacements pour lui
   laisser un peu plus de place. */
@media (max-width: 560px) {
  .nav-row { gap: 12px; }
  .nav-actions { gap: 8px; }
  .nav-actions :deep(.ie-pwa-install-btn) { padding: 8px 12px; font-size: 0.78rem; gap: 6px; }
}

/* Hero */
.hero { position: relative; color: #fff; overflow: hidden; }
.hero-media { position: absolute; inset: 0; background: #3d0a0e; }
.hero-ph {
  position: absolute; inset: 0; background: center/cover no-repeat; opacity: 0;
  transition: opacity 1.6s ease;
}
.hero-ph.is-active { opacity: 1; }
@media (prefers-reduced-motion: reduce) { .hero-ph { transition: none; } }
.hero-scrim { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(45, 10, 13, 0.55) 0%, rgba(45, 10, 13, 0.72) 55%, rgba(45, 10, 13, 0.9) 100%); }
.hero-inner { position: relative; padding: 150px 0 110px; max-width: 720px; }
.hero h1 { color: #fff; font-size: clamp(2.3rem, 5vw, 3.6rem); line-height: 1.08; font-weight: 500; letter-spacing: -0.01em; }
.hero h1 em {
  position: relative; font-style: italic; color: var(--slate-light); font-weight: 400;
}
.hero h1 em::after {
  content: ""; position: absolute; left: 1px; right: 1px; bottom: 3px; height: 2px;
  background: var(--wine); transform: scaleX(0); transform-origin: left;
  transition: transform 0.7s var(--ease) 0.9s;
}
.hero h1.is-visible em::after { transform: scaleX(1); }
.hero p.lede { color: rgba(255, 255, 255, 0.86); margin: 22px 0 34px; font-size: 1.08rem; }
.hero-ctas { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.hero-stats { display: flex; gap: 36px; margin-top: 64px; flex-wrap: wrap; }
/* Entrée en cascade : titre, texte, boutons, puis chiffres clés — plutôt que tout
   le bloc héro qui apparaît d'un bloc, moins soigné pour une première impression. */
.hero-inner h1[data-reveal] { transition-delay: 0.05s; }
.hero-inner p.lede[data-reveal] { transition-delay: 0.22s; }
.hero-inner .hero-ctas[data-reveal] { transition-delay: 0.38s; }
.hero-inner .hero-stats[data-reveal] { transition-delay: 0.52s; }
.hero-stats div strong { display: block; font-family: var(--display); font-size: 1.7rem; font-weight: 500; color: #fff; }
.hero-stats div span { font-size: 0.82rem; color: rgba(255, 255, 255, 0.72); }

/* Nos services */
.services-section { background: var(--paper); }
.services-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.service-card {
  display: flex; flex-direction: column; align-items: flex-start; gap: 12px;
  background: var(--paper); border: 1px solid var(--stone-line); border-radius: 14px;
  padding: 32px 26px; cursor: pointer;
  transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease), border-color 0.25s var(--ease);
}
.service-card:hover, .service-card:focus-visible { transform: translateY(-6px); box-shadow: 0 20px 44px rgba(30, 42, 51, 0.12); border-color: var(--wine); }
.service-card-icon {
  width: 56px; height: 56px; border-radius: 14px; background: var(--wine-tint); color: var(--wine);
  display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0;
  transition: background 0.25s var(--ease), color 0.25s var(--ease);
}
.service-card:hover .service-card-icon { background: var(--wine); color: #fff; }
.service-card h3 { font-size: 1.2rem; font-weight: 600; }
.service-card p { color: var(--ink-soft); font-size: 0.92rem; flex-grow: 1; }
.service-card-cta {
  display: inline-flex; align-items: center; gap: 8px; font-size: 0.86rem; font-weight: 700; color: var(--wine);
  margin-top: 2px; transition: gap 0.2s var(--ease);
}
.service-card-cta i { font-size: 11px; transition: transform 0.2s var(--ease); }
.service-card:hover .service-card-cta { gap: 12px; }
.service-card:hover .service-card-cta i { transform: translateX(2px); }
@media (max-width: 860px) { .services-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .services-grid { grid-template-columns: 1fr; } }

/* Marketplace InnovEvent */
.marketplace-section { background: var(--cream); }
.marketplace-benefits {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 44px;
}
.marketplace-benefit { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 10px; }
.marketplace-benefit-icon {
  width: 46px; height: 46px; border-radius: 50%; background: var(--wine-tint); color: var(--wine);
  display: flex; align-items: center; justify-content: center; font-size: 17px; flex-shrink: 0;
}
.marketplace-benefit p { margin: 0; font-size: 0.85rem; color: var(--ink-soft); line-height: 1.5; }
.marketplace-cta { display: flex; flex-direction: column; align-items: center; gap: 12px; margin-top: 40px; }
@media (max-width: 860px) { .marketplace-benefits { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .marketplace-benefits { grid-template-columns: 1fr; } }

/* Vous êtes prestataire ? */
.provider-section { background: var(--paper); }
.provider-wrap { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 56px; align-items: center; }
.provider-text .lede { margin: 14px 0 24px; }
.provider-benefits { list-style: none; margin: 0 0 28px; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.provider-benefits li { display: flex; align-items: flex-start; gap: 12px; font-size: 0.92rem; color: var(--ink-soft); line-height: 1.4; }
.provider-benefits li i { color: var(--wine); font-size: 15px; margin-top: 2px; flex-shrink: 0; width: 18px; }
.provider-card {
  background: var(--ink); background-image: radial-gradient(120% 140% at 100% 0%, rgba(192, 39, 45, 0.18), transparent 55%);
  color: #fff; border-radius: 20px; padding: 44px 38px;
  display: flex; flex-direction: column; align-items: flex-start; gap: 10px;
}
.provider-card-icon {
  width: 56px; height: 56px; border-radius: 14px; background: var(--wine); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 8px;
}
.provider-card h3 { color: #fff; font-size: 1.25rem; font-weight: 600; margin: 0; }
.provider-card p { color: rgba(255, 255, 255, 0.78); font-size: 0.9rem; line-height: 1.55; margin: 0 0 8px; }
.provider-card-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; width: 100%; }
.provider-card-list li { display: flex; align-items: center; gap: 10px; font-size: 0.88rem; color: rgba(255, 255, 255, 0.92); padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.12); }
.provider-card-list li i { color: var(--wine); font-size: 12px; }
@media (max-width: 860px) { .provider-wrap { grid-template-columns: 1fr; gap: 32px; } }

/* Qui sommes-nous */
.about-vision {
  max-width: 760px; margin: 0 auto 48px; padding: 30px 36px; border-radius: 12px;
  background: var(--wine-tint); border-left: 4px solid var(--wine);
}
.about-vision-kicker { display: block; font-weight: 700; font-size: 0.8rem; color: var(--wine); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px; }
.about-vision p { font-family: var(--display); font-size: 1.15rem; font-style: italic; color: var(--ink); line-height: 1.5; }

.about-values-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 52px; }
.about-value-card { background: var(--paper); border: 1px solid var(--stone-line); border-radius: 12px; padding: 26px 24px; transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease); }
.about-value-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(30, 42, 51, 0.08); }
.about-value-icon { width: 44px; height: 44px; border-radius: 10px; background: var(--wine-tint); color: var(--wine); display: flex; align-items: center; justify-content: center; font-size: 17px; margin-bottom: 14px; }
.about-value-card h4 { font-size: 1.02rem; font-weight: 600; margin-bottom: 6px; }
.about-value-card p { color: var(--ink-soft); font-size: 0.88rem; }
@media (max-width: 860px) { .about-values-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .about-values-grid { grid-template-columns: 1fr; } }

/* Pourquoi nous choisir */
.about-why-section {
  background: var(--ink);
  background-image: radial-gradient(120% 140% at 100% 0%, rgba(192, 39, 45, 0.16), transparent 55%);
}
.about-why-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.about-why-card {
  display: flex; align-items: center; gap: 16px; padding: 22px 24px; border-radius: 12px;
  background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
  transition: background 0.25s var(--ease), border-color 0.25s var(--ease), transform 0.25s var(--ease);
}
.about-why-card:hover { background: rgba(255, 255, 255, 0.09); border-color: rgba(255, 255, 255, 0.22); transform: translateY(-2px); }
.about-why-icon {
  width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
  background: rgba(192, 39, 45, 0.18); border: 1px solid rgba(192, 39, 45, 0.4); color: #f3b9bc;
  display: flex; align-items: center; justify-content: center; font-size: 17px;
}
.about-why-card p { color: rgba(255, 255, 255, 0.82); font-size: 0.92rem; line-height: 1.4; margin: 0; }
@media (max-width: 860px) { .about-why-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .about-why-grid { grid-template-columns: 1fr; } }

/* Value strip */
.value-strip { background: var(--paper); border-bottom: 1px solid var(--stone-line); }
.value-grid { display: grid; grid-template-columns: repeat(3, 1fr); }
.value-item { padding: 42px var(--gutter); border-left: 1px solid var(--stone-line); }
.value-item:first-child { border-left: none; }
.value-item .num { font-family: var(--display); font-style: italic; color: var(--slate); font-size: 1rem; margin-bottom: 10px; display: block; }
.value-item h3 { font-size: 1.05rem; font-weight: 600; margin-bottom: 8px; }
.value-item p { color: var(--ink-soft); font-size: 0.92rem; }
@media (max-width: 860px) {
  .value-grid { grid-template-columns: 1fr; }
  .value-item { border-left: none; border-top: 1px solid var(--stone-line); }
  .value-item:first-child { border-top: none; }
}

/* Chiffres clés */
.stats-band { background: var(--ink); padding: 56px 0; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.stats-item { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px; }
.stats-icon {
  width: 48px; height: 48px; border-radius: 50%; background: rgba(192, 39, 45, 0.16); color: var(--wine);
  display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;
}
.stats-item strong {
  font-family: var(--display); font-size: clamp(1.9rem, 3vw, 2.4rem); font-weight: 600; color: #fff;
  font-variant-numeric: tabular-nums; line-height: 1;
}
.stats-label { font-size: 0.9rem; color: rgba(255, 255, 255, 0.68); max-width: 22ch; }
@media (max-width: 720px) { .stats-grid { grid-template-columns: 1fr; gap: 28px; } }

/* Pôles */
.poles-feature { display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 56px; align-items: center; margin-bottom: 56px; }
.poles-feature-photo { aspect-ratio: 4/3; border-radius: 10px; overflow: hidden; background: var(--stone); }
.poles-feature-photo.is-clickable { cursor: zoom-in; }
.poles-feature-photo img { width: 100%; height: 100%; object-fit: cover; }
.poles-feature-photo-empty { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 40px; color: var(--muted); }
.poles-feature-text h3 { font-size: 1.9rem; font-weight: 500; margin-bottom: 16px; }
.poles-feature-text p { color: var(--ink-soft); margin-bottom: 22px; }
.poles-feature-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 26px; }
.poles-feature-list li { display: flex; gap: 10px; align-items: flex-start; font-size: 0.94rem; color: var(--ink-soft); }
.poles-feature-list svg { width: 16px; height: 16px; flex-shrink: 0; margin-top: 3px; color: var(--wine); }

.poles-feature-sublists { display: flex; flex-direction: column; gap: 22px; margin-bottom: 8px; }
.poles-feature-sublabel { font-weight: 700; font-size: 0.78rem; color: var(--slate); text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 12px; }

.poles-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--stone-line); border: 1px solid var(--stone-line); }
.pole-card { background: var(--paper); padding: 30px 28px; display: flex; flex-direction: column; gap: 12px; transition: background 0.25s var(--ease); }
.pole-card:hover { background: var(--wine-tint); }
.pole-card-icon { width: 40px; height: 40px; border-radius: 10px; background: var(--wine-tint); color: var(--wine); display: flex; align-items: center; justify-content: center; font-size: 16px; }
.pole-card-photo { aspect-ratio: 16/10; border-radius: 8px; overflow: hidden; margin: -30px -28px 4px; background: var(--stone); }
.pole-card-photo img { width: 100%; height: 100%; object-fit: cover; }
.pole-card h4 { font-size: 1.15rem; font-weight: 600; }
.pole-card p { color: var(--ink-soft); font-size: 0.9rem; flex-grow: 1; }
.pole-card .text-link { font-size: 0.86rem; align-self: flex-start; }
@media (max-width: 860px) {
  .poles-feature { grid-template-columns: 1fr; gap: 28px; }
  .poles-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 560px) { .poles-grid { grid-template-columns: 1fr; } }

/* Media (academy/portfolio/equipment) */
.media-photo { aspect-ratio: 4/3; background: var(--stone); position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.media-photo img { width: 100%; height: 100%; object-fit: cover; }
.media-photo i { font-size: 26px; color: var(--muted); }
.media-empty { color: var(--muted); font-size: 0.9rem; grid-column: 1 / -1; }
.media-skeleton { background: linear-gradient(90deg, var(--stone) 25%, #eee 37%, var(--stone) 63%); background-size: 400% 100%; animation: land-shimmer 1.4s ease infinite; border-radius: 10px; }
@keyframes land-shimmer { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }

/* Showcase déco */
.media-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.media-card { border-radius: 10px; overflow: hidden; background: var(--paper); border: 1px solid var(--stone-line); }
.media-label { display: block; padding: 10px 12px; font-size: 0.86rem; font-weight: 600; color: var(--ink); }
@media (max-width: 860px) { .media-grid { grid-template-columns: repeat(2, 1fr); } }

/* Cliquable → agrandissement (lightbox) */
.is-clickable, .media-photo.is-clickable { cursor: zoom-in; }
.media-zoom {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(20, 24, 28, 0.32); color: #fff; font-size: 18px; opacity: 0;
  transition: opacity 0.2s var(--ease);
}
.is-clickable:hover .media-zoom { opacity: 1; }

/* Scope + filtre galerie réalisations */
.scope-row { display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.scope-btn {
  padding: 12px 26px; border-radius: 999px; border: 1.5px solid rgba(255, 255, 255, 0.28); background: transparent;
  color: rgba(255, 255, 255, 0.78); font-size: 0.92rem; font-weight: 700; transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.scope-btn:hover { border-color: rgba(255, 255, 255, 0.6); color: #fff; }
.scope-btn.is-active { background: #fff; border-color: #fff; color: var(--ink); }

.filter-row { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-bottom: 32px; }
.filter-btn {
  padding: 8px 18px; border-radius: 999px; border: 1px solid rgba(255, 255, 255, 0.22); background: transparent;
  color: rgba(255, 255, 255, 0.72); font-size: 0.84rem; font-weight: 600; transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.filter-btn:hover { border-color: rgba(255, 255, 255, 0.5); color: #fff; }
.filter-btn.is-active { background: var(--wine); border-color: var(--wine); color: #fff; }
.filter-row-tier { padding-top: 20px; margin-top: -12px; border-top: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 36px; }
.filter-btn-tier { font-size: 0.78rem; padding: 6px 15px; border-color: rgba(255, 255, 255, 0.16); }
.filter-btn-tier.is-active { background: rgba(255, 255, 255, 0.14); border-color: #fff; color: #fff; }

.academy-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.academy-card .media-photo { border-radius: 10px; margin-bottom: 14px; }
.academy-card h4 { font-size: 1.02rem; font-weight: 600; margin-bottom: 4px; }
.academy-card span { font-size: 0.82rem; color: var(--muted); }
@media (max-width: 860px) { .academy-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 520px) { .academy-grid { grid-template-columns: 1fr; } }

/* Galerie (pure images, sans prix) */
.gallery { background: var(--ink); color: #fff; }
.gallery .section-head h2, .gallery .kicker { color: #fff; }
.gallery .kicker { color: var(--slate-light); }
.gallery .lede { color: rgba(255, 255, 255, 0.72); }
.gal-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.gal-item { border-radius: 4px; overflow: hidden; }
.gal-item .media-photo { background-color: #2b3238; border-radius: 4px; }
.gal-item .media-photo i { color: rgba(255, 255, 255, 0.4); }
.gal-tier {
  position: absolute; top: 10px; left: 10px; font-size: 0.68rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.03em; padding: 4px 10px; border-radius: 999px;
  background: rgba(20, 24, 28, 0.55); color: rgba(255, 255, 255, 0.85);
}
.gal-tier.is-haut { background: var(--wine); color: #fff; }
@media (max-width: 860px) { .gal-grid { grid-template-columns: repeat(2, 1fr); } }

/* Nos packs (tarifs) */
.pack-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.pack-card { background: var(--paper); border: 1px solid var(--stone-line); border-radius: 10px; overflow: hidden; transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease); }
.pack-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(30, 42, 51, 0.1); }
.pack-card-body { padding: 20px 22px 24px; display: flex; flex-direction: column; gap: 10px; }
.pack-card-body h4 { font-size: 1.1rem; font-weight: 600; }
.pack-card-body p { font-size: 0.88rem; color: var(--ink-soft); }
.pack-features { display: flex; flex-direction: column; gap: 7px; margin: 0; padding: 0; list-style: none; }
.pack-features li { display: flex; align-items: center; gap: 8px; font-size: 0.86rem; color: var(--ink-soft); }
.pack-features li i { color: var(--wine); font-size: 11px; flex-shrink: 0; }
.pack-card-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; padding-top: 14px; border-top: 1px solid var(--stone-line); }
.pack-price { font-family: var(--display); font-size: 1.2rem; font-weight: 600; color: var(--wine); }
.pack-discover-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 12px;
  padding: 10px 16px; border-radius: 999px; border: 1.5px solid var(--wine); color: var(--wine);
  font-size: 0.86rem; font-weight: 700; transition: background 0.2s var(--ease), color 0.2s var(--ease);
}
.pack-discover-btn:hover { background: var(--wine); color: #fff; }
@media (max-width: 860px) { .pack-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .pack-grid { grid-template-columns: 1fr; } }

/* Équipement */
.equip-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.equip-card { background: var(--paper); border: 1px solid var(--stone-line); border-radius: 10px; overflow: hidden; transition: transform 0.25s var(--ease), box-shadow 0.25s var(--ease); }
.equip-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(30, 42, 51, 0.1); }
.equip-card .media-photo { border-radius: 0; }
.equip-card-body { padding: 20px 22px 24px; display: flex; flex-direction: column; gap: 10px; }
.equip-card h4 { font-size: 1.05rem; font-weight: 600; }
.equip-stars { display: flex; gap: 2px; color: var(--wine); font-size: 12px; }
.equip-card p { font-size: 0.88rem; color: var(--ink-soft); }
.equip-card-foot { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 4px; }
.equip-price { font-size: 0.85rem; font-weight: 700; color: var(--ink); white-space: nowrap; }
.equip-reserve-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 20px; border-radius: 999px; background: var(--wine); color: #fff;
  font-size: 0.84rem; font-weight: 600; transition: background 0.2s var(--ease), transform 0.2s var(--ease), gap 0.2s var(--ease);
}
.equip-reserve-btn i { font-size: 11px; transition: transform 0.2s var(--ease); }
.equip-reserve-btn:hover { background: var(--wine-dark); gap: 12px; }
.equip-reserve-btn:hover i { transform: translateX(2px); }
@media (max-width: 860px) { .equip-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .equip-grid { grid-template-columns: 1fr; } }

/* Mon projet */
.project-section { background: var(--wine-tint); }
.project-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: center; }
.project-text h2 { font-size: clamp(1.7rem, 3vw, 2.4rem); font-weight: 500; margin-bottom: 16px; }
.project-text p { color: var(--ink-soft); margin-bottom: 24px; max-width: 48ch; }
.project-card { background: var(--paper); border: 1px solid var(--stone-line); border-radius: 10px; box-shadow: 0 30px 60px rgba(138, 14, 22, 0.12); overflow: hidden; }
.project-card-head { background: var(--ink); color: #fff; padding: 20px 26px; display: flex; justify-content: space-between; align-items: center; }
.project-card-head span { font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); display: block; }
.project-card-head strong { font-family: var(--display); font-size: 1.15rem; font-weight: 500; }
.project-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 22px 26px; border-bottom: 1px solid var(--stone-line); }
.project-meta div span { display: block; font-size: 0.74rem; color: var(--muted); margin-bottom: 3px; }
.project-meta div strong { font-size: 0.94rem; font-weight: 600; }
.project-list { padding: 18px 26px; display: flex; flex-direction: column; gap: 12px; }
.project-list li { display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; }
.project-list li .tag { display: inline-flex; align-items: center; gap: 8px; color: var(--ink-soft); }
.project-list li .tag i { color: var(--wine); width: 16px; }
.project-list li .amount { font-weight: 600; }
.project-total { display: flex; justify-content: space-between; align-items: center; padding: 20px 26px; background: var(--cream); border-top: 1px solid var(--stone-line); }
.project-total span { font-size: 0.86rem; color: var(--ink-soft); }
.project-total strong { font-family: var(--display); font-size: 1.3rem; font-weight: 600; color: var(--wine); }
@media (max-width: 860px) { .project-wrap { grid-template-columns: 1fr; gap: 36px; } }

/* Gammes */
.gammes { background: var(--ink); color: #fff; }
.gammes-grid { display: grid; grid-template-columns: repeat(4, 1fr); }
.gamme-item { padding: 36px 30px; border-left: 1px solid rgba(255, 255, 255, 0.14); }
.gamme-item:first-child { border-left: none; }
.gamme-item h4 { font-family: var(--display); font-weight: 500; font-size: 1.15rem; margin-bottom: 10px; color: #fff; }
.gamme-item p { color: rgba(255, 255, 255, 0.68); font-size: 0.88rem; }
@media (max-width: 860px) {
  .gammes-grid { grid-template-columns: 1fr 1fr; }
  .gamme-item:nth-child(2) { border-left: 1px solid rgba(255, 255, 255, 0.14); }
  .gamme-item:nth-child(3) { border-left: none; border-top: 1px solid rgba(255, 255, 255, 0.14); }
}
@media (max-width: 520px) {
  .gammes-grid { grid-template-columns: 1fr; }
  .gamme-item { border-left: none !important; border-top: 1px solid rgba(255, 255, 255, 0.14); }
  .gamme-item:first-child { border-top: none; }
}

/* Témoignages */
.testimonials { background: var(--cream); }
.testimonials-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.testimonial-card { background: var(--paper); border: 1px solid var(--stone-line); border-radius: 10px; padding: 30px 26px; display: flex; flex-direction: column; gap: 16px; }
.testimonial-stars { display: flex; gap: 3px; color: var(--wine); font-size: 13px; }
.testimonial-quote { font-size: 0.94rem; color: var(--ink-soft); flex-grow: 1; }
.testimonial-author { display: flex; flex-direction: column; gap: 2px; border-top: 1px solid var(--stone-line); padding-top: 14px; }
.testimonial-name { font-weight: 600; font-size: 0.92rem; color: var(--ink); }
.testimonial-meta { font-size: 0.8rem; color: var(--muted); }
@media (max-width: 860px) { .testimonials-grid { grid-template-columns: 1fr; } }

/* Contact */
.contact-wrap { display: grid; grid-template-columns: 0.85fr 1.15fr; gap: 0; border: 1px solid var(--stone-line); border-radius: 10px; overflow: hidden; background: var(--paper); }
.contact-info { padding: 44px 42px; display: flex; flex-direction: column; gap: 26px; }
.contact-info h2 { font-size: 1.7rem; font-weight: 500; }
.contact-row { display: flex; gap: 14px; align-items: flex-start; }
.contact-row i { color: var(--wine); flex-shrink: 0; margin-top: 3px; width: 18px; }
.contact-row div span { display: block; font-size: 0.76rem; color: var(--muted); margin-bottom: 2px; }
.contact-row div strong { font-size: 0.96rem; font-weight: 600; }
.social-row { display: flex; gap: 12px; margin-top: 6px; }
.social-btn {
  width: 42px; height: 42px; border-radius: 50%; border: 1px solid var(--stone-line);
  display: flex; align-items: center; justify-content: center; color: var(--ink);
  transition: background 0.2s, color 0.2s, border-color 0.2s, transform 0.2s;
}
.social-btn:hover { transform: translateY(-3px); }
.social-btn.fb:hover { background: #1877f2; border-color: #1877f2; color: #fff; }
.social-btn.tt:hover { background: #000; border-color: #000; color: #fff; }
.social-btn.wa:hover { background: var(--whatsapp); border-color: var(--whatsapp); color: #fff; }
.map-embed { min-height: 420px; background: var(--stone); }
.map-embed iframe { width: 100%; height: 100%; min-height: 420px; border: 0; display: block; }
@media (max-width: 860px) { .contact-wrap { grid-template-columns: 1fr; } .map-embed { order: -1; } }

/* CTA banner */
.cta-banner {
  background: var(--wine); color: #fff; text-align: center; padding: 90px var(--gutter);
  background-image: radial-gradient(circle at 15% 20%, rgba(255, 255, 255, 0.08), transparent 45%), radial-gradient(circle at 85% 80%, rgba(255, 255, 255, 0.08), transparent 45%);
}
.cta-banner h2 { color: #fff; font-size: clamp(1.8rem, 3.4vw, 2.6rem); font-weight: 500; max-width: 720px; margin: 0 auto 18px; }
.cta-banner p { color: rgba(255, 255, 255, 0.78); max-width: 520px; margin: 0 auto 32px; }
.cta-banner .hero-ctas { justify-content: center; }

/* Footer */
footer { background: #141d24; color: rgba(255, 255, 255, 0.78); padding: 70px 0 0; }
.footer-top { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1.2fr; gap: 40px; padding-bottom: 56px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.footer-brand p { margin: 16px 0 22px; font-size: 0.9rem; color: rgba(255, 255, 255, 0.58); max-width: 34ch; }
footer h5 { font-size: 0.82rem; font-weight: 600; color: #fff; margin-bottom: 16px; }
footer ul li { margin-bottom: 10px; }
footer ul li a { font-size: 0.9rem; color: rgba(255, 255, 255, 0.6); transition: color 0.2s; }
footer ul li a:hover { color: #fff; }
.footer-social { display: flex; gap: 10px; margin-top: 4px; }
.footer-social .social-btn { border-color: rgba(255, 255, 255, 0.2); color: #fff; }
.footer-bottom { display: flex; justify-content: space-between; align-items: center; padding: 22px 0; gap: 16px; flex-wrap: wrap; font-size: 0.8rem; color: rgba(255, 255, 255, 0.45); }
@media (max-width: 860px) { .footer-top { grid-template-columns: 1fr 1fr; } }
@media (max-width: 560px) { .footer-top { grid-template-columns: 1fr; } }

/* Floating WhatsApp */
.wa-float {
  position: fixed; right: 22px; bottom: 22px; z-index: 90;
  width: 58px; height: 58px; border-radius: 50%; background: var(--whatsapp); color: #fff;
  display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 26px rgba(37, 167, 91, 0.45);
  transition: transform 0.25s var(--ease); font-size: 26px;
}
.wa-float:hover { transform: scale(1.07); }

/* Floating "Créer mon projet" — même comportement que le bouton WhatsApp flottant */
.project-float {
  position: fixed; right: 22px; bottom: 92px; z-index: 90;
  display: flex; align-items: center; gap: 9px;
  padding: 14px 22px; border-radius: 999px; background: var(--wine); color: #fff;
  font-size: 0.88rem; font-weight: 600; white-space: nowrap;
  box-shadow: 0 10px 26px rgba(192, 39, 45, 0.4);
  transition: transform 0.25s var(--ease), background 0.25s var(--ease);
}
.project-float:hover { transform: scale(1.07); background: var(--wine-dark); }
.project-float i { font-size: 13px; }
.float-in-enter-active, .float-in-leave-active { transition: opacity 0.3s var(--ease), transform 0.3s var(--ease); }
.float-in-enter-from, .float-in-leave-to { opacity: 0; transform: translateY(12px) scale(0.9); }
@media (max-width: 560px) {
  .project-float span { display: none; }
  .project-float { padding: 16px; border-radius: 50%; width: 58px; height: 58px; }
}

/* Reveal */
.ie-land :deep([data-reveal]),
.ie-land :deep([data-reveal-group] > *) {
  opacity: 0; transform: translateY(18px);
  transition: opacity 0.7s var(--ease), transform 0.7s var(--ease);
}
.ie-land :deep(.is-visible) { opacity: 1 !important; transform: translateY(0) !important; }

/* Effet cascade : chaque carte d'une grille apparaît un peu après la précédente
   au lieu de surgir toutes en même temps — un détail qui distingue une animation
   soignée d'un simple fondu générique. Plafonné pour ne pas faire attendre les
   grandes grilles (galerie, métiers...). */
.ie-land :deep([data-reveal-group] > *:nth-child(1)) { transition-delay: 0s; }
.ie-land :deep([data-reveal-group] > *:nth-child(2)) { transition-delay: 0.08s; }
.ie-land :deep([data-reveal-group] > *:nth-child(3)) { transition-delay: 0.16s; }
.ie-land :deep([data-reveal-group] > *:nth-child(4)) { transition-delay: 0.24s; }
.ie-land :deep([data-reveal-group] > *:nth-child(5)) { transition-delay: 0.32s; }
.ie-land :deep([data-reveal-group] > *:nth-child(6)) { transition-delay: 0.4s; }
.ie-land :deep([data-reveal-group] > *:nth-child(n+7)) { transition-delay: 0.48s; }

@media (prefers-reduced-motion: reduce) {
  .ie-land :deep([data-reveal]), .ie-land :deep([data-reveal-group] > *) { transition-duration: 0.001ms; transition-delay: 0s !important; }
  .hero h1 em::after { transition-duration: 0.001ms; transition-delay: 0s !important; }
}
</style>
