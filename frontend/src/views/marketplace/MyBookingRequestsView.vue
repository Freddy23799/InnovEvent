<script setup>
import { reactive, onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";

const STATUS_META = {
  pending: { label: "En attente de réponse", badge: "ie-badge-neutral" },
  quoted: { label: "Devis reçu", badge: "ie-badge-warning" },
  modification_requested: { label: "Modification demandée", badge: "ie-badge-warning" },
  accepted: { label: "Devis accepté — paiement attendu", badge: "ie-badge-warning" },
  confirmed: { label: "Confirmée (payée)", badge: "ie-badge-success" },
  completed: { label: "Prestation réalisée", badge: "ie-badge-success" },
  declined: { label: "Refusée", badge: "ie-badge-danger" },
  cancelled: { label: "Annulée", badge: "ie-badge-danger" },
  contacted: { label: "Mise en relation effectuée", badge: "ie-badge-neutral" },
};

const requests = ref([]);
const loading = ref(true);
const actionBusy = reactive({});
const modificationDrafts = reactive({});
const showModificationForm = reactive({});
const quoteCoupon = reactive({});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/booking-requests/");
    requests.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function fmt(amount, currency) {
  return `${Number(amount).toLocaleString('fr-FR')} ${currency}`;
}

async function acceptQuote(quote) {
  actionBusy[quote.id] = true;
  try {
    await api.post(`/marketplace/quotes/${quote.id}/accept/`);
    await loadData();
  } finally {
    actionBusy[quote.id] = false;
  }
}

async function declineQuote(quote) {
  if (!confirm("Refuser ce devis ?")) return;
  actionBusy[quote.id] = true;
  try {
    await api.post(`/marketplace/quotes/${quote.id}/decline/`);
    await loadData();
  } finally {
    actionBusy[quote.id] = false;
  }
}

async function requestModification(quote) {
  actionBusy[quote.id] = true;
  try {
    await api.post(`/marketplace/quotes/${quote.id}/request-modification/`, { message: modificationDrafts[quote.id] || "" });
    showModificationForm[quote.id] = false;
    modificationDrafts[quote.id] = "";
    await loadData();
  } finally {
    actionBusy[quote.id] = false;
  }
}

async function payQuote(quote) {
  actionBusy[quote.id] = true;
  try {
    await api.post(`/marketplace/quotes/${quote.id}/pay/`, {
      payment_provider: "demo", coupon_code: quoteCoupon[quote.id] || undefined,
    });
    await loadData();
  } finally {
    actionBusy[quote.id] = false;
  }
}

async function downloadPdf(quote) {
  const { data } = await api.get(`/marketplace/quotes/${quote.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `devis-${String(quote.id).padStart(6, "0")}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-clipboard-list" style="color: var(--ie-red); margin-right: 8px;"></i>Mes demandes prestataires</h1>
        <p class="ie-page-subtitle">Suivez vos demandes de devis et négociez directement avec chaque prestataire, sans jamais échanger de coordonnées personnelles hors plateforme.</p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <div v-else-if="requests.length" style="display: flex; flex-direction: column; gap: 16px;">
      <div v-for="r in requests" :key="r.id" class="ie-card ie-card-body">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;">
          <div>
            <strong style="font-size: 14.5px; color: var(--ie-navy);">{{ r.business_name }}</strong>
            <p v-if="r.service_name" style="margin: 2px 0 0; font-size: 12.5px; color: var(--ie-muted);">{{ r.service_name }}</p>
            <p style="margin: 2px 0 0; font-size: 12px; color: var(--ie-muted);">
              {{ r.event_type || "Événement" }}
              <template v-if="r.event_date"> · {{ new Date(r.event_date).toLocaleDateString('fr-FR') }}</template>
              <template v-if="r.city"> · {{ r.city }}</template>
            </p>
          </div>
          <span class="ie-badge" :class="STATUS_META[r.status]?.badge">{{ STATUS_META[r.status]?.label || r.status }}</span>
        </div>
        <p v-if="r.message" style="margin: 10px 0 0; font-size: 12.5px; color: var(--ie-muted); line-height: 1.5;">{{ r.message }}</p>
        <p v-if="r.requested_equipment?.length" style="margin: 8px 0 0; font-size: 12px; color: var(--ie-ink);">
          <i class="fa-solid fa-boxes-stacked" style="color: var(--ie-red);"></i>
          {{ r.requested_equipment.map((i) => `${i.equipment_name} × ${i.quantity}`).join(', ') }}
        </p>
        <p style="margin: 8px 0 0; font-size: 11px; color: var(--ie-muted);">Envoyée le {{ new Date(r.created_at).toLocaleDateString('fr-FR') }}</p>

        <div v-if="r.latest_quote" class="ie-quote-block">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <strong style="font-size: 13px; color: var(--ie-navy);"><i class="fa-solid fa-file-invoice" style="color: var(--ie-red);"></i> Devis reçu</strong>
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="downloadPdf(r.latest_quote)">
              <i class="fa-solid fa-download"></i> Télécharger le PDF
            </button>
          </div>

          <div class="ie-quote-items">
            <div v-for="item in r.latest_quote.items" :key="item.id" class="ie-quote-item-row">
              <span>{{ item.label }} <template v-if="item.quantity > 1">× {{ item.quantity }}</template></span>
              <strong>{{ fmt(item.line_total, r.latest_quote.currency) }}</strong>
            </div>
          </div>
          <div class="ie-quote-totals">
            <div v-if="Number(r.latest_quote.travel_fee) > 0" class="ie-quote-item-row ie-quote-total-line">
              <span>Frais de déplacement</span><span>{{ fmt(r.latest_quote.travel_fee, r.latest_quote.currency) }}</span>
            </div>
            <div v-if="Number(r.latest_quote.additional_fees) > 0" class="ie-quote-item-row ie-quote-total-line">
              <span>Frais supplémentaires</span><span>{{ fmt(r.latest_quote.additional_fees, r.latest_quote.currency) }}</span>
            </div>
            <div v-if="Number(r.latest_quote.discount) > 0" class="ie-quote-item-row ie-quote-total-line">
              <span>Remise</span><span>-{{ fmt(r.latest_quote.discount, r.latest_quote.currency) }}</span>
            </div>
            <div class="ie-quote-item-row ie-quote-grand-total">
              <span>Total</span><span>{{ fmt(r.latest_quote.total_amount, r.latest_quote.currency) }}</span>
            </div>
          </div>

          <p v-if="r.latest_quote.conditions" class="ie-quote-note"><strong>Conditions :</strong> {{ r.latest_quote.conditions }}</p>
          <p v-if="r.latest_quote.cancellation_policy" class="ie-quote-note"><strong>Annulation :</strong> {{ r.latest_quote.cancellation_policy }}</p>
          <p v-if="r.latest_quote.provider_note" class="ie-quote-note"><strong>Message du prestataire :</strong> {{ r.latest_quote.provider_note }}</p>
          <p v-if="r.latest_quote.valid_until" class="ie-field-hint" style="margin-top: 6px;">
            Valable jusqu'au {{ new Date(r.latest_quote.valid_until).toLocaleDateString('fr-FR') }}
          </p>

          <div v-if="r.latest_quote.status === 'sent'" style="margin-top: 14px;">
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <button class="ie-btn ie-btn-primary ie-btn-sm" :disabled="actionBusy[r.latest_quote.id]" @click="acceptQuote(r.latest_quote)">
                <i class="fa-solid fa-check"></i> Accepter
              </button>
              <button class="ie-btn ie-btn-ghost ie-btn-sm" :disabled="actionBusy[r.latest_quote.id]" @click="showModificationForm[r.latest_quote.id] = !showModificationForm[r.latest_quote.id]">
                <i class="fa-solid fa-pen"></i> Demander une modification
              </button>
              <button class="ie-btn ie-btn-danger ie-btn-sm" :disabled="actionBusy[r.latest_quote.id]" @click="declineQuote(r.latest_quote)">
                <i class="fa-solid fa-xmark"></i> Refuser
              </button>
            </div>
            <div v-if="showModificationForm[r.latest_quote.id]" style="margin-top: 10px;">
              <textarea v-model="modificationDrafts[r.latest_quote.id]" class="ie-input" rows="2" placeholder="Précisez ce que vous souhaitez modifier..."></textarea>
              <button class="ie-btn ie-btn-primary ie-btn-sm" style="margin-top: 8px;" :disabled="actionBusy[r.latest_quote.id]" @click="requestModification(r.latest_quote)">
                Envoyer la demande de modification
              </button>
            </div>
          </div>

          <div v-else-if="r.latest_quote.status === 'accepted'" style="margin-top: 14px;">
            <input
              v-model="quoteCoupon[r.latest_quote.id]" class="ie-input" style="margin-bottom: 8px; font-size: 12px;"
              placeholder="Code de réduction (optionnel)"
            />
            <button class="ie-btn ie-btn-primary" style="width: 100%;" :disabled="actionBusy[r.latest_quote.id]" @click="payQuote(r.latest_quote)">
              <i class="fa-solid fa-credit-card"></i> {{ actionBusy[r.latest_quote.id] ? "Traitement…" : `Payer ${fmt(r.latest_quote.total_amount, r.latest_quote.currency)}` }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <EmptyState v-else icon="fa-solid fa-clipboard-list" text="Vous n'avez envoyé aucune demande de devis pour le moment." />
  </div>
</template>

<style scoped>
.ie-quote-block { margin-top: 14px; padding: 14px; background: var(--ie-navy-soft); border-radius: 10px; }
.ie-quote-items { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
.ie-quote-item-row { display: flex; justify-content: space-between; font-size: 12.5px; color: var(--ie-ink); }
.ie-quote-totals { margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--ie-line); display: flex; flex-direction: column; gap: 4px; }
.ie-quote-total-line { color: var(--ie-muted); font-size: 12px; }
.ie-quote-grand-total { font-weight: 700; color: var(--ie-red); font-size: 14px; margin-top: 4px; }
.ie-quote-note { margin: 8px 0 0; font-size: 12px; color: var(--ie-muted); line-height: 1.5; }
</style>
