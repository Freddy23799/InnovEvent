<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";

const STATUS_META = {
  pending: { label: "En attente de votre réponse", badge: "ie-badge-warning" },
  quoted: { label: "Devis envoyé — en attente du client", badge: "ie-badge-neutral" },
  modification_requested: { label: "Le client demande une modification", badge: "ie-badge-warning" },
  accepted: { label: "Accepté — paiement attendu", badge: "ie-badge-neutral" },
  confirmed: { label: "Confirmée (payée)", badge: "ie-badge-success" },
  completed: { label: "Prestation réalisée", badge: "ie-badge-success" },
  declined: { label: "Refusée", badge: "ie-badge-danger" },
  cancelled: { label: "Annulée", badge: "ie-badge-danger" },
  contacted: { label: "Suivi manuel par l'administration", badge: "ie-badge-neutral" },
};

const RESPONDABLE = new Set(["pending", "modification_requested"]);

const requests = ref([]);
const loading = ref(true);
const openQuoteForm = reactive({});
const quoteDrafts = reactive({});
const submitting = reactive({});
const errors = reactive({});

function emptyDraft(previousQuote) {
  return {
    items: previousQuote?.items?.length
      ? previousQuote.items.map((i) => ({ label: i.label, quantity: i.quantity, unit_price: i.unit_price }))
      : [{ label: "", quantity: 1, unit_price: 0 }],
    travel_fee: Number(previousQuote?.travel_fee) || 0,
    additional_fees: Number(previousQuote?.additional_fees) || 0,
    discount: Number(previousQuote?.discount) || 0,
    currency: previousQuote?.currency || "XAF",
    conditions: previousQuote?.conditions || "",
    cancellation_policy: previousQuote?.cancellation_policy || "",
    valid_until: previousQuote?.valid_until || "",
    provider_note: "",
  };
}

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get("/marketplace/booking-requests/");
    requests.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

function toggleQuoteForm(request) {
  if (!openQuoteForm[request.id]) {
    quoteDrafts[request.id] = emptyDraft(request.latest_quote);
  }
  openQuoteForm[request.id] = !openQuoteForm[request.id];
}

function addItem(requestId) {
  quoteDrafts[requestId].items.push({ label: "", quantity: 1, unit_price: 0 });
}

function removeItem(requestId, index) {
  quoteDrafts[requestId].items.splice(index, 1);
}

function draftTotal(draft) {
  if (!draft) return 0;
  const itemsTotal = draft.items.reduce((sum, i) => sum + (Number(i.quantity) || 0) * (Number(i.unit_price) || 0), 0);
  return itemsTotal + (Number(draft.travel_fee) || 0) + (Number(draft.additional_fees) || 0) - (Number(draft.discount) || 0);
}

