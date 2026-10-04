import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      devOptions: {
        enabled: true,
      },
      includeAssets: ["favicon.png"],
      manifest: {
        name: "InnovEvent Group",
        short_name: "InnovEvent",
        description: "Organisation d'événements, réservations, billetterie et formations — du premier devis au jour J.",
        lang: "fr",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: "#FAF8F3",
        theme_color: "#C0272D",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Application shell (JS/CSS/HTML/polices) précaché pour un démarrage
        // hors-ligne instantané ; les données métier, elles, restent "network first"
        // (section ci-dessous) pour ne jamais servir de contenu périmé par défaut.
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        navigateFallbackDenylist: [/^\/admin/, /^\/api/],
        runtimeCaching: [
          {
            // API : toujours la donnée la plus fraîche en priorité ; secours sur le
            // cache uniquement hors-ligne (consultation dégradée, jamais l'achat/paiement).
            // Limité aux GET : le cache HTTP ne peut de toute façon pas stocker les
            // réponses des requêtes mutatives (POST/PATCH/DELETE) — les laisser
            // matcher ici ferait échouer silencieusement leur mise en cache.
            urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
            method: "GET",
            handler: "NetworkFirst",
            options: {
              cacheName: "innovevent-api",
              networkTimeoutSeconds: 8,
              cacheableResponse: { statuses: [0, 200] },
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 },
            },
          },
          {
            // Photos/médias uploadés (salles, prestataires, événements...) : rarement
            // modifiés après publication, donc servis depuis le cache en priorité.
            // Les photos d'événements privés utilisent une URL signée et ne
            // doivent pas être conservées dans le cache partagé du service worker.
            urlPattern: ({ url }) => url.pathname.startsWith("/media/") && !url.pathname.startsWith("/media/events/"),
            handler: "CacheFirst",
            options: {
              cacheName: "innovevent-media",
              cacheableResponse: { statuses: [0, 200] },
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
          {
            urlPattern: ({ url }) => url.origin === "https://fonts.googleapis.com" || url.origin === "https://fonts.gstatic.com",
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts",
              cacheableResponse: { statuses: [0, 200] },
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    host: true,
    port: 5173,
  },
});
