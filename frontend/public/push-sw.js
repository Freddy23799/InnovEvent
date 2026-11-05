/* Notifications Web Push — importé par le service worker généré (Workbox).
 * Reçoit les push du serveur même application fermée, les affiche comme une
 * notification système (Android, iOS en PWA, ordinateur) et ouvre la bonne
 * page au toucher. Si l'application est déjà au premier plan, la
 * notification système est évitée : l'application affiche l'alerte elle-même. */

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "InnovEvent", body: event.data ? event.data.text() : "" };
  }
  const title = data.title || "InnovEvent";
  const options = {
    body: data.body || "",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: data.tag || undefined,
    renotify: Boolean(data.tag),
    data: { link: data.link || "/app" },
    vibrate: [80, 40, 80],
  };

  // Compteur sur l'icône de l'application installée (non lues).
  const badge = typeof data.unread_count === "number" && self.navigator.setAppBadge
    ? (data.unread_count > 0 ? self.navigator.setAppBadge(data.unread_count) : self.navigator.clearAppBadge()).catch(() => {})
    : Promise.resolve();

  event.waitUntil(
    badge.then(() => self.clients.matchAll({ type: "window", includeUncontrolled: true })).then((clients) => {
      const focused = clients.find((client) => client.focused && client.visibilityState === "visible");
      if (focused) {
        focused.postMessage({ type: "ie-push", notification: { ...data, title } });
        return undefined;
      }
      return self.registration.showNotification(title, options);
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const link = (event.notification.data && event.notification.data.link) || "/app";
  const target = new URL(link, self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => client.url.startsWith(self.location.origin));
      if (existing) {
        existing.postMessage({ type: "ie-navigate", link });
        return existing.focus();
      }
      return self.clients.openWindow(target);
    })
  );
});
