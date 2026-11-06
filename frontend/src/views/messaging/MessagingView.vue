<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const lightbox = useLightboxStore();
const toast = useToastStore();

const isAdmin = computed(() => auth.role === "admin");
const conversations = ref([]);
const messages = ref([]);
const activeConversationId = ref(null);
const newMessage = ref("");
const loading = ref(true);
const messagesLoading = ref(false);
const contactingAdmin = ref(false);
const sending = ref(false);
const search = ref("");
const listFilter = ref("all");
const showNewConversation = ref(false);
const availableUsers = ref([]);
const selectedUserId = ref("");

// Réponse de l'assistant : affichée après un court « … en train d'écrire »
// pour que l'échange se lise comme une vraie conversation.
const hiddenMessageIds = ref(new Set());
const assistantTyping = ref(false);

const threadRef = ref(null);
const composerRef = ref(null);
const fileInput = ref(null);
const showJumpToLatest = ref(false);

// --- Pièce jointe -----------------------------------------------------------
const attachmentFile = ref(null);
const attachmentPreviewUrl = ref(null);
const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024; // 20 Mo

function triggerFilePicker() {
  fileInput.value?.click();
}

function onFileSelected(e) {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  if (file.size > MAX_ATTACHMENT_SIZE) {
    toast.error("Fichier trop volumineux (20 Mo maximum).");
    return;
  }
  attachmentFile.value = file;
  if (attachmentPreviewUrl.value) URL.revokeObjectURL(attachmentPreviewUrl.value);
  attachmentPreviewUrl.value = file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
}

function clearAttachment() {
  if (attachmentPreviewUrl.value) URL.revokeObjectURL(attachmentPreviewUrl.value);
  attachmentFile.value = null;
  attachmentPreviewUrl.value = null;
}

function formatFileSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function documentIcon(contentType) {
  if (!contentType) return "fa-solid fa-file";
  if (contentType === "application/pdf") return "fa-solid fa-file-pdf";
  if (contentType.includes("word")) return "fa-solid fa-file-word";
  if (contentType.includes("sheet") || contentType.includes("excel")) return "fa-solid fa-file-excel";
  if (contentType.startsWith("audio/")) return "fa-solid fa-file-audio";
  if (contentType.startsWith("video/")) return "fa-solid fa-file-video";
  return "fa-solid fa-file";
}

function openImageMessage(msg) {
  lightbox.open(msg.attachment_url, msg.body || msg.attachment_name);
}

// --- Conversations ------------------------------------------------------------
const activeConversation = computed(() => conversations.value.find((c) => c.id === activeConversationId.value));

function others(conversation) {
  return conversation.participants.filter((p) => p.id !== auth.user?.id);
}

function conversationTitle(conversation) {
  if (conversation.is_admin_support && !isAdmin.value) return "Support InnovEvent";
  return others(conversation).map((p) => p.name).join(", ") || "Moi";
}

function conversationSubtitle(conversation) {
  if (conversation.is_admin_support && !isAdmin.value) {
    return conversation.human_handoff ? "Un conseiller vous répond ici" : "Assistant disponible · réponses instantanées";
  }
  const person = others(conversation)[0];
  if (!person) return "";
  const role = person.role_label || "";
  return person.is_online ? `${role} · en ligne` : role;
}

function isOnline(conversation) {
  if (conversation.is_admin_support && !isAdmin.value) return true;
  return others(conversation).some((p) => p.is_online);
}

function initials(name) {
  return (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
}

const AVATAR_TONES = ["#24384f", "#c0272d", "#1f7a73", "#b07a19", "#5b4a9e", "#2f6db0"];
function avatarTone(seed) {
  return AVATAR_TONES[Math.abs(Number(seed) || 0) % AVATAR_TONES.length];
}

function lastMessagePreview(conversation) {
  const last = conversation.last_message;
  if (!last) return "Aucun message";
  const text = last.body
    || (last.attachment_type === "image" ? "📷 Photo" : last.attachment_name ? `📎 ${last.attachment_name}` : "");
  if (last.is_automated) return `Assistant : ${text}`;
  return last.sender === auth.user?.id ? `Vous : ${text}` : text;
}

function listTime(value) {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return "Hier";
  if (now - date < 6 * 86400000) return date.toLocaleDateString("fr-FR", { weekday: "short" });
  return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
}

const LIST_FILTERS = computed(() => (isAdmin.value
  ? [
      { value: "all", label: "Toutes" },
      { value: "unread", label: "Non lues" },
      { value: "waiting", label: "À traiter" },
      { value: "support", label: "Support" },
    ]
  : [
      { value: "all", label: "Toutes" },
      { value: "unread", label: "Non lues" },
    ]));

// Support transmis à l'équipe et dont le dernier message n'est pas une
// réponse d'un conseiller (l'assistant écrit au nom de l'administrateur).
function needsReply(conversation) {
  const last = conversation.last_message;
  return conversation.is_admin_support && conversation.human_handoff && Boolean(last) && (last.is_automated || last.sender !== auth.user?.id);
}

function matchesFilter(conversation) {
  if (listFilter.value === "unread") return conversation.unread_count > 0;
  if (listFilter.value === "support") return conversation.is_admin_support;
  // « À traiter » : l'assistant a passé la main, un conseiller doit répondre.
  if (listFilter.value === "waiting") return needsReply(conversation);
  return true;
}

const visibleConversations = computed(() => {
  const needle = search.value.trim().toLowerCase();
  return conversations.value
    .filter(matchesFilter)
    .filter((c) => !needle || `${conversationTitle(c)} ${c.last_message?.body || ""}`.toLowerCase().includes(needle))
    .sort((a, b) => {
      // Côté client, le support reste en tête de liste.
      if (!isAdmin.value && a.is_admin_support !== b.is_admin_support) return a.is_admin_support ? -1 : 1;
      return new Date(b.last_message?.created_at || b.created_at) - new Date(a.last_message?.created_at || a.created_at);
    });
});

const totalUnread = computed(() => conversations.value.reduce((sum, c) => sum + (c.unread_count || 0), 0));
const waitingCount = computed(() => conversations.value.filter(needsReply).length);
const hasSupportConversation = computed(() => conversations.value.some((c) => c.is_admin_support));

async function loadConversations() {
  const { data } = await api.get("/messaging/conversations/");
  conversations.value = data.results || data;
}

// --- Fil de messages ----------------------------------------------------------
const visibleMessages = computed(() => messages.value.filter((m) => !hiddenMessageIds.value.has(m.id)));

function isMine(msg) {
  return msg.sender === auth.user?.id && !msg.is_automated;
}

function dayLabel(value) {
  const date = new Date(value);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) return "Aujourd'hui";
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return "Hier";
  return date.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
}

