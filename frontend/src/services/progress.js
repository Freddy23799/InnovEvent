import { reactive } from "vue";

// Barre de progression globale (TopProgressBar) : alimentée par les
// navigations du routeur et les requêtes API. Elle n'apparaît qu'au-delà de
// SHOW_DELAY_MS pour ne pas clignoter sur les actions instantanées.
const SHOW_DELAY_MS = 150;

export const progress = reactive({ visible: false, value: 0 });

let pending = 0;
let showTimer = null;
let trickleTimer = null;
let hideTimer = null;

function trickle() {
  // Avance de plus en plus lentement sans jamais atteindre 100 % seule.
  progress.value = Math.min(progress.value + (90 - progress.value) * 0.12, 90);
}

export function startProgress() {
  pending += 1;
  if (pending > 1) return;
  clearTimeout(hideTimer);
  showTimer = setTimeout(() => {
    progress.visible = true;
    progress.value = 12;
    trickleTimer = setInterval(trickle, 250);
  }, SHOW_DELAY_MS);
}

export function doneProgress() {
  pending = Math.max(0, pending - 1);
  if (pending > 0) return;
  clearTimeout(showTimer);
  clearInterval(trickleTimer);
  if (!progress.visible) return;
  progress.value = 100;
  hideTimer = setTimeout(() => {
    progress.visible = false;
    progress.value = 0;
  }, 260);
}