async function sendQuote(request) {
  errors[request.id] = "";
  submitting[request.id] = true;
  try {
    const draft = quoteDrafts[request.id];
    await api.post("/marketplace/quotes/", {
      booking_request: request.id,
      items: draft.items.filter((i) => i.label.trim()),
      travel_fee: draft.travel_fee || 0,
      additional_fees: draft.additional_fees || 0,
      discount: draft.discount || 0,
      currency: draft.currency || "XAF",
      conditions: draft.conditions,
      cancellation_policy: draft.cancellation_policy,
      valid_until: draft.valid_until || null,
      provider_note: draft.provider_note,
    });
    openQuoteForm[request.id] = false;
    await loadData();
  } catch (e) {
    errors[request.id] = e?.response?.data?.items?.[0] || e?.response?.data?.detail || "Impossible d'envoyer ce devis.";
  } finally {
    submitting[request.id] = false;
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

async function declineRequest(request) {
  if (!confirm("Refuser cette demande sans envoyer de devis ?")) return;
  submitting[request.id] = true;
  try {
    await api.post(`/marketplace/booking-requests/${request.id}/decline/`, {});
    await loadData();
  } finally {
    submitting[request.id] = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-file-invoice" style="color: var(--ie-red); margin-right: 8px;"></i>Demandes de devis reçues</h1>
        <p class="ie-page-subtitle">Répondez directement aux clients avec un devis détaillé — jamais de coordonnées personnelles échangées, tout se passe ici.</p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 200px;"></div>

    <div v-else-if="requests.length" style="display: flex; flex-direction: column; gap: 16px;">
      <div v-for="r in requests" :key="r.id" class="ie-card ie-card-body">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;">
          <div>
            <strong style="font-size: 14.5px; color: var(--ie-navy);">{{ r.client_name }}</strong>
            <span v-if="r.service_name" style="color: var(--ie-muted); font-size: 12.5px;"> — {{ r.service_name }}</span>
            <p style="margin: 4px 0 0; font-size: 12.5px; color: var(--ie-ink);">
              {{ r.event_type || "Événement" }}
              <template v-if="r.event_date"> · <i class="fa-solid fa-calendar-day"></i> {{ new Date(r.event_date).toLocaleDateString('fr-FR') }}</template>
              <template v-if="r.event_time"> à {{ r.event_time.slice(0, 5) }}</template>
              <template v-if="r.location"> · {{ r.location }}</template>
              <template v-if="r.city"> ({{ r.city }})</template>
            </p>
            <p style="margin: 2px 0 0; font-size: 12px; color: var(--ie-muted);">
              <template v-if="r.guest_count">{{ r.guest_count }} invités · </template>
              <template v-if="r.budget_estimate">Budget indicatif : {{ Number(r.budget_estimate).toLocaleString('fr-FR') }} XAF</template>
            </p>
          </div>
          <span class="ie-badge" :class="STATUS_META[r.status]?.badge">{{ STATUS_META[r.status]?.label || r.status }}</span>
        </div>

        <p v-if="r.options_wanted" style="margin: 8px 0 0; font-size: 12.5px; color: var(--ie-ink);"><strong>Options souhaitées :</strong> {{ r.options_wanted }}</p>
        <p v-if="r.message" style="margin: 8px 0 0; font-size: 12.5px; color: var(--ie-muted); line-height: 1.5;">{{ r.message }}</p>

        <div v-if="r.requested_equipment?.length" class="ie-requested-equipment">
          <strong><i class="fa-solid fa-boxes-stacked" style="color: var(--ie-red);"></i> Matériel souhaité</strong>
          <ul>
            <li v-for="item in r.requested_equipment" :key="item.id">{{ item.equipment_name }} × {{ item.quantity }}</li>
          </ul>
        </div>

        <div v-if="r.status === 'modification_requested' && r.latest_quote?.client_message" class="ie-alert ie-alert-warning" style="margin-top: 12px;">
          <i class="fa-solid fa-comment"></i> <strong>Le client demande :</strong> {{ r.latest_quote.client_message }}
        </div>

        <div v-if="r.latest_quote && !RESPONDABLE.has(r.status)" class="ie-quote-summary">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <strong>Votre devis : {{ Number(r.latest_quote.total_amount).toLocaleString('fr-FR') }} {{ r.latest_quote.currency }}</strong>
              <span class="ie-field-hint"> — {{ r.latest_quote.status_label }}</span>
            </div>
            <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="downloadPdf(r.latest_quote)">
              <i class="fa-solid fa-download"></i> Télécharger le PDF
            </button>
          </div>
          <div v-if="r.latest_quote.provider_payout != null" class="ie-payout-row">
            <span>Commission InnovEvent ({{ r.latest_quote.commission_percent }}%)</span>
            <span>-{{ Number(r.latest_quote.commission_amount).toLocaleString('fr-FR') }} {{ r.latest_quote.currency }}</span>
          </div>
          <div v-if="r.latest_quote.provider_payout != null" class="ie-payout-row ie-payout-net">
            <span>Vous recevez</span>
            <span>{{ Number(r.latest_quote.provider_payout).toLocaleString('fr-FR') }} {{ r.latest_quote.currency }}</span>
          </div>
        </div>

        <template v-if="RESPONDABLE.has(r.status)">
          <div style="display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap;">
            <button class="ie-btn ie-btn-primary ie-btn-sm" @click="toggleQuoteForm(r)">
              <i class="fa-solid fa-file-invoice"></i> {{ openQuoteForm[r.id] ? "Fermer" : (r.latest_quote ? "Envoyer un nouveau devis" : "Envoyer un devis") }}
            </button>
            <button class="ie-btn ie-btn-danger ie-btn-sm" :disabled="submitting[r.id]" @click="declineRequest(r)">
              <i class="fa-solid fa-xmark"></i> Refuser la demande
            </button>
          </div>

          <form v-if="openQuoteForm[r.id]" @submit.prevent="sendQuote(r)" class="ie-quote-form">
            <label class="ie-label">Lignes de prestation</label>
            <div v-for="(item, idx) in quoteDrafts[r.id].items" :key="idx" class="ie-quote-item-form-row">
              <input v-model="item.label" class="ie-input" placeholder="Ex : Décoration de salle" required />
              <input v-model.number="item.quantity" type="number" min="1" class="ie-input" style="max-width: 80px;" />
              <input v-model.number="item.unit_price" type="number" min="0" class="ie-input" style="max-width: 140px;" placeholder="Prix unitaire" />
              <button type="button" class="ie-btn ie-btn-danger ie-btn-sm" @click="removeItem(r.id, idx)" :disabled="quoteDrafts[r.id].items.length <= 1">
                <i class="fa-solid fa-trash"></i>
              </button>
            </div>
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" style="margin-top: 6px;" @click="addItem(r.id)">
              <i class="fa-solid fa-plus"></i> Ajouter une ligne
            </button>

            <div class="ie-form-row" style="margin-top: 14px;">
              <div>
                <label class="ie-label">Frais de déplacement</label>
                <input v-model.number="quoteDrafts[r.id].travel_fee" type="number" min="0" class="ie-input" />
              </div>
              <div>
                <label class="ie-label">Frais supplémentaires</label>
                <input v-model.number="quoteDrafts[r.id].additional_fees" type="number" min="0" class="ie-input" />
              </div>
              <div>
                <label class="ie-label">Remise</label>
                <input v-model.number="quoteDrafts[r.id].discount" type="number" min="0" class="ie-input" />
              </div>
              <div>
                <label class="ie-label">Devise</label>
                <select v-model="quoteDrafts[r.id].currency" class="ie-select">
                  <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
                </select>
              </div>
            </div>

            <label class="ie-label" style="margin-top: 12px;">Conditions de prestation</label>
            <textarea v-model="quoteDrafts[r.id].conditions" class="ie-input" rows="2"></textarea>
            <label class="ie-label" style="margin-top: 12px;">Conditions d'annulation</label>
            <textarea v-model="quoteDrafts[r.id].cancellation_policy" class="ie-input" rows="2"></textarea>
            <div class="ie-form-row" style="margin-top: 12px;">
              <div>
                <label class="ie-label">Valable jusqu'au</label>
                <input v-model="quoteDrafts[r.id].valid_until" type="date" class="ie-input" />
              </div>
            </div>
            <label class="ie-label" style="margin-top: 12px;">Message pour le client</label>
            <textarea v-model="quoteDrafts[r.id].provider_note" class="ie-input" rows="2" placeholder="Répondez à sa question, précisez votre proposition..."></textarea>

            <div class="ie-quote-form-total">
              Total du devis : <strong>{{ draftTotal(quoteDrafts[r.id]).toLocaleString('fr-FR') }} {{ quoteDrafts[r.id].currency }}</strong>
            </div>

            <p v-if="errors[r.id]" class="ie-alert ie-alert-danger" style="margin-top: 10px;">{{ errors[r.id] }}</p>
            <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 12px;" :disabled="submitting[r.id]">
              <i class="fa-solid fa-paper-plane"></i> {{ submitting[r.id] ? "Envoi…" : "Envoyer ce devis" }}
            </button>
          </form>
        </template>
      </div>
    </div>

    <EmptyState v-else icon="fa-solid fa-file-invoice" text="Aucune demande de devis reçue pour le moment." />
  </div>
</template>

<style scoped>
.ie-alert-warning { background: var(--ie-warning-soft); color: var(--ie-warning); }
.ie-requested-equipment { margin-top: 10px; padding: 10px 12px; background: #FAFBFC; border: 1px solid var(--ie-line); border-radius: 8px; font-size: 12.5px; color: var(--ie-navy); }
.ie-requested-equipment ul { list-style: none; margin: 6px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px 16px; }
.ie-requested-equipment li { font-size: 12px; color: var(--ie-ink); }
.ie-quote-summary { margin-top: 12px; padding: 10px 12px; background: var(--ie-navy-soft); border-radius: 8px; font-size: 13px; color: var(--ie-navy); }
.ie-payout-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--ie-muted); margin-top: 6px; }
.ie-payout-net { font-weight: 700; color: var(--ie-success); font-size: 13px; padding-top: 6px; border-top: 1px dashed var(--ie-line); }
.ie-quote-form { margin-top: 14px; padding: 14px; background: var(--ie-navy-soft); border-radius: 10px; }
.ie-quote-item-form-row { display: flex; gap: 8px; margin-top: 6px; align-items: center; }
.ie-quote-form-total { margin-top: 14px; font-size: 14px; color: var(--ie-red); text-align: right; }
</style>
