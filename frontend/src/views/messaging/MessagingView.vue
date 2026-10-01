<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useLightboxStore } from "../../stores/lightbox";
import { useToastStore } from "../../stores/toast";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const lightbox = useLightboxStore();
const toast = useToastStore();
const contactingAdmin = ref(false);
const conversations = ref([]);
const messages = ref([]);
const activeConversationId = ref(null);
const newMessage = ref("");
const loading = ref(true);
const showNewConversation = ref(false);
const availableUsers = ref([]);

// Pièce jointe sélectionnée avant envoi (photo, document...) — comme sur
// WhatsApp, l'aperçu s'affiche au-dessus du champ de saisie avant de valider.
const attachmentFile = ref(null);
const attachmentPreviewUrl = ref(null);
const fileInput = ref(null);
const sending = ref(false);

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
const selectedUserId = ref("");
let pollHandle = null;

const activeConversation = computed(() =>
  conversations.value.find((c) => c.id === activeConversationId.value)
);

function otherParticipantList(conversation) {
  return conversation.participants.filter((p) => p.id !== auth.user?.id);
}

function otherParticipants(conversation) {
  const others = otherParticipantList(conversation);
  return others.map((p) => p.name).join(", ") || "Moi";
}

function isConversationOnline(conversation) {
  return otherParticipantList(conversation).some((p) => p.is_online);
}

async function loadConversations() {
  const { data } = await api.get("/messaging/conversations/");
  conversations.value = data.results || data;
}

async function openConversation(conversation) {
  activeConversationId.value = conversation.id;
  clearAttachment();
  await loadMessages();
  await api.post("/messaging/messages/mark-read/", { conversation: conversation.id });
  await loadConversations();
}

async function loadMessages() {
  if (!activeConversationId.value) return;
  const { data } = await api.get("/messaging/messages/", { params: { conversation: activeConversationId.value } });
  messages.value = data.results || data;
}

async function sendMessage() {
  const body = newMessage.value.trim();
  if (!activeConversationId.value || (!body && !attachmentFile.value)) return;
  sending.value = true;
  try {
    if (attachmentFile.value) {
      const payload = new FormData();
      payload.append("conversation", activeConversationId.value);
      if (body) payload.append("body", body);
      payload.append("attachment", attachmentFile.value);
      await api.post("/messaging/messages/", payload);
      clearAttachment();
    } else {
      await api.post("/messaging/messages/", { conversation: activeConversationId.value, body });
    }
    newMessage.value = "";
    await loadMessages();
    await loadConversations();
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d'envoyer ce message.");
  } finally {
    sending.value = false;
  }
}

async function loadAvailableUsers() {
  if (auth.role !== "admin") return;
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
  await openConversation(data);
}

async function contactAdmin() {
  contactingAdmin.value = true;
  try {
    const { data } = await api.post("/messaging/conversations/contact-admin/");
    await loadConversations();
    await openConversation(data);
  } finally {
    contactingAdmin.value = false;
  }
}

onMounted(async () => {
  loading.value = true;
  await loadConversations();
  await loadAvailableUsers();
  loading.value = false;

  const conversationId = Number(route.query.conversation);
  if (conversationId) {
    const target = conversations.value.find((c) => c.id === conversationId);
    if (target) await openConversation(target);
    router.replace({ query: {} });
  }

  pollHandle = setInterval(async () => {
    await loadConversations();
    if (activeConversationId.value) await loadMessages();
  }, 10000);
});

