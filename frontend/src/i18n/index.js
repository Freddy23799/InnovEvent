import { createI18n } from "vue-i18n";
import en from "./locales/en";
import fr from "./locales/fr";

// Infrastructure multi-langues : le français reste la langue par défaut de
// toute l'application (comportement inchangé pour les écrans non encore
// convertis, qui gardent simplement leur texte français codé en dur). Seuls
// les écrans passés à $t()/useI18n() changent réellement de langue ; les
// autres continuent de fonctionner à l'identique, ce qui permet d'étendre la
// couverture progressivement, écran par écran, sans rien casser.
export const SUPPORTED_LOCALES = [
  { code: "fr", label: "Français" },
  { code: "en", label: "English" },
];

const STORAGE_KEY = "innovevent_locale";

function detectInitialLocale() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && SUPPORTED_LOCALES.some((l) => l.code === saved)) return saved;
  const browserLang = (navigator.language || "fr").slice(0, 2);
  return SUPPORTED_LOCALES.some((l) => l.code === browserLang) ? browserLang : "fr";
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: detectInitialLocale(),
  fallbackLocale: "fr",
  messages: { fr, en },
});

export function setLocale(code) {
  if (!SUPPORTED_LOCALES.some((l) => l.code === code)) return;
  i18n.global.locale.value = code;
  localStorage.setItem(STORAGE_KEY, code);
  document.documentElement.setAttribute("lang", code);
}

document.documentElement.setAttribute("lang", i18n.global.locale.value);

export default i18n;
