<script setup>
import { onMounted, ref } from "vue";
import KpiCard from "../../components/KpiCard.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const STATUS_META = {
  pending: { label: "En attente", badge: "ie-badge-neutral" },
  converted: { label: "Converti", badge: "ie-badge-success" },
  reversed: { label: "Annulé", badge: "ie-badge-danger" },
};

const loading = ref(true);
const stats = ref(null);
const referrals = ref([]);
const statusFilter = ref("");
const flaggedOnly = ref(false);
const search = ref("");

async function loadStats() {
  const { data } = await api.get("/referrals/admin/referrals/stats/");
  stats.value = data;
}

async function loadReferrals() {
  const params = {};
  if (statusFilter.value) params.status = statusFilter.value;
  if (flaggedOnly.value) params.is_flagged = true;
  if (search.value.trim()) params.search = search.value.trim();
  const { data } = await api.get("/referrals/admin/referrals/", { params });
  referrals.value = data.results || data;
}

async function loadAll() {
  loading.value = true;
  try {
    await Promise.all([loadStats(), loadReferrals()]);
  } finally {
    loading.value = false;
  }
}

async function flagReferral(referral) {
  const reason = prompt("Motif du signalement :", "Activité suspecte");
  if (reason === null) return;
  await api.post(`/referrals/admin/referrals/${referral.id}/flag/`, { reason });
  toast.success("Parrainage signalé.");
  await loadReferrals();
}

async function unflagReferral(referral) {
  await api.post(`/referrals/admin/referrals/${referral.id}/unflag/`);
  toast.success("Signalement levé.");
  await loadReferrals();
}

onMounted(loadAll);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-user-plus" style="color: var(--ie-red); margin-right: 8px;"></i>Gestion des parrainages</h1>
        <p class="ie-page-subtitle">Parrains, filleuls, transactions générées et comptes suspects.</p>
      </div>
    </div>

    <div v-if="stats" class="ie-kpi-grid" style="margin-bottom: 20px;">
      <KpiCard label="Parrains" :value="stats.total_referrers" icon="fa-solid fa-users" />
      <KpiCard label="Filleuls" :value="stats.total_referred" icon="fa-solid fa-user-plus" />
      <KpiCard label="Filleuls actifs" :value="stats.active_referrals" icon="fa-solid fa-circle-check" tone="success" />
      <KpiCard label="Comptes suspects" :value="stats.flagged_referrals" icon="fa-solid fa-triangle-exclamation" tone="warning" />
      <KpiCard label="CA généré (XAF)" :value="Number(stats.revenue_generated).toLocaleString('fr-FR')" icon="fa-solid fa-coins" />
      <KpiCard label="Commission générée (XAF)" :value="Number(stats.commission_generated).toLocaleString('fr-FR')" icon="fa-solid fa-percent" />
      <KpiCard label="Récompenses émises" :value="stats.coupons_issued" icon="fa-solid fa-gift" />
      <KpiCard label="Récompenses utilisées" :value="stats.coupons_used" icon="fa-solid fa-check" tone="success" />
      <KpiCard label="Disponibles" :value="stats.coupons_available" icon="fa-solid fa-hourglass-half" />
      <KpiCard label="Expirées/annulées" :value="stats.coupons_expired" icon="fa-solid fa-ban" tone="warning" />
    </div>

    <div style="display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap;">
      <input v-model="search" class="ie-input" placeholder="Rechercher un utilisateur..." style="max-width: 260px;" @keyup.enter="loadReferrals" />
      <select v-model="statusFilter" class="ie-select" style="max-width: 200px;" @change="loadReferrals">
        <option value="">Tous les statuts</option>
        <option value="pending">En attente</option>
        <option value="converted">Converti</option>
        <option value="reversed">Annulé</option>
      </select>
      <label style="display: flex; align-items: center; gap: 6px; font-size: 13px;">
        <input type="checkbox" v-model="flaggedOnly" @change="loadReferrals" /> Comptes suspects uniquement
      </label>
      <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="loadReferrals"><i class="fa-solid fa-magnifying-glass"></i> Filtrer</button>
    </div>

    <SkeletonTable v-if="loading" :columns="6" />

    <div v-else class="ie-table-wrap">
      <table class="ie-table">
        <thead>
          <tr>
            <th>Parrain</th>
            <th>Filleul</th>
            <th>Statut</th>
            <th>Inscrit le</th>
            <th>Converti le</th>
            <th>Suspect</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in referrals" :key="r.id">
            <td>{{ r.referrer_username }}</td>
            <td>{{ r.referred_username }}</td>
            <td><span class="ie-badge" :class="STATUS_META[r.status]?.badge">{{ STATUS_META[r.status]?.label }}</span></td>
            <td>{{ new Date(r.created_at).toLocaleDateString('fr-FR') }}</td>
            <td>{{ r.converted_at ? new Date(r.converted_at).toLocaleDateString('fr-FR') : '—' }}</td>
            <td>
              <span v-if="r.is_flagged" class="ie-badge ie-badge-danger" :title="r.flag_reason">Signalé</span>
              <span v-else>—</span>
            </td>
            <td>
              <button v-if="!r.is_flagged" class="ie-btn ie-btn-ghost ie-btn-sm" @click="flagReferral(r)">Signaler</button>
              <button v-else class="ie-btn ie-btn-ghost ie-btn-sm" @click="unflagReferral(r)">Lever le signalement</button>
            </td>
          </tr>
          <tr v-if="!referrals.length">
            <td colspan="7" style="text-align: center; color: var(--ie-muted); padding: 24px;">Aucun parrainage trouvé.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