function timeLabel(value) {
  return new Date(value).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

// Messages regroupés par jour, et en « blocs » consécutifs du même auteur
// (moins de 5 minutes d'écart) : nom et avatar affichés une seule fois.
const timeline = computed(() => {
  const rows = [];
  let lastDay = "";
  let previous = null;
  visibleMessages.value.forEach((msg) => {
    const day = new Date(msg.created_at).toDateString();
    if (day !== lastDay) {
      rows.push({ type: "day", key: `day-${day}`, label: dayLabel(msg.created_at) });
      lastDay = day;
      previous = null;
    }
    const author = msg.is_automated ? "bot" : msg.sender;
    const grouped = previous && previous.author === author && new Date(msg.created_at) - new Date(previous.created_at) < 5 * 60000;
    rows.push({ type: "message", key: `msg-${msg.id}`, msg, author, first: !grouped });
    previous = { author, created_at: msg.created_at };
  });
  return rows;
});

const lastMineId = computed(() => [...visibleMessages.value].reverse().find((m) => isMine(m))?.id);

function isNearBottom() {
  const el = threadRef.value;
  return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 120;
}

async function scrollToBottom(smooth = false) {
  await nextTick();
  const el = threadRef.value;
  if (!el) return;
  el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  showJumpToLatest.value = false;
}

function onThreadScroll() {
  if (isNearBottom()) showJumpToLatest.value = false;
}

async function fetchMessages() {
  const { data } = await api.get("/messaging/messages/", { params: { conversation: activeConversationId.value } });
  return data.results || data;
}

// Rafraîchit le fil sans le reconstruire si rien n'a changé (pas de saut).
async function refreshMessages({ revealAssistant = false } = {}) {
  if (!activeConversationId.value) return;
  const conversationId = activeConversationId.value;
  const fresh = await fetchMessages();
  if (conversationId !== activeConversationId.value) return;

  const known = new Set(messages.value.filter((m) => !m.pending).map((m) => m.id));
  const incoming = fresh.filter((m) => !known.has(m.id));
  const changed = incoming.length || fresh.length !== messages.value.length
    || fresh.some((m, i) => messages.value[i] && m.is_read !== messages.value[i].is_read);
  if (!changed) return;

  const wasNearBottom = isNearBottom();
  const newAssistant = incoming.filter((m) => m.is_automated);
  if (revealAssistant && newAssistant.length) {
    newAssistant.forEach((m) => hiddenMessageIds.value.add(m.id));
    assistantTyping.value = true;
    setTimeout(() => {
      newAssistant.forEach((m) => hiddenMessageIds.value.delete(m.id));
      hiddenMessageIds.value = new Set(hiddenMessageIds.value);
      assistantTyping.value = false;
      scrollToBottom(true);
    }, 900);
  }
  messages.value = fresh;

  const fromOthers = incoming.filter((m) => !isMine(m));
  if (fromOthers.length) {
    api.post("/messaging/messages/mark-read/", { conversation: conversationId }).catch(() => {});
  }
  if (wasNearBottom || incoming.some(isMine)) scrollToBottom(true);
  else if (fromOthers.length) showJumpToLatest.value = true;
}

async function openConversation(conversation) {
  if (activeConversationId.value === conversation.id) return;
  activeConversationId.value = conversation.id;
  messages.value = [];
  hiddenMessageIds.value = new Set();
  assistantTyping.value = false;
  clearAttachment();
  messagesLoading.value = true;
  try {
    messages.value = await fetchMessages();
  } finally {
    messagesLoading.value = false;
  }
  scrollToBottom();
  if (conversation.unread_count) {
    await api.post("/messaging/messages/mark-read/", { conversation: conversation.id });
    conversation.unread_count = 0;
  }
  nextTick(() => composerRef.value?.focus());
}

function closeConversation() {
  activeConversationId.value = null;
  messages.value = [];
}

// --- Envoi --------------------------------------------------------------------
async function sendMessage(text = null) {
  const body = (text ?? newMessage.value).trim();
  if (!activeConversationId.value || (!body && !attachmentFile.value) || sending.value) return;
  const conversation = activeConversation.value;
  const file = attachmentFile.value;

  // Affiché tout de suite, confirmé quand le serveur répond.
  const temp = {
    id: `tmp-${Date.now()}`, pending: true, sender: auth.user?.id, body, created_at: new Date().toISOString(),
    is_automated: false, is_read: false, attachment_name: file?.name, attachment_type: file?.type?.startsWith("image/") ? "image" : file ? "document" : "",
    attachment_url: file && attachmentPreviewUrl.value ? attachmentPreviewUrl.value : null,
  };
  messages.value = [...messages.value, temp];
  if (text === null) newMessage.value = "";
  resizeComposer();
  scrollToBottom(true);
  sending.value = true;
  try {
    if (file) {
      const payload = new FormData();
      payload.append("conversation", activeConversationId.value);
      if (body) payload.append("body", body);
      payload.append("attachment", file);
      attachmentFile.value = null;
      await api.post("/messaging/messages/", payload);
      clearAttachment();
    } else {
      await api.post("/messaging/messages/", { conversation: activeConversationId.value, body });
    }
    const expectAssistant = conversation?.is_admin_support && !conversation.human_handoff && !isAdmin.value;
    messages.value = messages.value.filter((m) => m.id !== temp.id);
    await refreshMessages({ revealAssistant: expectAssistant });
    await loadConversations();
  } catch (e) {
    messages.value = messages.value.filter((m) => m.id !== temp.id);
    if (text === null) newMessage.value = body;
    toast.error(e?.response?.data?.detail || "Impossible d'envoyer ce message.");
  } finally {
    sending.value = false;
  }
}

function onComposerKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMessage();
  }
}

