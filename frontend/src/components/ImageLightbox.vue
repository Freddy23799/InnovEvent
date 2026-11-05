<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import { useLightboxStore } from "../stores/lightbox";

const lightbox = useLightboxStore();

function onKeydown(event) {
  if (!lightbox.imageUrl) return;
  if (event.key === "Escape") lightbox.close();
  else if (event.key === "ArrowRight") lightbox.next();
  else if (event.key === "ArrowLeft") lightbox.prev();
}

// Glisser horizontalement sur mobile pour passer d'une réalisation à l'autre.
let touchStartX = null;
function onTouchStart(event) {
  touchStartX = event.touches[0].clientX;
}
function onTouchEnd(event) {
  if (touchStartX === null) return;
  const delta = event.changedTouches[0].clientX - touchStartX;
  touchStartX = null;
  if (Math.abs(delta) < 40) return;
  if (delta < 0) lightbox.next();
  else lightbox.prev();
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Teleport to="body">
    <div
      v-if="lightbox.imageUrl"
      class="ie-lightbox-overlay"
      role="dialog"
      aria-modal="true"
      @click.self="lightbox.close()"
      @touchstart.passive="onTouchStart"
      @touchend="onTouchEnd"
    >
      <button class="ie-lightbox-close" @click="lightbox.close()" aria-label="Fermer">
        <i class="fa-solid fa-xmark"></i>
      </button>
      <span v-if="lightbox.hasMany" class="ie-lightbox-counter">{{ lightbox.index + 1 }} / {{ lightbox.items.length }}</span>
      <button v-if="lightbox.hasMany" class="ie-lightbox-nav prev" aria-label="Image précédente" @click="lightbox.prev()">
        <i class="fa-solid fa-chevron-left"></i>
      </button>
      <figure class="ie-lightbox-figure">
        <img :key="lightbox.imageUrl" :src="lightbox.imageUrl" :alt="lightbox.caption" />
        <figcaption v-if="lightbox.caption">{{ lightbox.caption }}</figcaption>
      </figure>
      <button v-if="lightbox.hasMany" class="ie-lightbox-nav next" aria-label="Image suivante" @click="lightbox.next()">
        <i class="fa-solid fa-chevron-right"></i>
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.ie-lightbox-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(20, 24, 28, 0.88);
  display: flex; align-items: center; justify-content: center;
  padding: 40px; cursor: zoom-out;
}
.ie-lightbox-figure { max-width: 90vw; max-height: 90vh; margin: 0; text-align: center; cursor: default; }
.ie-lightbox-figure img {
  max-width: 90vw; max-height: 80vh; border-radius: 10px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: ie-lightbox-in 0.18s ease;
}
.ie-lightbox-figure figcaption { color: #fff; font-size: 13px; margin-top: 12px; }
.ie-lightbox-close, .ie-lightbox-nav {
  position: absolute; background: rgba(255, 255, 255, 0.12);
  color: #fff; border: 0; border-radius: 50%;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.ie-lightbox-close { top: 20px; right: 24px; width: 40px; height: 40px; font-size: 16px; }
.ie-lightbox-nav { top: 50%; transform: translateY(-50%); width: 46px; height: 46px; font-size: 17px; z-index: 1; }
.ie-lightbox-nav.prev { left: 20px; }
.ie-lightbox-nav.next { right: 20px; }
.ie-lightbox-close:hover, .ie-lightbox-nav:hover { background: rgba(255, 255, 255, 0.24); }
.ie-lightbox-counter {
  position: absolute; top: 28px; left: 50%; transform: translateX(-50%);
  color: #fff; font-size: 13px; font-weight: 700; opacity: 0.85;
}
@keyframes ie-lightbox-in { from { opacity: 0; transform: scale(0.98); } }
@media (max-width: 640px) {
  .ie-lightbox-overlay { padding: 16px; padding-top: max(16px, env(safe-area-inset-top)); }
  .ie-lightbox-figure, .ie-lightbox-figure img { max-width: 100%; }
  .ie-lightbox-figure img { max-height: 78dvh; object-fit: contain; }
  .ie-lightbox-close { top: max(12px, env(safe-area-inset-top)); right: 12px; }
  .ie-lightbox-counter { top: max(22px, calc(env(safe-area-inset-top) + 10px)); }
  .ie-lightbox-nav { top: auto; bottom: max(18px, env(safe-area-inset-bottom)); transform: none; width: 44px; height: 44px; }
  .ie-lightbox-nav.prev { left: calc(50% - 56px); }
  .ie-lightbox-nav.next { right: calc(50% - 56px); }
}
@media (prefers-reduced-motion: reduce) {
  .ie-lightbox-figure img { animation: none; }
}
</style>
