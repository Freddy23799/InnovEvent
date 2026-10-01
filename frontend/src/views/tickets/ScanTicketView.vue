<script setup>
import { onBeforeUnmount, ref } from "vue";
import QrScanner from "qr-scanner";
import QrScannerWorkerPath from "qr-scanner/qr-scanner-worker.min.js?url";
import api from "../../services/api";

QrScanner.WORKER_PATH = QrScannerWorkerPath;

const mode = ref("ticket"); // 'ticket' | 'provider'
const token = ref("");
const scanning = ref(false);
const result = ref(null);
const errorMessage = ref("");
const inputEl = ref(null);

const cameraActive = ref(false);
const cameraError = ref("");
const videoEl = ref(null);
let qrScanner = null;
let resumeTimeout = null;

function switchMode(newMode) {
  mode.value = newMode;
  result.value = null;
  errorMessage.value = "";
  token.value = "";
}

async function handleScan(scannedToken) {
  const value = (scannedToken ?? token.value).trim();
  if (!value) return;
  errorMessage.value = "";
  result.value = null;
  scanning.value = true;
  const endpoint = mode.value === "ticket" ? "/tickets/scan/" : "/providers/scan/";
  try {
    const { data } = await api.post(endpoint, { token: value });
    result.value = data;
  } catch (e) {
    result.value = e?.response?.data || null;
    errorMessage.value = e?.response?.data?.detail || "Erreur lors du contrôle.";
  } finally {
    scanning.value = false;
    token.value = "";
    inputEl.value?.focus();
    if (cameraActive.value) {
      qrScanner?.pause();
      resumeTimeout = setTimeout(() => {
        result.value = null;
        qrScanner?.start();
      }, 2500);
    }
  }
}

async function toggleCamera() {
  if (cameraActive.value) {
    stopCamera();
    return;
  }
  cameraError.value = "";
  try {
    qrScanner = new QrScanner(
      videoEl.value,
      (scanResult) => handleScan(scanResult.data),
      { highlightScanRegion: true, highlightCodeOutline: true, maxScansPerSecond: 5 }
    );
    await qrScanner.start();
    cameraActive.value = true;
  } catch (e) {
    cameraError.value = "Impossible d'accéder à la caméra (autorisation refusée ou aucune caméra disponible).";
    qrScanner = null;
  }
}

function stopCamera() {
  clearTimeout(resumeTimeout);
  qrScanner?.stop();
  qrScanner?.destroy();
  qrScanner = null;
  cameraActive.value = false;
}

onBeforeUnmount(stopCamera);
</script>

<template>
  <div>
    <h1><i class="fa-solid fa-qrcode" style="color: var(--ie-red); margin-right: 8px;"></i>Scan de contrôle</h1>
    <p style="color: var(--ie-muted); margin: 6px 0 20px;">
      Activez la caméra pour scanner en continu, ou collez le contenu signé manuellement.
    </p>

    <div class="ie-scan-tabs">
      <button class="ie-scan-tab" :class="{ active: mode === 'ticket' }" @click="switchMode('ticket')">
        <i class="fa-solid fa-ticket"></i> Billets
      </button>
      <button class="ie-scan-tab" :class="{ active: mode === 'provider' }" @click="switchMode('provider')">
        <i class="fa-solid fa-id-card"></i> Badges prestataires
      </button>
    </div>

    <div class="ie-card" style="max-width: 560px; padding: 24px;">
      <button class="ie-btn" :class="cameraActive ? 'ie-btn-danger' : 'ie-btn-primary'" style="width: 100%;" @click="toggleCamera">
        <i class="fa-solid" :class="cameraActive ? 'fa-video-slash' : 'fa-camera'"></i>
        {{ cameraActive ? "Désactiver la caméra" : "Activer la caméra" }}
      </button>
      <p v-if="cameraError" style="color: var(--ie-red); font-size: 12.5px; margin-top: 8px;">{{ cameraError }}</p>

      <div class="ie-camera-wrap" v-show="cameraActive">
        <video ref="videoEl"></video>
      </div>

      <div class="ie-scan-divider"><span>ou saisie manuelle</span></div>

      <form @submit.prevent="handleScan()">
        <label class="ie-label">Contenu du QR code</label>
        <input
          ref="inputEl"
          v-model="token"
          class="ie-input"
          :placeholder="mode === 'ticket' ? 'Coller le jeton du billet…' : 'Coller le jeton du badge prestataire…'"
        />
        <button class="ie-btn ie-btn-secondary" type="submit" style="width: 100%; margin-top: 14px;" :disabled="scanning">
          {{ scanning ? "Vérification…" : "Contrôler" }}
        </button>
      </form>

      <div v-if="result" class="ie-scan-result" :class="result.valid ? 'valid' : 'invalid'">
        <div class="ie-scan-status">{{ result.valid ? "✅ VALIDE" : "❌ INVALIDE" }}</div>
        <template v-if="result.valid && mode === 'ticket'">
          <p><strong>{{ result.holder }}</strong> — {{ result.event }}</p>
        </template>
        <template v-else-if="result.valid && mode === 'provider'">
          <p><strong>{{ result.name }}</strong> — {{ result.category }}</p>
          <p style="font-size:12px;">Pièce d'identité : {{ result.identity_number || "non renseignée" }}</p>
        </template>
        <p v-else>{{ result.reason || errorMessage }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-scan-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.ie-scan-tab {
  display: inline-flex; align-items: center; gap: 8px;
  border: 1px solid var(--ie-line); background: #fff; color: var(--ie-navy);
  padding: 8px 14px; border-radius: 999px; font-size: 13px; font-weight: 700; cursor: pointer;
}
.ie-scan-tab.active { background: var(--ie-red); color: #fff; border-color: var(--ie-red); }

.ie-camera-wrap {
  margin-top: 14px; border-radius: 12px; overflow: hidden; background: #000;
  aspect-ratio: 1 / 1; max-height: 340px;
}
.ie-camera-wrap video { width: 100%; height: 100%; object-fit: cover; }

.ie-scan-divider {
  display: flex; align-items: center; gap: 10px; margin: 18px 0 14px;
  color: var(--ie-muted); font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.04em;
}
.ie-scan-divider::before, .ie-scan-divider::after { content: ""; flex: 1; height: 1px; background: var(--ie-line); }

.ie-scan-result {
  margin-top: 20px;
  padding: 18px;
  border-radius: 12px;
  text-align: center;
}
.ie-scan-result.valid { background: var(--ie-success-soft); color: var(--ie-success); }
.ie-scan-result.invalid { background: var(--ie-red-soft); color: var(--ie-red); }
.ie-scan-status { font-size: 20px; font-weight: 900; margin-bottom: 8px; }
</style>
