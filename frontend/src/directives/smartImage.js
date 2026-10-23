// Directive `v-img` : remplace `:src` sur les <img> qui affichent une photo.
//
//   <img v-img="venue.photo" alt="…" />          chargement différé
//   <img v-img.eager="hero.image" alt="…" />     image visible dès l'ouverture
//
// Pour une image servie par la plateforme (/media/…), elle :
// 1. affiche tout de suite un aperçu flou très léger (`?w=32`, < 1 Ko) ;
// 2. attend que l'image approche de l'écran (sauf `.eager`) ;
// 3. choisit la version WebP adaptée à la taille réellement affichée et à la
//    densité de l'écran, la télécharge ET la décode hors de la page ;
// 4. l'affiche d'un seul coup avec un fondu, sans jamais la voir se dessiner
//    ligne par ligne.
// En cas d'échec de la version allégée, l'original est utilisé ; si l'original
// manque aussi, un fond neutre remplace l'icône d'image cassée.
// Les autres images (logos importés, aperçus locaux blob:/data:) gardent un
// simple fondu.

import { PLACEHOLDER_WIDTH, bestWidth, mediaUrl, preloadImage as preload, withWidth } from "../services/media";

const TRANSPARENT_PIXEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

const states = new WeakMap();
let observer = null;

function targetWidth(el) {
  const box = el.getBoundingClientRect();
  return bestWidth(box.width || el.parentElement?.getBoundingClientRect().width);
}

function reveal(el, state, src) {
  if (state.token !== el.__imgToken) return;
  el.src = src;
  el.classList.remove("ie-img-loading", "ie-img-error", "ie-img-fade");
  el.classList.add("ie-img-ready");
}

function fail(el, state) {
  if (state.token !== el.__imgToken) return;
  el.src = TRANSPARENT_PIXEL;
  el.classList.remove("ie-img-loading", "ie-img-fade");
  el.classList.add("ie-img-error");
}

function loadFull(el) {
  const state = states.get(el);
  if (!state || state.started) return;
  state.started = true;
  const variant = withWidth(state.url, targetWidth(el));
  preload(variant)
    .catch(() => preload(state.url.href))
    .then((src) => reveal(el, state, src), () => fail(el, state));
}

function getObserver() {
  if (observer || typeof IntersectionObserver === "undefined") return observer;
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        loadFull(entry.target);
      });
    },
    { rootMargin: "400px 0px" },
  );
  return observer;
}

function setup(el, binding) {
  const src = binding.value;
  const previous = states.get(el);
  if (previous && previous.src === src) return;
  if (previous) observer?.unobserve(el);

  el.__imgToken = (el.__imgToken || 0) + 1;
  const url = mediaUrl(src);
  const state = { src, url, started: false, token: el.__imgToken };
  states.set(el, state);
  el.decoding = "async";
  el.classList.remove("ie-img-ready", "ie-img-error", "ie-img-fade");

  if (!src) {
    fail(el, state);
    return;
  }
  if (!url) {
    // Logo importé, aperçu local… : pas de version allégée, simple fondu.
    el.classList.add("ie-img-fade");
    el.addEventListener("load", () => reveal(el, state, el.src), { once: true });
    el.addEventListener("error", () => fail(el, state), { once: true });
    el.src = src;
    return;
  }
  el.classList.add("ie-img-loading");
  el.src = withWidth(url, PLACEHOLDER_WIDTH);

  const io = binding.modifiers.eager ? null : getObserver();
  if (io) io.observe(el);
  else requestAnimationFrame(() => loadFull(el));
}

export default {
  mounted: setup,
  updated: setup,
  beforeUnmount(el) {
    observer?.unobserve(el);
    states.delete(el);
  },
};