function resizeComposer() {
  nextTick(() => {
    const el = composerRef.value;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  });
}

// Suggestions affichées dans la conversation avec le support.
const QUICK_REPLIES = [
  "Je veux louer du matériel",
  "Acheter dans la boutique",
  "Où est ma facture ?",
  "Trouver un prestataire",
  "Parler à un conseiller",
];
const showQuickReplies = computed(() =>
  !isAdmin.value && activeConversation.value?.is_admin_support && !activeConversation.value.human_handoff && !sending.value
);

// --- Nouvelle conversation (admin) / support (autres comptes) --------------
async function loadAvailableUsers() {
  if (!isAdmin.value) return;
  try {
    const { data } = await api.get("/auth/users/");
    availableUsers.value = (data.results || data).filter((u) => u.id !== auth.user?.id);
  } catch (e) {
    // seuls les admins peuvent lister les comptes
  }
}

async function startConversation() {
  if (!selectedUserId.value) return;
  const { data } = await api.post("/messaging/conversations/", { participant_ids: [selectedUserId.value] });
  showNewConversation.value = false;
  selectedUserId.value = "";
  await loadConversations();
  await openConversation(conversations.value.find((c) => c.id === data.id) || data);
}

async function contactAdmin() {
  contactingAdmin.value = true;
  try {
    const { data } = await api.post("/messaging/conversations/contact-admin/");
    await loadConversations();
    await openConversation(conversations.value.find((c) => c.id === data.id) || data);
  } finally {
    contactingAdmin.value = false;
  }
}

// --- Rafraîchissement ---------------------------------------------------------
// Toutes les 4 s quand une conversation est ouverte et l'onglet visible,
// sinon toutes les 15 s : les nouveaux messages arrivent sans attendre.
let pollTimer = null;
function schedulePoll() {
  clearTimeout(pollTimer);
  const delay = document.hidden ? 30000 : activeConversationId.value ? 4000 : 15000;
  pollTimer = setTimeout(async () => {
    try {
      await loadConversations();
      if (activeConversationId.value && !sending.value) await refreshMessages();
    } catch (e) {
      // réseau momentanément indisponible : nouvel essai au prochain tour
    }
    schedulePoll();
  }, delay);
}

// Une notification arrive en temps réel (WebSocket ou push) : la liste et la
// conversation ouverte se mettent à jour tout de suite.
function onRealtimeNotification(event) {
  const link = event.detail?.link || "";
  if (!link.includes("messaging")) return;
  loadConversations()
    .then(() => {
      // Sur grand écran, sans conversation ouverte : on ouvre la plus récente.
      if (!activeConversationId.value && window.innerWidth > 900 && visibleConversations.value.length) {
        openConversation(visibleConversations.value[0]);
      }
    })
    .catch(() => {});
  if (activeConversationId.value && !sending.value) refreshMessages().catch(() => {});
}

function onVisibilityChange() {
  if (!document.hidden) {
    loadConversations().catch(() => {});
    if (activeConversationId.value) refreshMessages().catch(() => {});
  }
  schedulePoll();
}

watch(activeConversationId, schedulePoll);

onMounted(async () => {
  loading.value = true;
  try {
    await loadConversations();
    await loadAvailableUsers();
  } finally {
    loading.value = false;
  }

  const conversationId = Number(route.query.conversation);
  if (conversationId) {
    const target = conversations.value.find((c) => c.id === conversationId);
    if (target) await openConversation(target);
    router.replace({ query: {} });
  } else if (route.query.guided_tour === "1") {
    try {
      await contactAdmin();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Impossible d'ouvrir la messagerie pour le moment.");
    } finally {
      router.replace({ query: {} });
    }
  } else if (window.innerWidth > 900 && visibleConversations.value.length) {
    await openConversation(visibleConversations.value[0]);
  }

  document.addEventListener("visibilitychange", onVisibilityChange);
  window.addEventListener("ie:notification", onRealtimeNotification);
  schedulePoll();
});

