<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../services/api";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const notifications = ref([]);
const open = ref(false);
const live = ref(false); // true dès que le flux temps réel (WebSocket) est connecté
let pollHandle = null;
let socket = null;
let reconnectTimer = null;
let permissionAsked = false;

const unreadCount = () => notifications.value.filter((n) => !n.is_read).length;

async function loadNotifications() {
  try {
    const { data } = await api.get("/notifications/");
    notifications.value = data.results || data;
  } catch (e) {
    // silencieux : la cloche ne doit pas bloquer le reste de l'interface
  }
}

function wsUrl() {
  const token = auth.accessToken;
  if (!token) return null;
  const apiBase = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  // Avec /api/v1, le WebSocket doit se raccrocher au domaine courant ;
  // WebSocket n'accepte pas une URL relative seule.
  const origin = apiBase.startsWith("/")
    ? window.location.origin
    : apiBase.replace(/\/api\/v1\/?$/, "");
  const wsOrigin = origin.replace(/^http/, "ws");
  return `${wsOrigin}/ws/notifications/?token=${encodeURIComponent(token)}`;
}

function connectRealtime() {
  const url = wsUrl();
  if (!url) return;
  socket = new WebSocket(url);

  socket.onopen = () => { live.value = true; };

  socket.onmessage = (event) => {
    try {
      const notification = JSON.parse(event.data);
      if (!notifications.value.some((n) => n.id === notification.id)) {
        notifications.value.unshift(notification);
      }
      notifyBrowser(notification);
    } catch (e) {
      // ignore un message mal formé
    }
  };

  socket.onclose = () => {
    live.value = false;
    socket = null;
    // Reconnexion automatique (ex: réseau coupé, backend redémarré) tant que le
    // composant est monté et l'utilisateur toujours connecté.
    reconnectTimer = setTimeout(() => {
      if (auth.accessToken) connectRealtime();
    }, 4000);
  };

  socket.onerror = () => socket?.close();
}

function notifyBrowser(notification) {
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  new Notification(notification.title || "InnovEvent", {
    body: notification.message || "",
    icon: "/favicon.png",
  });
}

function ensureNotificationPermission() {
  if (permissionAsked || typeof Notification === "undefined") return;
  permissionAsked = true;
  if (Notification.permission === "default") Notification.requestPermission();
}

async function toggle() {
  open.value = !open.value;
  if (open.value) ensureNotificationPermission();
}

async function openNotification(notification) {
  if (!notification.is_read) {
    await api.post(`/notifications/${notification.id}/read/`);
    notification.is_read = true;
  }
  open.value = false;
  if (notification.link) router.push(notification.link);
}

async function markAllRead() {
  await api.post("/notifications/read-all/");
  notifications.value.forEach((n) => (n.is_read = true));
}

function closeOnOutsideClick(e) {
  if (!e.target.closest(".ie-bell-wrap")) open.value = false;
}

onMounted(() => {
  loadNotifications();
  if (auth.accessToken) connectRealtime();
  // Filet de sécurité si le WebSocket est indisponible (proxy, réseau restrictif...) :
  // rafraîchissement périodique bien plus espacé, le temps réel étant assuré par la WS.
  pollHandle = setInterval(loadNotifications, 60000);
  document.addEventListener("click", closeOnOutsideClick);
});
onBeforeUnmount(() => {
  if (pollHandle) clearInterval(pollHandle);
  if (reconnectTimer) clearTimeout(reconnectTimer);
  if (socket) { socket.onclose = null; socket.close(); }
  document.removeEventListener("click", closeOnOutsideClick);
});
</script>

<template>
  <div class="ie-bell-wrap">
    <button class="ie-bell-btn" @click.stop="toggle" :title="live ? 'Notifications en temps réel actives' : 'Connexion au temps réel…'">
      <i class="fa-solid fa-bell"></i>
      <span class="ie-bell-live-dot" :class="{ 'is-live': live }"></span>
      <span v-if="unreadCount()" class="ie-bell-badge">{{ unreadCount() }}</span>
    </button>
    <div v-if="open" class="ie-bell-panel">
      <div class="ie-bell-header">
        <strong>Notifications</strong>
        <button class="ie-bell-markall" @click="markAllRead">Tout marquer comme lu</button>
      </div>
      <div class="ie-bell-list">
        <button
          v-for="n in notifications"
          :key="n.id"
          class="ie-bell-item"
          :class="{ unread: !n.is_read }"
          @click="openNotification(n)"
        >
          <div class="ie-bell-title">{{ n.title }}</div>
          <div class="ie-bell-message">{{ n.message }}</div>
          <div class="ie-bell-date">{{ new Date(n.created_at).toLocaleString('fr-FR') }}</div>
        </button>
        <div v-if="!notifications.length" class="ie-bell-empty">Aucune notification.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-bell-wrap { position: relative; }
.ie-bell-btn {
  position: relative; background: #eef0f2; border: 0; border-radius: 8px;
  width: 36px; height: 36px; display: grid; place-items: center; cursor: pointer; color: var(--ie-navy);
}
.ie-bell-badge {
  position: absolute; top: -4px; right: -4px; background: var(--ie-red); color: #fff;
  font-size: 10px; font-weight: 800; border-radius: 999px; min-width: 16px; height: 16px;
  display: inline-flex; align-items: center; justify-content: center; padding: 0 4px;
}
.ie-bell-live-dot {
  position: absolute; bottom: 5px; right: 5px; width: 7px; height: 7px; border-radius: 50%;
  background: #c7cbd1; border: 1.5px solid #fff; transition: background 0.2s;
}
.ie-bell-live-dot.is-live { background: #1e7b4d; }
.ie-bell-panel {
  position: absolute; top: 44px; right: 0; width: 320px; max-height: 420px;
  background: #fff; border: 1px solid var(--ie-line); border-radius: 12px;
  box-shadow: var(--ie-shadow); z-index: 50; overflow: hidden; display: flex; flex-direction: column;
}
.ie-bell-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid var(--ie-line); font-size: 13px; }
.ie-bell-markall { background: none; border: 0; color: var(--ie-red); font-size: 11.5px; font-weight: 700; cursor: pointer; }
.ie-bell-list { overflow-y: auto; max-height: 360px; }
.ie-bell-item { display: block; width: 100%; text-align: left; padding: 10px 14px; border: 0; border-bottom: 1px solid var(--ie-line); background: #fff; cursor: pointer; }
.ie-bell-item:hover { background: #fafbfc; }
.ie-bell-item.unread { background: var(--ie-red-soft); }
.ie-bell-title { font-size: 12.5px; font-weight: 700; color: var(--ie-navy); }
.ie-bell-message { font-size: 12px; color: var(--ie-muted); margin-top: 2px; }
.ie-bell-date { font-size: 10.5px; color: var(--ie-muted); margin-top: 4px; }
.ie-bell-empty { padding: 20px; text-align: center; font-size: 12.5px; color: var(--ie-muted); }
@media (max-width: 560px) {
  .ie-bell-panel { position: fixed; top: 60px; right: 12px; width: min(320px, calc(100vw - 24px)); max-width: calc(100vw - 24px); }
}
</style>
