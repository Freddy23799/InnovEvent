<script setup>
import { onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";

const payments = ref([]);
const loading = ref(true);
const statusFilter = ref("");

const STATUS_LABELS = { pending: "En attente", completed: "Complété", failed: "Échoué", refunded: "Remboursé" };
const STATUS_BADGE = { pending: "ie-badge-warning", completed: "ie-badge-success", failed: "ie-badge-danger", refunded: "ie-badge-neutral" };
const PROVIDER_LABELS = { paypal: "PayPal", mobile_money: "Mobile Money", freemopay: "FreemoPay", kob: "KOB", demo: "Démonstration" };

async function loadPayments() {
  loading.value = true;
  try {
    const params = {};
    if (statusFilter.value) params.status = statusFilter.value;
    const { data } = await api.get("/payments/", { params });
    payments.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

const downloadingReport = ref(false);

async function downloadReport() {
  downloadingReport.value = true;
  try {
    const params = {};
    if (statusFilter.value) params.status = statusFilter.value;
    const response = await api.get("/payments/report/", { params, responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "rapport-paiements.pdf";
    link.click();
    window.URL.revokeObjectURL(url);
  } finally {
    downloadingReport.value = false;
  }
}

onMounted(loadPayments);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-credit-card" style="color: var(--ie-red); margin-right: 8px;"></i>Paiements</h1>
        <p class="ie-page-subtitle">Historique des transactions, toutes passerelles confondues.</p>
      </div>
      <div class="ie-page-header-actions">
        <select v-model="statusFilter" class="ie-select" style="width: 200px;" @change="loadPayments">
          <option value="">Tous les statuts</option>
          <option value="pending">En attente</option>
          <option value="completed">Complété</option>
          <option value="failed">Échoué</option>
          <option value="refunded">Remboursé</option>
        </select>
        <button class="ie-btn ie-btn-secondary" @click="downloadReport" :disabled="downloadingReport">
          <i class="fa-solid fa-file-pdf"></i> {{ downloadingReport ? "Génération…" : "Rapport PDF" }}
        </button>
      </div>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="payments.length">
        <table class="ie-table">
          <thead>
            <tr><th>Référence</th><th>Utilisateur</th><th class="ie-num">Montant</th><th>Passerelle</th><th>Statut</th><th>Date</th></tr>
          </thead>
          <tbody>
            <tr v-for="payment in payments" :key="payment.id">
              <td style="font-family: monospace; font-size: 12px;">{{ payment.transaction_ref }}</td>
              <td>{{ payment.user_name }}</td>
              <td class="ie-num">{{ Number(payment.amount).toLocaleString('fr-FR') }} {{ payment.currency }}</td>
              <td>{{ PROVIDER_LABELS[payment.provider] || payment.provider }}</td>
              <td>
                <span class="ie-badge" :class="STATUS_BADGE[payment.status] || 'ie-badge-neutral'">
                  {{ STATUS_LABELS[payment.status] || payment.status }}
                </span>
              </td>
              <td>{{ new Date(payment.created_at).toLocaleString('fr-FR') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-credit-card" text="Aucun paiement enregistré." />
    </div>
  </div>
</template>
