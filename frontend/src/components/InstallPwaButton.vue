<script setup>
import { computed, onMounted, ref } from "vue";

defineProps({
  compact: { type: Boolean, default: false },
  label: { type: String, default: "Installer l'application" },
});

const deferredPrompt = ref(null);
const installed = ref(false);
const isIOS = ref(false);
const showIOSHint = ref(false);
const installing = ref(false);

onMounted(() => {
  const standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (standalone) {
    installed.value = true;
    return;
  }
  isIOS.value = /iphone|ipad|ipod/i.test(window.navigator.userAgent) && !window.MSStream;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt.value = e;
  });
  window.addEventListener("appinstalled", () => {
    installed.value = true;
    deferredPrompt.value = null;
    showIOSHint.value = false;
  });
});

const canInstall = computed(() => !installed.value && (deferredPrompt.value || isIOS.value));

async function install() {
  if (isIOS.value) {
    showIOSHint.value = !showIOSHint.value;
    return;
  }
  if (!deferredPrompt.value) return;
  installing.value = true;
  deferredPrompt.value.prompt();
  await deferredPrompt.value.userChoice;
  deferredPrompt.value = null;
  installing.value = false;
}
</script>

<template>
  <div v-if="canInstall" class="ie-pwa-install-wrap">
    <button class="ie-pwa-install-btn" :class="{ 'is-compact': compact }" type="button" :disabled="installing" @click="install">
      <i class="fa-solid fa-arrow-down-to-line"></i>
      <span>{{ installing ? "Installation…" : label }}</span>
    </button>
    <div v-if="showIOSHint" class="ie-pwa-ios-hint">
      <p>
        Sur iPhone/iPad : appuyez sur <i class="fa-solid fa-arrow-up-from-bracket"></i> « Partager », puis
        <strong>« Sur l'écran d'accueil »</strong>.
      </p>
      <button type="button" class="ie-pwa-ios-hint-close" @click="showIOSHint = false"><i class="fa-solid fa-xmark"></i></button>
    </div>
  </div>
</template>

<style scoped>
.ie-pwa-install-wrap { position: relative; display: inline-block; }
.ie-pwa-install-btn {
  display: inline-flex; align-items: center; gap: 8px;
  background: #c0272d; color: #fff; border: 0; border-radius: 999px;
  padding: 9px 18px; font-size: 0.85rem; font-weight: 700; font-family: inherit;
  cursor: pointer; transition: background 0.2s ease, transform 0.2s ease;
  white-space: nowrap;
}
.ie-pwa-install-btn:hover:not(:disabled) { background: #8a0e16; transform: translateY(-1px); }
.ie-pwa-install-btn:disabled { opacity: 0.7; cursor: default; }
.ie-pwa-install-btn i:first-child { font-size: 12px; }

.ie-pwa-install-btn.is-compact {
  background: transparent; color: #39495b; border: 1px solid #e4e7eb;
  padding: 9px 10px; width: 100%; justify-content: flex-start;
}
.ie-pwa-install-btn.is-compact:hover:not(:disabled) { background: #f6e2e3; color: #c0272d; transform: none; }

.ie-pwa-ios-hint {
  position: absolute; top: calc(100% + 8px); right: 0; z-index: 60; width: 240px;
  background: #1e2a33; color: #fff; border-radius: 10px; padding: 12px 14px;
  font-size: 12px; line-height: 1.5; box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
}
.ie-pwa-ios-hint p { margin: 0; padding-right: 16px; }
.ie-pwa-ios-hint i { color: #f3b9bc; }
.ie-pwa-ios-hint-close {
  position: absolute; top: 8px; right: 8px; background: none; border: 0; color: rgba(255, 255, 255, 0.6);
  cursor: pointer; font-size: 11px; padding: 2px;
}
.ie-pwa-ios-hint-close:hover { color: #fff; }
</style>