// Notification touchée alors que la messagerie est déjà ouverte.
watch(
  () => route.query.conversation,
  async (value) => {
    const target = conversations.value.find((c) => c.id === Number(value));
    if (!value) return;
    if (!target) await loadConversations();
    const conversation = conversations.value.find((c) => c.id === Number(value));
    if (conversation) await openConversation(conversation);
    router.replace({ query: {} });
  },
);

onBeforeUnmount(() => {
  clearTimeout(pollTimer);
  document.removeEventListener("visibilitychange", onVisibilityChange);
  window.removeEventListener("ie:notification", onRealtimeNotification);
  clearAttachment();
});
</script>

<template>
  <div class="msg" :class="{ 'has-active': activeConversation }">
    <!-- Liste des conversations -->
    <aside class="msg-list">
      <header class="msg-list-head">
        <div>
          <h1>Messages</h1>
          <small v-if="totalUnread">{{ totalUnread }} non lu{{ totalUnread > 1 ? "s" : "" }}</small>
          <small v-else>Tout est lu</small>
        </div>
        <button v-if="isAdmin" type="button" class="msg-icon-btn" :class="{ on: showNewConversation }" aria-label="Nouvelle conversation" @click="showNewConversation = !showNewConversation">
          <i class="fa-solid" :class="showNewConversation ? 'fa-xmark' : 'fa-pen-to-square'"></i>
        </button>
      </header>

      <div v-if="showNewConversation" class="msg-new">
        <select v-model="selectedUserId" class="ie-select" aria-label="Destinataire">
          <option value="" disabled>Choisir un utilisateur…</option>
          <option v-for="u in availableUsers" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
        </select>
        <button type="button" class="ie-btn ie-btn-primary ie-btn-sm" :disabled="!selectedUserId" @click="startConversation">Démarrer</button>
      </div>

      <button v-if="!isAdmin && !hasSupportConversation && !loading" type="button" class="msg-support-cta" :disabled="contactingAdmin" @click="contactAdmin">
        <span><i class="fa-solid fa-headset"></i></span>
        <div><strong>Besoin d'aide ?</strong><small>Écrivez au support InnovEvent</small></div>
        <i class="fa-solid fa-chevron-right"></i>
      </button>

      <div class="msg-search">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="search" type="search" placeholder="Rechercher une conversation" aria-label="Rechercher une conversation" />
      </div>
      <div class="msg-filters" role="tablist">
        <button
          v-for="f in LIST_FILTERS" :key="f.value" type="button" role="tab" :aria-selected="listFilter === f.value"
          :class="{ active: listFilter === f.value }" @click="listFilter = f.value"
        >
          {{ f.label }}
          <span v-if="f.value === 'unread' && totalUnread">{{ totalUnread }}</span>
          <span v-if="f.value === 'waiting' && waitingCount" class="alert">{{ waitingCount }}</span>
        </button>
      </div>

      <div class="msg-items">
        <template v-if="loading">
          <div v-for="i in 5" :key="i" class="msg-item-skeleton"><span class="ie-skeleton"></span><div><span class="ie-skeleton"></span><span class="ie-skeleton"></span></div></div>
        </template>
        <template v-else>
          <button
            v-for="conv in visibleConversations" :key="conv.id" type="button" class="msg-item"
            :class="{ active: conv.id === activeConversationId, unread: conv.unread_count }"
            @click="openConversation(conv)"
          >
            <span class="msg-avatar" :class="{ support: conv.is_admin_support && !isAdmin }" :style="conv.is_admin_support && !isAdmin ? null : { background: avatarTone(others(conv)[0]?.id) }">
              <i v-if="conv.is_admin_support && !isAdmin" class="fa-solid fa-headset"></i>
              <template v-else>{{ initials(conversationTitle(conv)) }}</template>
              <b v-if="isOnline(conv)" class="msg-online"></b>
            </span>
            <span class="msg-item-body">
              <span class="msg-item-top">
                <strong>{{ conversationTitle(conv) }}</strong>
                <time>{{ listTime(conv.last_message?.created_at || conv.created_at) }}</time>
              </span>
              <span class="msg-item-bottom">
                <span class="msg-preview">{{ lastMessagePreview(conv) }}</span>
                <span v-if="conv.unread_count" class="msg-unread">{{ conv.unread_count }}</span>
              </span>
              <span v-if="isAdmin && conv.is_admin_support" class="msg-tags">
                <em>Support</em>
                <em v-if="needsReply(conv)" class="warn">Conseiller requis</em>
              </span>
            </span>
          </button>
          <div v-if="!visibleConversations.length" class="msg-list-empty">
            <i class="fa-regular fa-comments"></i>
            <p>{{ search || listFilter !== "all" ? "Aucune conversation ne correspond." : "Aucune conversation pour le moment." }}</p>
          </div>
        </template>
      </div>
    </aside>

    <!-- Conversation -->
    <section class="msg-thread">
      <template v-if="activeConversation">
        <header class="msg-thread-head">
          <button type="button" class="msg-back" aria-label="Retour aux conversations" @click="closeConversation">
            <i class="fa-solid fa-arrow-left"></i>
          </button>
          <span class="msg-avatar" :class="{ support: activeConversation.is_admin_support && !isAdmin }" :style="activeConversation.is_admin_support && !isAdmin ? null : { background: avatarTone(others(activeConversation)[0]?.id) }">
            <i v-if="activeConversation.is_admin_support && !isAdmin" class="fa-solid fa-headset"></i>
            <template v-else>{{ initials(conversationTitle(activeConversation)) }}</template>
            <b v-if="isOnline(activeConversation)" class="msg-online"></b>
          </span>
          <div class="msg-thread-title">
            <strong>{{ conversationTitle(activeConversation) }}</strong>
            <small>{{ conversationSubtitle(activeConversation) }}</small>
          </div>
          <span v-if="isAdmin && activeConversation.is_admin_support" class="msg-mode" :class="{ human: activeConversation.human_handoff }">
            <i class="fa-solid" :class="activeConversation.human_handoff ? 'fa-user-tie' : 'fa-robot'"></i>
            {{ activeConversation.human_handoff ? "Conseiller en charge" : "Assistant actif" }}
          </span>
        </header>

        <div ref="threadRef" class="msg-messages" @scroll.passive="onThreadScroll">
          <div v-if="messagesLoading" class="msg-loading"><span class="ie-skeleton"></span><span class="ie-skeleton mine"></span><span class="ie-skeleton"></span></div>

          <div v-else-if="!messages.length" class="msg-welcome">
            <span><i class="fa-solid" :class="activeConversation.is_admin_support ? 'fa-headset' : 'fa-comments'"></i></span>
            <strong>{{ activeConversation.is_admin_support && !isAdmin ? "Bienvenue au support InnovEvent" : "Démarrez la conversation" }}</strong>
            <p v-if="activeConversation.is_admin_support && !isAdmin">Posez votre question : notre assistant répond tout de suite, et un conseiller prend le relais si besoin.</p>
            <p v-else>Envoyez un premier message à {{ conversationTitle(activeConversation) }}.</p>
          </div>

          <template v-for="row in timeline" :key="row.key">
            <div v-if="row.type === 'day'" class="msg-day"><span>{{ row.label }}</span></div>
            <div
              v-else class="msg-row"
              :class="{ mine: isMine(row.msg), bot: row.msg.is_automated, first: row.first, pending: row.msg.pending }"
            >
              <span v-if="!isMine(row.msg)" class="msg-row-avatar">
                <template v-if="row.first">
                  <span v-if="row.msg.is_automated" class="msg-avatar small bot"><i class="fa-solid fa-robot"></i></span>
                  <span v-else class="msg-avatar small" :style="{ background: avatarTone(row.msg.sender) }">{{ initials(row.msg.sender_name) }}</span>
                </template>
              </span>
              <div class="msg-bubble-wrap">
                <span v-if="row.first && !isMine(row.msg)" class="msg-author">
                  {{ row.msg.is_automated ? "Assistant InnovEvent" : row.msg.sender_name }}
                  <em v-if="row.msg.is_automated">Auto</em>
                </span>
                <div class="msg-bubble">
                  <img
                    v-if="row.msg.attachment_type === 'image' && row.msg.attachment_url" :src="row.msg.attachment_url" :alt="row.msg.attachment_name"
                    class="msg-image" @click="openImageMessage(row.msg)"
                  />
                  <a
                    v-else-if="row.msg.attachment_url || row.msg.attachment_name" :href="row.msg.attachment_url || undefined" target="_blank" rel="noopener"
                    class="msg-doc"
                  >
                    <i :class="documentIcon(row.msg.attachment_content_type)"></i>
                    <span><strong>{{ row.msg.attachment_name }}</strong><small>{{ formatFileSize(row.msg.attachment_size) }}</small></span>
                    <i class="fa-solid fa-download"></i>
                  </a>
                  <p v-if="row.msg.body">{{ row.msg.body }}</p>
                  <span class="msg-meta">
                    {{ timeLabel(row.msg.created_at) }}
                    <template v-if="isMine(row.msg)">
                      <i v-if="row.msg.pending" class="fa-regular fa-clock" title="Envoi…"></i>
                      <i v-else-if="row.msg.is_read" class="fa-solid fa-check-double read" title="Lu"></i>
                      <i v-else class="fa-solid fa-check" title="Envoyé"></i>
                    </template>
                  </span>
                </div>
                <span v-if="isMine(row.msg) && row.msg.id === lastMineId && row.msg.is_read" class="msg-seen">Vu</span>
              </div>
            </div>
          </template>

          <div v-if="assistantTyping" class="msg-row bot first">
            <span class="msg-row-avatar"><span class="msg-avatar small bot"><i class="fa-solid fa-robot"></i></span></span>
            <div class="msg-bubble-wrap"><div class="msg-bubble msg-typing"><span></span><span></span><span></span></div></div>
          </div>
        </div>

        <button v-if="showJumpToLatest" type="button" class="msg-jump" @click="scrollToBottom(true)">
          <i class="fa-solid fa-arrow-down"></i> Nouveaux messages
        </button>

        <footer class="msg-composer">
          <div v-if="showQuickReplies" class="msg-quick">
            <button v-for="q in QUICK_REPLIES" :key="q" type="button" @click="sendMessage(q)">{{ q }}</button>
          </div>
          <div v-if="attachmentFile" class="msg-attachment">
            <img v-if="attachmentPreviewUrl" :src="attachmentPreviewUrl" alt="Aperçu" />
            <i v-else :class="documentIcon(attachmentFile.type)"></i>
            <span>{{ attachmentFile.name }} <small>{{ formatFileSize(attachmentFile.size) }}</small></span>
            <button type="button" aria-label="Retirer la pièce jointe" @click="clearAttachment"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <form class="msg-input" @submit.prevent="sendMessage()">
            <input ref="fileInput" type="file" hidden @change="onFileSelected" />
            <button type="button" class="msg-icon-btn" aria-label="Joindre un fichier" @click="triggerFilePicker"><i class="fa-solid fa-paperclip"></i></button>
            <textarea
              ref="composerRef" v-model="newMessage" rows="1" placeholder="Écrire un message…" aria-label="Message"
              @keydown="onComposerKeydown" @input="resizeComposer"
            ></textarea>
            <button type="submit" class="msg-send" :disabled="sending || (!newMessage.trim() && !attachmentFile)" aria-label="Envoyer">
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </form>
          <small class="msg-hint">Entrée pour envoyer · Maj + Entrée pour aller à la ligne</small>
        </footer>
      </template>

      <div v-else class="msg-empty">
        <span><i class="fa-regular fa-comments"></i></span>
        <strong>Vos conversations</strong>
        <p>Sélectionnez une conversation pour afficher les messages.</p>
        <button v-if="!isAdmin" type="button" class="ie-btn ie-btn-primary" :disabled="contactingAdmin" @click="contactAdmin">
          <i class="fa-solid fa-headset"></i> {{ contactingAdmin ? "Connexion…" : "Écrire au support" }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.msg {
  --msg-height: calc(100dvh - 68px - 48px);
  display: grid; grid-template-columns: 340px minmax(0, 1fr); height: var(--msg-height); min-height: 460px; overflow: hidden;
  border: 1px solid var(--ie-line); border-radius: 18px; background: #fff; box-shadow: var(--ie-shadow-sm);
}

/* Liste */
.msg-list { display: flex; flex-direction: column; min-height: 0; border-right: 1px solid var(--ie-line); background: #fbfcfd; }
.msg-list-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 18px 18px 12px; }
.msg-list-head h1 { margin: 0; color: var(--ie-navy); font-size: 21px; }
.msg-list-head small { color: var(--ie-muted); font-size: 12px; }
.msg-icon-btn {
  display: grid; place-items: center; width: 38px; height: 38px; flex: 0 0 38px; border: 1px solid var(--ie-line); border-radius: 10px;
  background: #fff; color: var(--ie-navy); font-size: 15px; cursor: pointer;
}
.msg-icon-btn:hover, .msg-icon-btn.on { border-color: var(--ie-navy); background: var(--ie-navy-soft); }
.msg-new { display: flex; gap: 8px; padding: 0 18px 12px; }
.msg-new .ie-select { flex: 1; min-width: 0; }
.msg-support-cta {
  display: flex; align-items: center; gap: 12px; margin: 0 18px 12px; padding: 12px; border: 1px solid #f0d4d5; border-radius: 12px;
  background: var(--ie-red-soft); text-align: left; cursor: pointer; font-family: inherit;
}
.msg-support-cta > span { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: var(--ie-red); color: #fff; }
.msg-support-cta div { flex: 1; display: flex; flex-direction: column; }
.msg-support-cta strong { color: var(--ie-navy); font-size: 13.5px; }
.msg-support-cta small { color: #7a4a4c; font-size: 12px; }
.msg-support-cta > i { color: var(--ie-red); font-size: 12px; }
.msg-search { position: relative; margin: 0 18px; }
.msg-search i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--ie-muted); font-size: 13px; }
.msg-search input { width: 100%; height: 38px; padding: 0 12px 0 34px; border: 1px solid var(--ie-line); border-radius: 10px; background: #fff; font-size: 13px; font-family: inherit; }
.msg-search input:focus { outline: none; border-color: var(--ie-navy); }
.msg-filters { display: flex; gap: 6px; padding: 12px 18px; overflow-x: auto; scrollbar-width: none; border-bottom: 1px solid var(--ie-line); }
.msg-filters button {
  display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; padding: 6px 12px; border: 1px solid var(--ie-line); border-radius: 999px;
  background: #fff; color: #5d6771; font-size: 12.5px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.msg-filters button.active { background: var(--ie-navy); border-color: var(--ie-navy); color: #fff; }
.msg-filters button span { min-width: 18px; padding: 0 5px; border-radius: 999px; background: #e7eaee; color: var(--ie-navy); font-size: 11px; }
.msg-filters button span.alert { background: var(--ie-red); color: #fff; }
.msg-filters button.active span { background: #ffffff2b; color: #fff; }
.msg-items { flex: 1; min-height: 0; overflow-y: auto; padding: 6px 8px; }
.msg-item {
  display: flex; align-items: center; gap: 12px; width: 100%; padding: 11px 10px; border: 0; border-radius: 12px; background: none;
  text-align: left; cursor: pointer; font-family: inherit;
}
.msg-item:hover { background: #f1f3f6; }
.msg-item.active { background: #fff; box-shadow: 0 2px 10px #18283b14, inset 3px 0 0 var(--ie-red); }
.msg-item-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.msg-item-top, .msg-item-bottom { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.msg-item-top strong { overflow: hidden; color: var(--ie-navy); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.msg-item-top time { flex-shrink: 0; color: var(--ie-muted); font-size: 11.5px; }
.msg-preview { overflow: hidden; color: var(--ie-muted); font-size: 12.5px; text-overflow: ellipsis; white-space: nowrap; }
.msg-item.unread .msg-preview { color: var(--ie-ink); font-weight: 600; }
.msg-item.unread time { color: var(--ie-red); font-weight: 700; }
.msg-unread { display: grid; place-items: center; flex-shrink: 0; min-width: 20px; height: 20px; padding: 0 6px; border-radius: 999px; background: var(--ie-red); color: #fff; font-size: 11px; font-weight: 800; }
.msg-tags { display: flex; gap: 4px; }
.msg-tags em { padding: 1px 7px; border-radius: 6px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 10.5px; font-weight: 700; font-style: normal; }
.msg-tags em.warn { background: var(--ie-warning-soft); color: var(--ie-warning); }
.msg-list-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 40px 20px; color: var(--ie-muted); text-align: center; }
.msg-list-empty i { font-size: 28px; opacity: 0.5; }
.msg-list-empty p { margin: 0; font-size: 13px; }
.msg-item-skeleton { display: flex; gap: 12px; padding: 11px 10px; }
.msg-item-skeleton > .ie-skeleton { width: 44px; height: 44px; border-radius: 50%; flex-shrink: 0; }
.msg-item-skeleton div { flex: 1; display: flex; flex-direction: column; gap: 6px; justify-content: center; }
.msg-item-skeleton div .ie-skeleton { height: 10px; border-radius: 6px; }
.msg-item-skeleton div .ie-skeleton:last-child { width: 70%; }

/* Avatars */
.msg-avatar {
  position: relative; display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px; border-radius: 50%;
  background: var(--ie-navy); color: #fff; font-size: 14px; font-weight: 800; letter-spacing: 0.02em;
}
.msg-avatar.support { background: var(--ie-red); font-size: 17px; }
.msg-avatar.small { width: 30px; height: 30px; flex-basis: 30px; font-size: 11px; }
.msg-avatar.bot { background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 13px; }
.msg-online { position: absolute; right: 0; bottom: 1px; width: 12px; height: 12px; border: 2px solid #fff; border-radius: 50%; background: #22a05b; }

/* Conversation */
.msg-thread { position: relative; display: flex; flex-direction: column; min-width: 0; min-height: 0; background: #fff; }
.msg-thread-head { display: flex; align-items: center; gap: 12px; padding: 12px 18px; border-bottom: 1px solid var(--ie-line); background: #fff; }
.msg-back { display: none; }
.msg-thread-title { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.msg-thread-title strong { overflow: hidden; color: var(--ie-navy); font-size: 15.5px; text-overflow: ellipsis; white-space: nowrap; }
.msg-thread-title small { color: var(--ie-muted); font-size: 12px; }
.msg-mode { display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; padding: 5px 10px; border-radius: 999px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 12px; font-weight: 700; }
.msg-mode.human { background: var(--ie-warning-soft); color: var(--ie-warning); }

.msg-messages {
  flex: 1; min-height: 0; overflow-y: auto; padding: 18px 22px 10px; display: flex; flex-direction: column; gap: 2px;
  background: linear-gradient(#f7f8fa, #f7f8fa);
}
.msg-loading { display: flex; flex-direction: column; gap: 10px; }
.msg-loading .ie-skeleton { width: 55%; height: 44px; border-radius: 14px; }
.msg-loading .ie-skeleton.mine { align-self: flex-end; width: 40%; }
.msg-welcome { display: flex; flex-direction: column; align-items: center; gap: 8px; max-width: 360px; margin: auto; padding: 24px; text-align: center; }
.msg-welcome > span { display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: var(--ie-red-soft); color: var(--ie-red); font-size: 24px; }
.msg-welcome strong { color: var(--ie-navy); font-size: 16px; }
.msg-welcome p { margin: 0; color: var(--ie-muted); font-size: 13px; line-height: 1.5; }

.msg-day { display: flex; justify-content: center; margin: 14px 0 8px; }
.msg-day span { padding: 4px 12px; border-radius: 999px; background: #e9ecf0; color: #5d6771; font-size: 11.5px; font-weight: 700; text-transform: capitalize; }
.msg-row { display: flex; align-items: flex-end; gap: 8px; max-width: 78%; }
.msg-row.first { margin-top: 8px; }
.msg-row.mine { align-self: flex-end; flex-direction: row-reverse; }
.msg-row-avatar { width: 30px; flex: 0 0 30px; }
.msg-bubble-wrap { display: flex; flex-direction: column; min-width: 0; }
.msg-row.mine .msg-bubble-wrap { align-items: flex-end; }
.msg-author { display: inline-flex; align-items: center; gap: 6px; margin: 0 0 3px 4px; color: var(--ie-muted); font-size: 11.5px; font-weight: 700; }
.msg-author em { padding: 0 5px; border-radius: 4px; background: var(--ie-navy-soft); color: var(--ie-navy); font-size: 9.5px; font-style: normal; text-transform: uppercase; }
.msg-bubble {
  position: relative; padding: 8px 12px 6px; border-radius: 16px; background: #fff; color: var(--ie-ink); font-size: 14px; line-height: 1.45;
  box-shadow: 0 1px 2px #18283b14; overflow-wrap: anywhere;
}
.msg-row:not(.mine) .msg-bubble { border-bottom-left-radius: 6px; }
.msg-row.mine .msg-bubble { border-bottom-right-radius: 6px; background: var(--ie-navy); color: #fff; }
.msg-row.bot .msg-bubble { background: #fff; border: 1px solid #dfe5ec; }
.msg-row.pending .msg-bubble { opacity: 0.7; }
.msg-bubble p { margin: 0; white-space: pre-line; }
.msg-meta { display: flex; align-items: center; justify-content: flex-end; gap: 4px; margin-top: 2px; color: var(--ie-muted); font-size: 10.5px; }
.msg-row.mine .msg-meta { color: #c6d1dc; }
.msg-meta .read { color: #7fd1a3; }
.msg-seen { margin: 3px 4px 0; color: var(--ie-muted); font-size: 11px; }
.msg-image { display: block; max-width: 240px; max-height: 240px; margin: 2px 0 4px; border-radius: 10px; object-fit: cover; cursor: zoom-in; }
.msg-doc {
  display: flex; align-items: center; gap: 10px; min-width: 200px; margin: 2px 0 4px; padding: 8px 10px; border-radius: 10px;
  background: #00000010; color: inherit; text-decoration: none;
}
.msg-doc > i:first-child { color: var(--ie-red); font-size: 22px; }
.msg-row.mine .msg-doc > i:first-child { color: #fff; }
.msg-doc span { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.msg-doc strong { overflow: hidden; font-size: 12.5px; text-overflow: ellipsis; white-space: nowrap; }
.msg-doc small { opacity: 0.75; font-size: 11px; }
.msg-typing { display: inline-flex; gap: 4px; padding: 12px 14px; }
.msg-typing span { width: 7px; height: 7px; border-radius: 50%; background: #9aa3ac; animation: msg-dot 1.2s infinite ease-in-out; }
.msg-typing span:nth-child(2) { animation-delay: 0.15s; }
.msg-typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes msg-dot { 0%, 80%, 100% { transform: translateY(0); opacity: 0.5; } 40% { transform: translateY(-4px); opacity: 1; } }
.msg-jump {
  position: absolute; left: 50%; bottom: 132px; z-index: 2; display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px;
  border: 0; border-radius: 999px; background: var(--ie-navy); color: #fff; font-size: 12.5px; font-weight: 700; transform: translateX(-50%);
  box-shadow: 0 6px 16px #0003; cursor: pointer; font-family: inherit;
}

.msg-composer { padding: 10px 16px 12px; border-top: 1px solid var(--ie-line); background: #fff; }
.msg-quick { display: flex; gap: 6px; margin-bottom: 10px; overflow-x: auto; scrollbar-width: none; }
.msg-quick button {
  flex-shrink: 0; padding: 7px 12px; border: 1px solid #d5dde6; border-radius: 999px; background: #fff; color: var(--ie-navy);
  font-size: 12.5px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.msg-quick button:hover { border-color: var(--ie-navy); background: var(--ie-navy-soft); }
.msg-attachment { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; padding: 6px 8px; border: 1px solid var(--ie-line); border-radius: 10px; background: #fafbfc; }
.msg-attachment img { width: 44px; height: 44px; border-radius: 6px; object-fit: cover; }
.msg-attachment > i { color: var(--ie-red); font-size: 20px; }
.msg-attachment span { flex: 1; min-width: 0; overflow: hidden; color: var(--ie-navy); font-size: 12.5px; text-overflow: ellipsis; white-space: nowrap; }
.msg-attachment small { color: var(--ie-muted); }
.msg-attachment button { width: 26px; height: 26px; border: 0; border-radius: 50%; background: var(--ie-navy); color: #fff; font-size: 11px; cursor: pointer; }
.msg-input { display: flex; align-items: flex-end; gap: 8px; }
.msg-input textarea {
  flex: 1; min-width: 0; max-height: 140px; padding: 10px 14px; border: 1px solid var(--ie-line); border-radius: 20px; resize: none;
  background: #f7f8fa; color: var(--ie-ink); font-size: 14px; line-height: 1.4; font-family: inherit;
}
.msg-input textarea:focus { outline: none; border-color: var(--ie-navy); background: #fff; }
.msg-send { display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; border: 0; border-radius: 50%; background: var(--ie-red); color: #fff; font-size: 15px; cursor: pointer; }
.msg-send:disabled { background: #d9dde2; cursor: default; }
.msg-hint { display: block; margin-top: 6px; color: #a0a8b1; font-size: 11px; text-align: center; }

.msg-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; height: 100%; padding: 30px; text-align: center; background: #f7f8fa; }
.msg-empty > span { display: grid; place-items: center; width: 72px; height: 72px; border-radius: 50%; background: #fff; color: var(--ie-navy); font-size: 28px; box-shadow: var(--ie-shadow-sm); }
.msg-empty strong { color: var(--ie-navy); font-size: 17px; }
.msg-empty p { margin: 0 0 8px; color: var(--ie-muted); font-size: 13px; }

@media (max-width: 900px) {
  /* Mobile : liste OU conversation, en plein écran (au-dessus de la barre d'onglets). */
  /* 68 px d'en-tête, 14 px de marge haute, 84 px réservés à la barre d'onglets. */
  .msg { --msg-height: calc(100dvh - 166px - env(safe-area-inset-bottom)); display: block; border-radius: 14px; }
  .msg-list, .msg-thread { height: 100%; }
  .msg-list { border-right: 0; }
  .msg-thread { display: none; }
  .msg.has-active .msg-list { display: none; }
  .msg.has-active .msg-thread { display: flex; }
  .msg-back { display: grid; place-items: center; width: 36px; height: 36px; flex: 0 0 36px; border: 0; border-radius: 50%; background: var(--ie-navy-soft); color: var(--ie-navy); cursor: pointer; }
  .msg-thread-head { padding: 10px 12px; gap: 10px; }
  .msg-mode { display: none; }
  .msg-messages { padding: 12px 12px 8px; }
  .msg-row { max-width: 88%; }
  .msg-composer { padding: 8px 10px 10px; }
  .msg-hint { display: none; }
  .msg-jump { bottom: 96px; }
}
@media (prefers-reduced-motion: reduce) {
  .msg-typing span { animation: none; }
}
</style>
