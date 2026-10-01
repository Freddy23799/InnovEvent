<script setup>
import { onMounted, reactive, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import SkeletonTable from "../../components/SkeletonTable.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();
const ticketTypes = ref([]);
const events = ref([]);
const loading = ref(true);
const showForm = ref(false);
const submitting = ref(false);
const errorMessage = ref("");
const editingId = ref(null);

const emptyForm = { event: "", name: "", price: 0, currency: "XAF", quota: 100, sale_start: "", sale_end: "", is_active: true, is_premium: false };
const form = reactive({ ...emptyForm });

async function loadData() {
  loading.value = true;
  try {
    const [typesRes, eventsRes] = await Promise.all([
      api.get("/tickets/types/"),
      api.get("/events/"),
    ]);
    ticketTypes.value = typesRes.data.results || typesRes.data;
    events.value = eventsRes.data.results || eventsRes.data;
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  Object.assign(form, emptyForm);
  editingId.value = null;
  errorMessage.value = "";
  showForm.value = true;
}

function startEdit(tt) {
  Object.assign(form, {
    event: tt.event, name: tt.name, price: tt.price, currency: tt.currency,
    quota: tt.quota, sale_start: tt.sale_start?.slice(0, 16), sale_end: tt.sale_end?.slice(0, 16),
    is_active: tt.is_active, is_premium: tt.is_premium,
  });
  editingId.value = tt.id;
  errorMessage.value = "";
  showForm.value = true;
}

async function submitForm() {
  errorMessage.value = "";
  submitting.value = true;
  try {
    if (editingId.value) {
      await api.patch(`/tickets/types/${editingId.value}/`, form);
    } else {
      await api.post("/tickets/types/", form);
    }
    showForm.value = false;
    toast.success(editingId.value ? "Modifications enregistrées." : "Type de billet enregistré.");
    await loadData();
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Impossible d'enregistrer ce type de billet.";
  } finally {
    submitting.value = false;
  }
}

async function toggleActive(tt) {
  await api.patch(`/tickets/types/${tt.id}/`, { is_active: !tt.is_active });
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-ticket" style="color: var(--ie-red); margin-right: 8px;"></i>Billetterie</h1>
        <p class="ie-page-subtitle">Types de billets, quotas et périodes de vente par événement.</p>
      </div>
      <div class="ie-page-header-actions">
        <button class="ie-btn ie-btn-primary" @click="showForm ? (showForm = false) : startCreate()">
          <i class="fa-solid" :class="showForm ? 'fa-xmark' : 'fa-plus'"></i> {{ showForm ? "Annuler" : "Nouveau type de billet" }}
        </button>
      </div>
    </div>

    <div v-if="showForm" class="ie-card ie-card-body" style="margin-bottom: 20px;">
      <form @submit.prevent="submitForm">
        <div class="ie-form-row">
          <div>
            <label class="ie-label">Événement</label>
            <select v-model="form.event" class="ie-select" required :disabled="!!editingId">
              <option value="" disabled>Choisir un événement</option>
              <option v-for="ev in events" :key="ev.id" :value="ev.id">{{ ev.title }}</option>
            </select>
          </div>
          <div>
            <label class="ie-label">Nom du billet</label>
            <input v-model="form.name" class="ie-input" required placeholder="Standard, VIP…" />
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Prix</label>
            <input v-model.number="form.price" type="number" min="0" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Devise</label>
            <select v-model="form.currency" class="ie-select">
              <option>XAF</option><option>EUR</option><option>USD</option><option>GBP</option>
            </select>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Quota</label>
            <input v-model.number="form.quota" type="number" min="1" class="ie-input" required />
          </div>
          <div>
            <label style="display:flex; align-items:center; gap:8px; margin-top: 30px; font-size:14px;">
              <input v-model="form.is_active" type="checkbox" /> Actif
            </label>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label style="display:flex; align-items:center; gap:8px; font-size:14px;">
              <input v-model="form.is_premium" type="checkbox" />
              <i class="fa-solid fa-star" style="color:#C8A24A;"></i> Design premium (billet PDF avec visuel VIP/prestige)
            </label>
          </div>
        </div>
        <div class="ie-form-row" style="margin-top: 14px;">
          <div>
            <label class="ie-label">Début des ventes</label>
            <input v-model="form.sale_start" type="datetime-local" class="ie-input" required />
          </div>
          <div>
            <label class="ie-label">Fin des ventes</label>
            <input v-model="form.sale_end" type="datetime-local" class="ie-input" required />
          </div>
        </div>
        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>
        <button class="ie-btn ie-btn-primary" type="submit" style="margin-top: 16px;" :disabled="submitting">
          {{ submitting ? "Enregistrement…" : editingId ? "Mettre à jour" : "Créer" }}
        </button>
      </form>
    </div>

    <div class="ie-card">
      <SkeletonTable v-if="loading" />
      <div class="ie-table-wrap" v-else-if="ticketTypes.length">
        <table class="ie-table">
          <thead>
            <tr>
              <th>Événement</th><th>Billet</th><th class="ie-num">Prix</th><th class="ie-num">Quota</th>
              <th class="ie-num">Vendus</th><th class="ie-num">Restants</th><th>Statut</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tt in ticketTypes" :key="tt.id">
              <td>{{ tt.event_title }}</td>
              <td>
                <strong>{{ tt.name }}</strong>
                <i v-if="tt.is_premium" class="fa-solid fa-star" style="color:#C8A24A; margin-left:6px;" title="Design premium"></i>
              </td>
              <td class="ie-num">{{ Number(tt.price).toLocaleString('fr-FR') }} {{ tt.currency }}</td>
              <td class="ie-num">{{ tt.quota }}</td>
              <td class="ie-num">{{ tt.sold_count }}</td>
              <td class="ie-num">{{ tt.remaining_quota }}</td>
              <td>
                <span class="ie-badge" :class="tt.is_active ? 'ie-badge-success' : 'ie-badge-neutral'">
                  {{ tt.is_active ? "Active" : "Inactive" }}
                </span>
              </td>
              <td class="ie-table-actions">
                <button class="ie-btn ie-btn-ghost ie-btn-sm" @click="startEdit(tt)">Modifier</button>
                <button class="ie-btn ie-btn-secondary ie-btn-sm" @click="toggleActive(tt)">
                  {{ tt.is_active ? "Désactiver" : "Activer" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="fa-solid fa-ticket" text="Aucun type de billet créé pour le moment." />
    </div>
  </div>
</template>
