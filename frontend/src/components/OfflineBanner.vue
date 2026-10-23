<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

const offline = ref(typeof navigator !== "undefined" && navigator.onLine === false);
const update = () => (offline.value = navigator.onLine === false);

onMounted(() => {
  window.addEventListener("online", update);
  window.addEventListener("offline", update);
});
onBeforeUnmount(() => {
  window.removeEventListener("online", update);
  window.removeEventListener("offline", update);
});
</script>

<template>
  <transition name="ie-offline">
    <div v-if="offline" class="ie-offline-banner" role="status">
      <i class="fa-solid fa-wifi"></i>
      Connexion perdue. Vos actions reprendront dès le retour du réseau — aucun paiement ne sera débité deux fois.
    </div>
  </transition>
</template>

<style scoped>
.ie-offline-banner { position: fixed; left: 50%; bottom: 18px; z-index: 2500; display: flex; align-items: center; gap: 10px; max-width: calc(100vw - 32px); padding: 11px 16px; border-radius: 12px; background: #1d2b3a; color: #fff; font-size: 13px; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25); transform: translateX(-50%); }
.ie-offline-banner i { color: #ffb4b4; }
.ie-offline-enter-active, .ie-offline-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.ie-offline-enter-from, .ie-offline-leave-to { opacity: 0; transform: translate(-50%, 10px); }
</style>
