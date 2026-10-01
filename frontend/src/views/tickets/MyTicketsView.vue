<script setup>
import { onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useLightboxStore } from "../../stores/lightbox";

const lightbox = useLightboxStore();

const STATUS_LABELS = { valid: "Payé", used: "Utilisé", cancelled: "Annulé" };
const STATUS_BADGE = { valid: "ie-badge-success", used: "ie-badge-neutral", cancelled: "ie-badge-danger" };

const tickets = ref([]);
const loading = ref(true);

async function loadTickets() {
  loading.value = true;
  try {
    const { data } = await api.get("/tickets/my/");
    tickets.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

async function downloadTicketPdf(ticket) {
  const response = await api.get(`/tickets/my/${ticket.id}/pdf/`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `billet-${ticket.code}.pdf`;
  link.click();
  window.URL.revokeObjectURL(url);
}

onMounted(loadTickets);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-ticket" style="color: var(--ie-red); margin-right: 8px;"></i>Mes billets</h1>
        <p class="ie-page-subtitle">Retrouvez vos billets et téléchargez-les au format PDF.</p>
      </div>
      <div class="ie-page-header-actions">
        <router-link :to="{ name: 'marketplace' }" class="ie-btn ie-btn-primary">
          <i class="fa-solid fa-store"></i> Billetterie
        </router-link>
      </div>
    </div>
    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="tickets.length">
        <table class="ie-table">
          <thead>
            <tr><th></th><th>Événement</th><th>Type</th><th>Date</th><th>Lieu</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="ticket in tickets" :key="ticket.id">
              <td>
                <div class="ie-ticket-thumb">
                  <img v-if="ticket.event_photo" :src="ticket.event_photo" :alt="ticket.event_title" class="ie-zoomable" @click="lightbox.open(ticket.event_photo, ticket.event_title)" />
                  <i v-else class="fa-solid fa-ticket"></i>
                </div>
              </td>
              <td><strong>{{ ticket.event_title }}</strong></td>
              <td>
                {{ ticket.ticket_type_name }}
                <span v-if="ticket.is_premium" class="ie-badge ie-ticket-premium-badge"><i class="fa-solid fa-star"></i> Premium</span>
              </td>
              <td>{{ new Date(ticket.event_start_date).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }) }}</td>
              <td>{{ ticket.venue_name || "—" }}</td>
              <td>
                <span class="ie-badge" :class="STATUS_BADGE[ticket.status] || 'ie-badge-neutral'">
                  {{ STATUS_LABELS[ticket.status] || ticket.status }}
                </span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="downloadTicketPdf(ticket)">
                  <i class="fa-solid fa-download"></i> PDF
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="ie-empty-state-wrap">
        <EmptyState icon="fa-solid fa-ticket" text="Vous n'avez pas encore de billet." />
        <router-link :to="{ name: 'marketplace' }" class="ie-btn ie-btn-primary" style="margin-top: 12px;">
          <i class="fa-solid fa-store"></i> Découvrir le marché des événements
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ie-ticket-thumb {
  width: 40px; height: 40px; border-radius: 8px; overflow: hidden;
  background: var(--ie-navy-soft); display: flex; align-items: center; justify-content: center;
}
.ie-ticket-thumb img { width: 100%; height: 100%; object-fit: cover; }
.ie-ticket-thumb i { color: var(--ie-navy); opacity: 0.4; font-size: 14px; }
.ie-empty-state-wrap { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
.ie-ticket-premium-badge { margin-left: 6px; background: #2A2116; color: #C8A24A; }
.ie-ticket-premium-badge i { margin-right: 3px; }
</style>
