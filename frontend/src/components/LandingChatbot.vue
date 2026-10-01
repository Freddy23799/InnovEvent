<script setup>
import { computed, nextTick, ref } from "vue";

// Base de connaissances dérivée du document de positionnement InnovEvent Group
// (historique, vision, mission, valeurs, pôles d'activité...). Correspondance
// simple par mots-clés — pas d'appel réseau, pas d'authentification requise :
// ce chatbot doit répondre à tout visiteur anonyme de la page d'accueil.
const FAQS = [
  {
    id: "presentation",
    chip: "Qui êtes-vous ?",
    keywords: ["qui etes vous", "qui es tu", "presentation", "c'est quoi innovevent", "innovevent group", "acamed", "vous etes qui"],
    answer: "INNOVEVENT, en collaboration avec ACAMED (Académie des Métiers de l'Événementiel et du Design), est une entreprise multiservices qui conçoit, planifie et organise des événements à forte valeur ajoutée pour les entreprises, institutions, associations et particuliers — et forme les talents de demain aux métiers de l'événementiel et du design.",
  },
  {
    id: "historique",
    keywords: ["historique", "depuis quand", "origine", "a vos debuts", "evolution de l'activite"],
    answer: "INNOVEVENT s'est d'abord développée autour de l'organisation d'événements privés, professionnels et institutionnels. Face à l'évolution des besoins de nos clients, nous évoluons aujourd'hui vers une entreprise multiservices : événement, maison, design, formation, commerce, tourisme et hébergement.",
  },
  {
    id: "vision",
    chip: "Quelle est votre vision ?",
    keywords: ["vision"],
    answer: "Construire un écosystème de services permettant à chacun d'accéder, depuis un même espace, à des solutions dans l'événement, la maison, le design, la formation, le commerce, le tourisme et l'hébergement.",
  },
  {
    id: "mission",
    keywords: ["mission"],
    answer: "Simplifier l'accès à des services de qualité en réunissant, dans un même écosystème, des professionnels, des produits et des prestations complémentaires — pour vous faire gagner du temps et vous proposer des offres adaptées à votre budget.",
  },
  {
    id: "valeurs",
    keywords: ["valeurs"],
    answer: "Nos valeurs : Innovation, Créativité, Qualité, Accessibilité, Professionnalisme, Fiabilité et Expérience client — vous pouvez les découvrir en détail dans la section « Qui sommes-nous » de cette page.",
  },
  {
    id: "poles",
    chip: "Quels sont vos domaines d'activité ?",
    keywords: ["domaine", "pole", "poles", "activites", "services proposes", "que proposez vous", "que faites vous"],
    answer: "Nous intervenons sur plusieurs pôles complémentaires réunis sous la marque InnovEvent Group : Events (organisation d'événements), Home & Design (décoration et aménagement), Shop (vente d'objets et équipements), Academy (formations), Travel (tourisme) et Stay (hébergement).",
  },
  {
    id: "evenementiel",
    keywords: ["mariage", "bapteme", "anniversaire", "gala", "conference", "seminaire", "salon", "team building", "evenement entreprise", "evenement institutionnel", "cocktail"],
    answer: "Nous organisons tout type d'événement, en prise en charge complète ou partielle : mariages, baptêmes, anniversaires, galas, cérémonies, conférences, séminaires, salons professionnels, team building, événements corporate et institutionnels, lancements de produits...",
  },
  {
    id: "decoration",
    keywords: ["decoration", "scenographie", "deco"],
    answer: "Notre pôle Décoration & Scénographie couvre la décoration événementielle, la décoration de salles et extérieure, la décoration florale, la scénographie, la décoration de tables et la conception d'ambiances thématiques.",
  },
  {
    id: "specialises",
    chip: "Proposez-vous photo, vidéo, traiteur... ?",
    keywords: ["photo", "video", "traiteur", "patisserie", "gateau", "dj", "animation", "impresario", "artiste", "graphisme", "infographie", "impression", "flyer", "invitation", "mc"],
    answer: "Oui : au-delà de l'organisation, nous proposons ou coordonnons via notre réseau de partenaires la photographie, la vidéo, le traiteur, la pâtisserie événementielle (wedding cakes...), l'animation (DJ, MC, artistes, danseurs...), l'impresario, le graphisme/infographie (invitations, affiches, identité visuelle) et l'impression.",
  },
  {
    id: "location",
    keywords: ["location salle", "location materiel", "chaise", "table", "chapiteau", "sonorisation", "louer"],
    answer: "Nous proposons la location de salles de réception et de conférence, de jardins et espaces extérieurs, ainsi que de matériel événementiel : tables, chaises, vaisselle, chapiteaux, tentes, mobilier, éclairage, sonorisation...",
  },
  {
    id: "home",
    keywords: ["home design", "decoration interieure", "amenagement maison", "design interieur"],
    answer: "InnovEvent & Home est notre pôle dédié à la décoration intérieure, au design d'espaces et à l'aménagement résidentiel et professionnel — le prolongement naturel de notre expertise en décoration événementielle vers la décoration permanente.",
  },
  {
    id: "shop",
    keywords: ["shop", "boutique", "acheter", "vente objet", "produit deco"],
    answer: "InnovEvent Shop proposera à terme une boutique en ligne d'objets décoratifs, de mobilier et d'équipements événementiels. Ce pôle est en cours de développement.",
  },
  {
    id: "academy",
    chip: "Proposez-vous des formations ?",
    keywords: ["formation", "academy", "apprendre", "wedding planner", "cours", "certifiant"],
    answer: "InnovEvent Academy propose des formations en décoration événementielle, wedding planning, organisation événementielle, design intérieur et entrepreneuriat créatif — formations certifiantes, ateliers pratiques et masterclass, avec attestation à la clé.",
  },
  {
    id: "travel",
    keywords: ["travel", "tourisme", "voyage", "excursion", "sejour touristique"],
    answer: "InnovEvent Travel proposera des circuits touristiques, excursions et expériences à associer à vos événements (par exemple : mariage + séjour touristique). Ce pôle est en cours de développement.",
  },
  {
    id: "stay",
    keywords: ["stay", "hebergement", "logement", "appartement meuble"],
    answer: "InnovEvent Stay proposera des solutions d'hébergement — logements temporaires, appartements meublés — pour vos invités ou vos séjours touristiques. Ce pôle est en cours de développement.",
  },
  {
    id: "fonctionnement",
    chip: "Comment ça marche ?",
    keywords: ["comment ca marche", "comment reserver", "projet client", "fonctionnement", "comment ca fonctionne"],
    answer: "Vous créez votre compte, décrivez votre projet (date, lieu, nombre d'invités, budget), puis vous sélectionnez les prestations dont vous avez besoin (salle, décoration, traiteur, DJ...). Le coût estimatif se met à jour automatiquement et vous suivez tout depuis votre espace client.",
  },
  {
    id: "prix",
    chip: "Quelles sont vos gammes de prix ?",
    keywords: ["prix", "tarif", "budget", "gamme", "combien ca coute", "cher"],
    answer: "Nos offres sont classées en quatre gammes pour s'adapter à votre budget : Accessible, Standard/Confort, Premium et Luxe/Sur mesure.",
  },
  {
    id: "contact",
    chip: "Comment vous contacter ?",
    keywords: ["contact", "telephone", "whatsapp", "adresse", "joindre", "numero"],
    answer: "Vous pouvez nous joindre au +237 6 73 00 39 93 (WhatsApp) ou nous rendre visite Rue Germaine Ahidjo, Yaoundé. Toute l'équipe est disponible du lundi au samedi, de 8h à 19h.",
  },
  {
    id: "pourquoi",
    keywords: ["pourquoi vous choisir", "difference", "avantage", "pourquoi innovevent"],
    answer: "Parce que nous sommes une structure professionnelle organisée, avec une expertise combinée événementiel + formation, des offres flexibles et personnalisées, un réseau de prestataires qualifiés, et un accompagnement avant, pendant et après votre événement.",
  },
  {
    id: "inscription",
    keywords: ["creer compte", "inscription", "devis", "s'inscrire", "creer mon projet"],
    answer: "Cliquez sur « Créer mon projet » en haut de page pour créer votre compte gratuitement, ou sur « Demande de devis » pour être recontacté rapidement par notre équipe.",
  },
];