onBeforeUnmount(() => {
  if (pollHandle) clearInterval(pollHandle);
});
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-comments" style="color: var(--ie-red); margin-right: 8px;"></i>Messagerie</h1>
        <p class="ie-page-subtitle">Échangez avec les autres utilisateurs de la plateforme.</p>
      </div>
      <div class="ie-page-header-actions">
        <button v-if="auth.role === 'admin'" class="ie-btn ie-btn-primary" @click="showNewConversation = !showNewConversation">
          <i class="fa-solid" :class="showNewConversation ? 'fa-xmark' : 'fa-plus'"></i> {{ showNewConversation ? "Annuler" : "Nouvelle conversation" }}
        </button>
        <button v-else class="ie-btn ie-btn-primary" :disabled="contactingAdmin" @click="contactAdmin">
          <i class="fa-solid fa-headset"></i> {{ contactingAdmin ? "Connexion…" : "Contacter l'administration" }}
        </button>
      </div>
    </div>

    <div v-if="showNewConversation" class="ie-card" style="padding: 16px; margin-bottom: 16px; display:flex; gap:10px; align-items:center;">
      <select v-model="selectedUserId" class="ie-select" style="max-width: 320px;">
        <option value="" disabled>Choisir un utilisateur</option>
        <option v-for="u in availableUsers" :key="u.id" :value="u.id">{{ u.first_name }} {{ u.last_name }} ({{ u.username }})</option>
      </select>
      <button class="ie-btn ie-btn-secondary" @click="startConversation">Démarrer</button>
    </div>

    <div class="ie-messaging-layout ie-card" :class="{ 'has-active-conversation': activeConversation }">
      <aside class="ie-conversation-list">
        <div v-if="loading" class="ie-skeleton-table">
          <div class="ie-skeleton ie-skeleton-row" v-for="i in 4" :key="i" style="height: 44px;"></div>
        </div>
        <template v-if="!loading">
          <button
            v-for="conv in conversations"
            :key="conv.id"
            class="ie-conversation-item"
            :class="{ active: conv.id === activeConversationId }"
            @click="openConversation(conv)"
          >
            <div class="ie-conversation-name">
              <span class="ie-online-dot" :class="{ online: isConversationOnline(conv) }"></span>
              {{ otherParticipants(conv) }}
            </div>
            <div class="ie-conversation-preview">
              {{ conv.last_message?.body
                || (conv.last_message?.attachment_type === "image" ? "📷 Photo"
                    : conv.last_message?.attachment_name ? `📎 ${conv.last_message.attachment_name}`
                    : "Aucun message") }}
            </div>
            <span v-if="conv.unread_count" class="ie-nav-badge">{{ conv.unread_count }}</span>
          </button>
          <EmptyState v-if="!conversations.length" icon="fa-solid fa-comments" text="Aucune conversation." />
        </template>
      </aside>

      <section class="ie-thread">
        <template v-if="activeConversation">
          <div class="ie-thread-header">
            <button type="button" class="mobile-conversation-back" @click="activeConversationId = null" aria-label="Retour aux conversations">
              <i class="fa-solid fa-arrow-left"></i>
            </button>
            <span class="ie-online-dot" :class="{ online: isConversationOnline(activeConversation) }"></span>
            {{ otherParticipants(activeConversation) }}
          </div>
          <div class="ie-thread-messages">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="ie-message-bubble"
              :class="{ mine: msg.sender === auth.user?.id }"
            >
              <div class="ie-message-sender">{{ msg.sender_name }}</div>

              <img
                v-if="msg.attachment_type === 'image'" :src="msg.attachment_url" :alt="msg.attachment_name"
                class="ie-message-image" @click="openImageMessage(msg)"
              />
              <a
                v-else-if="msg.attachment_url" :href="msg.attachment_url" target="_blank" rel="noopener"
                class="ie-message-document"
              >
                <i :class="documentIcon(msg.attachment_content_type)"></i>
                <div class="ie-message-document-info">
                  <span class="ie-message-document-name">{{ msg.attachment_name }}</span>
                  <span class="ie-message-document-size">{{ formatFileSize(msg.attachment_size) }}</span>
                </div>
                <i class="fa-solid fa-download ie-message-document-download"></i>
              </a>

              <div v-if="msg.body">{{ msg.body }}</div>
            </div>
          </div>

          <div v-if="attachmentFile" class="ie-attachment-preview">
            <img v-if="attachmentPreviewUrl" :src="attachmentPreviewUrl" alt="Aperçu" />
            <div v-else class="ie-attachment-preview-doc">
              <i :class="documentIcon(attachmentFile.type)"></i>
              <span>{{ attachmentFile.name }}</span>
            </div>
            <button type="button" class="ie-attachment-preview-remove" @click="clearAttachment" aria-label="Retirer">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <form class="ie-thread-input" @submit.prevent="sendMessage">
            <input ref="fileInput" type="file" hidden @change="onFileSelected" />
            <button type="button" class="ie-thread-attach-btn" @click="triggerFilePicker" aria-label="Joindre un fichier">
              <i class="fa-solid fa-paperclip"></i>
            </button>
            <input v-model="newMessage" class="ie-input" placeholder="Écrire un message…" />
            <button class="ie-btn ie-btn-primary" type="submit" :disabled="sending || (!newMessage.trim() && !attachmentFile)">
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </form>
        </template>
        <div v-else class="ie-empty-state" style="margin: auto;">Sélectionnez une conversation.</div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ie-page-header { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-bottom: 20px; }
