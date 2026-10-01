<script setup>
import { useLightboxStore } from "../stores/lightbox";

const lightbox = useLightboxStore();
</script>

<template>
  <Teleport to="body">
    <div v-if="lightbox.imageUrl" class="ie-lightbox-overlay" @click.self="lightbox.close()">
      <button class="ie-lightbox-close" @click="lightbox.close()" aria-label="Fermer">
        <i class="fa-solid fa-xmark"></i>
      </button>
      <figure class="ie-lightbox-figure">
        <img :src="lightbox.imageUrl" :alt="lightbox.caption" />
        <figcaption v-if="lightbox.caption">{{ lightbox.caption }}</figcaption>
      </figure>
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
.ie-lightbox-figure img { max-width: 90vw; max-height: 80vh; border-radius: 10px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); }
.ie-lightbox-figure figcaption { color: #fff; font-size: 13px; margin-top: 12px; }
.ie-lightbox-close {
  position: absolute; top: 20px; right: 24px; background: rgba(255, 255, 255, 0.12);
  color: #fff; border: 0; width: 40px; height: 40px; border-radius: 50%;
  font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.ie-lightbox-close:hover { background: rgba(255, 255, 255, 0.24); }
@media (max-width: 640px) {
  .ie-lightbox-overlay { padding: 16px; padding-top: max(16px, env(safe-area-inset-top)); }
  .ie-lightbox-figure, .ie-lightbox-figure img { max-width: 100%; }
  .ie-lightbox-figure img { max-height: 78dvh; object-fit: contain; }
  .ie-lightbox-close { top: max(12px, env(safe-area-inset-top)); right: 12px; }
}
</style>
