<script setup>
import { onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";

const logs = ref([]);
const loading = ref(true);
const search = ref("");
const methodFilter = ref("");

const METHOD_BADGE = {
  GET: "ie-badge-neutral", POST: "ie-badge-success",
  PATCH: "ie-badge-warning", PUT: "ie-badge-warning", DELETE: "ie-badge-danger",
};

async function loadLogs() {
  loading.value = true;
  try {
    const params = {};
    if (search.value) params.search = search.value;
    if (methodFilter.value) params.method = methodFilter.value;
    const { data } = await api.get("/audit/logs/", { params });
    logs.value = data.results || data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadLogs);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-shield-halved" style="color: var(--ie-red); margin-right: 8px;"></i>Journal d'activité</h1>
        <p class="ie-page-subtitle">Historique des actions sensibles effectuées sur la plateforme.</p>
      </div>
      <div class="ie-page-header-actions">
        <select v-model="methodFilter" class="ie-select" style="width: 160px;" @change="loadLogs">
          <option value="">Toutes méthodes</option>
          <option value="POST">Création</option>
          <option value="PATCH">Modification</option>
          <option value="PUT">Modification</option>
          <option value="DELETE">Suppression</option>
        </select>
        <input v-model="search" class="ie-input" placeholder="Rechercher une action…" style="width:220px;" @keyup.enter="loadLogs" />
      </div>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="logs.length">
        <table class="ie-table">
          <thead>
            <tr><th>Date</th><th>Utilisateur</th><th>Action</th><th>Méthode</th><th class="ie-num">Statut</th><th>IP</th></tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td>{{ new Date(log.created_at).toLocaleString('fr-FR') }}</td>
              <td>{{ log.actor_name }}</td>
              <td style="font-family: monospace; font-size: 11.5px;">{{ log.action }}</td>
              <td><span class="ie-badge" :class="METHOD_BADGE[log.method] || 'ie-badge-neutral'">{{ log.method || "—" }}</span></td>
              <td class="ie-num">{{ log.status_code || "—" }}</td>
              <td style="font-family: monospace; font-size: 11.5px;">{{ log.ip_address || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-shield-halved" text="Aucune entrée dans le journal." />
    </div>
  </div>
</template>
