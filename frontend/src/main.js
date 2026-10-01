import "@fortawesome/fontawesome-free/css/all.min.css";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import "./assets/styles/design-system.css";
import i18n from "./i18n";
import router from "./router";
import { useAuthStore } from "./stores/auth";

const app = createApp(App);
app.use(createPinia());
app.use(i18n);

const auth = useAuthStore();
// Le routeur déclenche sa résolution de route initiale (et donc les gardes de
// navigation basées sur auth.role) dès `app.use(router)`, indépendamment de
// `app.mount()`. Il faut donc attendre la restauration de session AVANT
// d'installer le routeur, sinon un rechargement direct sur une route
// réservée à un rôle (ex: /app/users) est renvoyé vers le tableau de bord
// car auth.role est encore `null` au moment où la garde s'exécute.
auth.restoreSession().finally(() => {
  app.use(router);
  app.mount("#app");
});