const SUGGESTIONS = FAQS.filter((f) => f.chip);

function normalize(str) {
  return str
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function findAnswer(text) {
  const normalized = normalize(text);
  let best = null;
  let bestScore = 0;
  for (const faq of FAQS) {
    let score = 0;
    for (const kw of faq.keywords) {
      if (normalized.includes(normalize(kw))) score += 1;
    }
    if (score > bestScore) {
      bestScore = score;
      best = faq;
    }
  }
  return best;
}

const FALLBACK = "Je n'ai pas encore la réponse précise à cette question 🙂 Écrivez-nous directement sur WhatsApp, notre équipe vous répondra rapidement !";

const isOpen = ref(false);
const messages = ref([
  { role: "bot", text: "Bonjour 👋 Je suis l'assistant InnovEvent. Posez-moi une question sur nos services, nos pôles d'activité ou notre fonctionnement — ou choisissez une suggestion ci-dessous." },
]);
const draft = ref("");
const messagesEl = ref(null);

function toggle() {
  isOpen.value = !isOpen.value;
}

async function scrollToBottom() {
  await nextTick();
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function respond(userText) {
  messages.value.push({ role: "user", text: userText });
  const match = findAnswer(userText);
  messages.value.push({ role: "bot", text: match ? match.answer : FALLBACK, fallback: !match });
  scrollToBottom();
}

function send() {
  const text = draft.value.trim();
  if (!text) return;
  draft.value = "";
  respond(text);
}

function askSuggestion(faq) {
  respond(faq.chip);
}

const remainingSuggestions = computed(() => SUGGESTIONS);
</script>

<template>
  <div class="ie-chatbot">
    <Transition name="chatbot-pop">
      <div v-if="isOpen" class="ie-chatbot-panel" role="dialog" aria-label="Assistant InnovEvent">
        <div class="ie-chatbot-head">
          <div class="ie-chatbot-head-info">
            <span class="ie-chatbot-avatar"><i class="fa-solid fa-robot"></i></span>
            <div>
              <strong>Assistant InnovEvent</strong>
              <span>Répond à vos questions sur nos services</span>
            </div>
          </div>
          <button type="button" class="ie-chatbot-close" aria-label="Fermer l'assistant" @click="toggle">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="ie-chatbot-messages" ref="messagesEl">
          <div v-for="(m, i) in messages" :key="i" class="ie-chatbot-msg" :class="`is-${m.role}`">
            <p>{{ m.text }}</p>
            <a v-if="m.fallback" href="https://wa.me/237673003993" target="_blank" rel="noopener" class="ie-chatbot-wa-link">
              <i class="fa-brands fa-whatsapp"></i> Écrire sur WhatsApp
            </a>
          </div>
        </div>

        <div class="ie-chatbot-suggestions">
          <button v-for="faq in remainingSuggestions" :key="faq.id" type="button" class="ie-chatbot-chip" @click="askSuggestion(faq)">
            {{ faq.chip }}
          </button>
        </div>

        <form class="ie-chatbot-input-row" @submit.prevent="send">
          <input v-model="draft" type="text" placeholder="Posez votre question…" aria-label="Votre question" />
          <button type="submit" aria-label="Envoyer"><i class="fa-solid fa-paper-plane"></i></button>
        </form>
      </div>
    </Transition>

    <button type="button" class="ie-chatbot-toggle" :class="{ 'is-open': isOpen }" @click="toggle" aria-label="Ouvrir l'assistant InnovEvent">
      <i class="fa-solid" :class="isOpen ? 'fa-xmark' : 'fa-comment-dots'"></i>
    </button>
  </div>
</template>

<style scoped>
.ie-chatbot { position: fixed; left: 22px; bottom: 22px; z-index: 95; }

.ie-chatbot-toggle {
  width: 58px; height: 58px; border-radius: 50%; background: var(--wine); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 24px;
  box-shadow: 0 10px 26px rgba(192, 39, 45, 0.4);
  transition: transform 0.25s var(--ease), background 0.25s var(--ease);
}
.ie-chatbot-toggle:hover { transform: scale(1.07); background: var(--wine-dark); }
.ie-chatbot-toggle.is-open { background: var(--ink); }

.ie-chatbot-panel {
  position: absolute; left: 0; bottom: 72px; width: min(360px, calc(100vw - 44px));
  background: var(--paper); border-radius: 14px; overflow: hidden;
  box-shadow: 0 24px 60px rgba(30, 42, 51, 0.28); border: 1px solid var(--stone-line);
  display: flex; flex-direction: column; max-height: min(560px, 70vh);
}

.ie-chatbot-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 16px; background: var(--ink); color: #fff; flex-shrink: 0; }
.ie-chatbot-head-info { display: flex; align-items: center; gap: 10px; }
.ie-chatbot-avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--wine); display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; }
.ie-chatbot-head-info strong { display: block; font-size: 0.92rem; font-weight: 600; }
.ie-chatbot-head-info span { font-size: 0.74rem; color: rgba(255, 255, 255, 0.65); }
.ie-chatbot-close { color: rgba(255, 255, 255, 0.7); font-size: 16px; padding: 4px; }
.ie-chatbot-close:hover { color: #fff; }

.ie-chatbot-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; background: var(--cream); }
.ie-chatbot-msg { max-width: 86%; padding: 10px 13px; border-radius: 12px; font-size: 0.86rem; line-height: 1.45; }
.ie-chatbot-msg p { margin: 0; }
.ie-chatbot-msg.is-bot { align-self: flex-start; background: var(--paper); border: 1px solid var(--stone-line); color: var(--ink); border-bottom-left-radius: 3px; }
.ie-chatbot-msg.is-user { align-self: flex-end; background: var(--wine); color: #fff; border-bottom-right-radius: 3px; }
.ie-chatbot-wa-link { display: inline-flex; align-items: center; gap: 6px; margin-top: 8px; font-size: 0.8rem; font-weight: 700; color: var(--whatsapp); }
.ie-chatbot-wa-link:hover { text-decoration: underline; }

.ie-chatbot-suggestions { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 12px; border-top: 1px solid var(--stone-line); background: var(--paper); flex-shrink: 0; }
.ie-chatbot-chip {
  padding: 6px 12px; border-radius: 999px; border: 1px solid var(--stone-line); background: var(--cream);
  color: var(--ink-soft); font-size: 0.74rem; font-weight: 600; transition: background 0.2s, border-color 0.2s, color 0.2s;
}
.ie-chatbot-chip:hover { background: var(--wine-tint); border-color: var(--wine); color: var(--wine); }

.ie-chatbot-input-row { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--stone-line); background: var(--paper); flex-shrink: 0; }
.ie-chatbot-input-row input {
  flex: 1; border: 1px solid var(--stone-line); border-radius: 999px; padding: 10px 16px; font-size: 0.85rem;
  font-family: var(--body); color: var(--ink); background: var(--cream);
}
.ie-chatbot-input-row input:focus { outline: none; border-color: var(--wine); }
.ie-chatbot-input-row button {
  width: 40px; height: 40px; border-radius: 50%; background: var(--wine); color: #fff; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 14px; transition: background 0.2s;
}
.ie-chatbot-input-row button:hover { background: var(--wine-dark); }

.chatbot-pop-enter-active, .chatbot-pop-leave-active { transition: opacity 0.2s var(--ease), transform 0.2s var(--ease); }
.chatbot-pop-enter-from, .chatbot-pop-leave-to { opacity: 0; transform: translateY(12px) scale(0.96); }

@media (max-width: 480px) {
  .ie-chatbot { left: 14px; bottom: 14px; }
  .ie-chatbot-panel { width: calc(100vw - 28px); left: -8px; }
}
</style>
