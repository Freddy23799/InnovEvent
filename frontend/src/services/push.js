import api from "./api";

// Abonnement Web Push de l'appareil : notifications même application fermée
// (Android, ordinateur, iPhone une fois l'application installée).

export function isPushSupported() {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export function notificationPermission() {
  return typeof Notification === "undefined" ? "unsupported" : Notification.permission;
}

function urlBase64ToUint8Array(base64) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)));
}

async function registration() {
  return navigator.serviceWorker.ready;
}

// Enregistre l'appareil auprès du serveur. `ask` : demande l'autorisation
// si elle n'a pas encore été donnée (doit venir d'un clic de l'utilisateur).
export async function enablePush({ ask = false } = {}) {
  if (!isPushSupported()) return "unsupported";
  let permission = Notification.permission;
  if (permission === "default" && ask) permission = await Notification.requestPermission();
  if (permission !== "granted") return permission;

  const { data } = await api.get("/notifications/push/");
  if (!data.enabled || !data.public_key) return "server-disabled";

  const reg = await registration();
  let subscription = await reg.pushManager.getSubscription();
  if (!subscription) {
    subscription = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(data.public_key),
    });
  }
  await api.post("/notifications/push/", subscription.toJSON());
  return "granted";
}

export async function hasPushSubscription() {
  if (!isPushSupported() || Notification.permission !== "granted") return false;
  const reg = await registration();
  return Boolean(await reg.pushManager.getSubscription());
}

// Compteur de notifications non lues sur l'icône de l'application
// (PWA installée : Android, iPhone, ordinateur) — sans effet ailleurs.
export function setAppBadge(count) {
  if (typeof navigator === "undefined" || !navigator.setAppBadge) return;
  (count > 0 ? navigator.setAppBadge(count) : navigator.clearAppBadge()).catch(() => {});
}

// Notification système affichée par l'application elle-même (onglet en
// arrière-plan sans abonnement push) — `new Notification()` est refusé sur
// mobile, le service worker doit l'afficher.
export async function showLocalNotification(notification) {
  if (!isPushSupported() || Notification.permission !== "granted") return;
  const reg = await registration();
  reg.showNotification(notification.title || "InnovEvent", {
    body: notification.message || notification.body || "",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: `notification-${notification.id}`,
    data: { link: notification.link || "/app" },
  });
}
