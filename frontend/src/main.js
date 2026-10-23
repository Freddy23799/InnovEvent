import "@fortawesome/fontawesome-free/css/all.min.css";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import "./assets/styles/design-system.css";
import i18n from "./i18n";
import router from "./router";
import { useAuthStore } from "./stores/auth";
import { useToastStore } from "./stores/toast";

const app = createApp(App);
app.use(createPinia());
app.use(i18n);

// Filet de sécurité : de nombreux écrans chargent leurs données dans un
// `try { … } finally { … }` sans `catch`. Sans gestionnaire global, un échec
// d'API y passait inaperçu (liste vide, aucun message). Les erreurs déjà
// interceptées localement n'arrivent jamais ici, donc pas de double toast.
function apiErrorMessage(error) {
  const response = error?.response;
  if (!response) return "Connexion au serveur impossible. Vérifiez votre réseau puis réessayez.";
  const data = response.data;
  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.message === "string") return data.message;
  const firstField = data && typeof data === "object" ? Object.values(data).flat()[0] : null;
  if (typeof firstField === "string") return firstField;
  return "Une erreur est survenue. Réessayez dans quelques instants.";
}

function reportUnhandledError(error) {
  console.error(error);
  if (!error?.isAxiosError || error.code === "ERR_CANCELED" || error.response?.status === 401) return;
  useToastStore().error(apiErrorMessage(error));
}

app.config.errorHandler = reportUnhandledError;
window.addEventListener("unhandledrejection", (event) => reportUnhandledError(event.reason));

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
