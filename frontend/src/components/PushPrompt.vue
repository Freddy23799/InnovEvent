<script setup>
import { onMounted, ref } from "vue";
import { enablePush, isPushSupported, notificationPermission } from "../services/push";

// Invitation à activer les notifications push sur cet appareil. L'autorisation
// doit venir d'un geste de l'utilisateur (obligatoire sur iPhone et Android) :
// d'où ce bandeau plutôt qu'une demande automatique au chargement.
const DISMISS_KEY = "ie-push-prompt-dismissed";
const visible = ref(false);
const busy = ref(false);
const denied = ref(false);

function dismissedRecently() {
  try {
    const at = Number(localStorage.getItem(DISMISS_KEY) || 0);
    return Date.now() - at < 7 * 86400000;
  } catch (e) {
    return false;
  }
}

function dismiss() {
  visible.value = false;
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  } catch (e) {
    // stockage indisponible : le bandeau réapparaîtra simplement plus tard
  }
}

async function activate() {
  busy.value = true;
  try {
    const result = await enablePush({ ask: true });
    if (result === "granted") {
      visible.value = false;
      window.dispatchEvent(new CustomEvent("ie:push-activated"));
    } else if (result === "denied") {
      denied.value = true;
    } else {
      dismiss();
    }
  } catch (e) {
    dismiss();
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  visible.value = isPushSupported() && notificationPermission() === "default" && !dismissedRecently();
});
</script>

<template>
  <div v-if="visible" class="pp" role="region" aria-label="Activer les notifications">
    <span class="pp-icon"><i class="fa-solid fa-bell"></i></span>
    <div class="pp-text">
      <strong>{{ denied ? "Notifications bloquées" : "Ne manquez aucun message" }}</strong>
      <small v-if="denied">Autorisez les notifications pour ce site dans les réglages du navigateur.</small>
      <small v-else>Recevez vos messages, commandes et devis en temps réel, même application fermée.</small>
    </div>
    <button v-if="!denied" type="button" class="ie-btn ie-btn-primary ie-btn-sm" :disabled="busy" @click="activate">
      {{ busy ? "…" : "Activer" }}
    </button>
    <button type="button" class="pp-close" aria-label="Plus tard" @click="dismiss"><i class="fa-solid fa-xmark"></i></button>
  </div>
</template>

<style scoped>
.pp {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 12px 14px; border: 1px solid #d9e1ea;
  border-radius: 14px; background: #fff; box-shadow: var(--ie-shadow-sm);
}
.pp-icon { display: grid; place-items: center; width: 40px; height: 40px; flex: 0 0 40px; border-radius: 12px; background: var(--ie-red-soft); color: var(--ie-red); font-size: 16px; }
.pp-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.pp-text strong { color: var(--ie-navy); font-size: 14px; }
.pp-text small { color: var(--ie-muted); font-size: 12.5px; line-height: 1.4; }
.pp-close { width: 30px; height: 30px; flex: 0 0 30px; border: 0; border-radius: 50%; background: #f2f4f6; color: var(--ie-muted); cursor: pointer; }
@media (max-width: 560px) {
  .pp { flex-wrap: wrap; }
  .pp-text { flex-basis: calc(100% - 100px); }
  .pp .ie-btn { order: 3; width: 100%; justify-content: center; }
}
</style>