.ie-messaging-layout { display: grid; grid-template-columns: minmax(220px, 280px) minmax(0, 1fr); height: min(560px, calc(100dvh - 220px)); min-height: 420px; overflow: hidden; }
.ie-conversation-list { border-right: 1px solid var(--ie-line); overflow-y: auto; }
.ie-conversation-item {
  display: block; width: 100%; text-align: left; padding: 14px 16px;
  border: 0; border-bottom: 1px solid var(--ie-line); background: #fff; cursor: pointer; position: relative;
}
.ie-conversation-item:hover, .ie-conversation-item.active { background: var(--ie-red-soft); }
.ie-conversation-name { font-weight: 700; font-size: 13.5px; color: var(--ie-navy); display: flex; align-items: center; gap: 6px; }
.ie-online-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 999px;
  background: #c7cbd1; flex-shrink: 0;
}
.ie-online-dot.online { background: var(--ie-success); box-shadow: 0 0 0 3px var(--ie-success-soft); }
.ie-conversation-preview { font-size: 12px; color: var(--ie-muted); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ie-nav-badge {
  position: absolute; top: 12px; right: 12px; background: var(--ie-red); color: #fff;
  font-size: 11px; font-weight: 800; border-radius: 999px; min-width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center; padding: 0 5px;
}
.ie-thread { display: flex; flex-direction: column; }
.ie-thread-header { display: flex; align-items: center; gap: 8px; padding: 14px 20px; border-bottom: 1px solid var(--ie-line); font-weight: 700; color: var(--ie-navy); }
.mobile-conversation-back { display: none; }
.ie-thread-messages { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }
.ie-message-bubble { max-width: 70%; background: #eef0f2; border-radius: 12px; padding: 8px 12px; font-size: 13.5px; }
.ie-message-bubble.mine { align-self: flex-end; background: var(--ie-red-soft); }
.ie-message-sender { font-size: 11px; font-weight: 700; color: var(--ie-muted); margin-bottom: 2px; }
.ie-thread-input { display: flex; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--ie-line); }
.ie-thread-input .ie-input { flex: 1; }
.ie-thread-attach-btn {
  width: 38px; height: 38px; border-radius: 50%; border: 0; background: var(--ie-navy-soft); color: var(--ie-navy);
  cursor: pointer; font-size: 15px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ie-thread-attach-btn:hover { background: var(--ie-red-soft); color: var(--ie-red); }

.ie-message-image { max-width: 220px; max-height: 220px; border-radius: 8px; display: block; cursor: pointer; margin-bottom: 4px; object-fit: cover; }
.ie-message-document {
  display: flex; align-items: center; gap: 10px; background: #fff; border: 1px solid var(--ie-line);
  border-radius: 8px; padding: 8px 10px; text-decoration: none; color: inherit; margin-bottom: 4px; min-width: 180px;
}
.ie-message-document i:first-child { font-size: 22px; color: var(--ie-red); flex-shrink: 0; }
.ie-message-document-info { display: flex; flex-direction: column; overflow: hidden; }
.ie-message-document-name { font-size: 12.5px; font-weight: 600; color: var(--ie-navy); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ie-message-document-size { font-size: 10.5px; color: var(--ie-muted); }
.ie-message-document-download { margin-left: auto; color: var(--ie-muted); flex-shrink: 0; }

.ie-attachment-preview {
  position: relative; display: inline-flex; align-items: center; margin: 0 20px 10px; padding: 6px;
  background: #fafbfc; border: 1px solid var(--ie-line); border-radius: 10px; width: fit-content;
}
.ie-attachment-preview img { height: 64px; width: 64px; object-fit: cover; border-radius: 6px; }
.ie-attachment-preview-doc { display: flex; align-items: center; gap: 8px; padding: 6px 10px; font-size: 12.5px; color: var(--ie-navy); }
.ie-attachment-preview-doc i { font-size: 20px; color: var(--ie-red); }
.ie-attachment-preview-remove {
  position: absolute; top: -6px; right: -6px; width: 20px; height: 20px; border-radius: 50%; border: 0;
  background: var(--ie-navy); color: #fff; font-size: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
@media (max-width: 760px) {
  .ie-page-header { align-items: flex-start; flex-direction: column; }
  .ie-page-header-actions { width: 100%; }
  .ie-page-header-actions .ie-btn { width: 100%; justify-content: center; }
  .ie-messaging-layout { display: block; height: min(68dvh, 620px); min-height: 420px; }
  .ie-conversation-list { height: 100%; border-right: 0; }
  .ie-thread { display: none; height: 100%; }
  .ie-messaging-layout.has-active-conversation .ie-conversation-list { display: none; }
  .ie-messaging-layout.has-active-conversation .ie-thread { display: flex; }
  .mobile-conversation-back { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border: 0; border-radius: 50%; background: var(--ie-navy-soft); color: var(--ie-navy); }
  .ie-thread-header { padding: 10px 12px; }
  .ie-thread-messages { padding: 12px; }
  .ie-message-bubble { max-width: 88%; overflow-wrap: anywhere; }
  .ie-thread-input { gap: 7px; padding: 10px; }
  .ie-thread-input .ie-input { min-width: 0; }
  .ie-thread-input .ie-btn { padding: 9px 12px; }
  .ie-message-document { min-width: 0; max-width: 100%; }
}
@media (max-width: 420px) {
  .ie-messaging-layout { min-height: 380px; }
  .ie-conversation-item { padding: 12px; }
  .ie-thread-input .ie-btn { padding: 9px 10px; }
}
</style>
