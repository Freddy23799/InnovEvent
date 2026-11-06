<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import logo from "../../assets/images/logo-mark.png";
import EmptyState from "../../components/EmptyState.vue";
import ShopBar from "../../components/shop/ShopBar.vue";
import { formatDay, formatMoney } from "../../data/saleCategories";
import api from "../../services/api";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";

const route = useRoute();
const auth = useAuthStore();
const toast = useToastStore();

const order = ref(null);
const loading = ref(true);
const notFound = ref(false);
const downloading = ref(false);
const updating = ref(false);
const isNew = computed(() => route.query.new === "1");
const pieces = computed(() => order.value?.items.reduce((sum, item) => sum + item.quantity, 0) || 0);

async function loadOrder() {
  loading.value = true;
  try {
    const { data } = await api.get(`/marketplace/sale-orders/${route.params.id}/`);
    order.value = data;
  } catch (e) {
    if (e?.response?.status === 404) notFound.value = true;
    else throw e;
  } finally {
    loading.value = false;
  }
}

async function downloadPdf() {
  downloading.value = true;
  try {
    const response = await api.get(`/marketplace/sale-orders/${order.value.id}/pdf/`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `facture-${order.value.number}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    toast.error("Impossible de télécharger la facture pour le moment.");
  } finally {
    downloading.value = false;
  }
}

async function setStatus(status) {
  if (status === "cancelled" && !confirm(isRental.value ? "Annuler cette location ? Les pièces réservées seront libérées." : "Annuler cette commande ? Les pièces reviendront en stock.")) return;
  updating.value = true;
  try {
    const { data } = await api.post(`/marketplace/sale-orders/${order.value.id}/set-status/`, { status });
    order.value = data;
    toast.success(status === "paid" ? "Facture marquée comme payée." : "Commande annulée.");
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible de modifier le statut.");
  } finally {
    updating.value = false;
  }
}

const isRental = computed(() => order.value?.order_type === "rental");
const RENTAL_STEPS = [
  { value: "reserved", label: "Réservée", icon: "fa-solid fa-calendar-check" },
  { value: "out", label: "Sortie / livrée", icon: "fa-solid fa-truck-fast" },
  { value: "returned", label: "Retournée", icon: "fa-solid fa-warehouse" },
];
const rentalStepIndex = computed(() => RENTAL_STEPS.findIndex((step) => step.value === order.value?.rental_status));
const damagedTotal = computed(() => order.value?.items.reduce((sum, i) => sum + i.damaged_quantity + i.lost_quantity, 0) || 0);

async function markOut() {
  updating.value = true;
  try {
    const { data } = await api.post(`/marketplace/sale-orders/${order.value.id}/mark-out/`);
    order.value = data;
    toast.success("Matériel marqué comme sorti.");
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible de modifier la location.");
  } finally {
    updating.value = false;
  }
}

// Retour : saisie des pièces abîmées / perdues par ligne.
const returnForm = ref(null);
function openReturn() {
  returnForm.value = {
    notes: "",
    items: order.value.items.map((item) => ({ item: item.id, title: item.title, quantity: item.quantity, damaged_quantity: 0, lost_quantity: 0 })),
  };
}
async function submitReturn() {
  updating.value = true;
  try {
    const { data } = await api.post(`/marketplace/sale-orders/${order.value.id}/mark-returned/`, {
      notes: returnForm.value.notes,
      items: returnForm.value.items.map(({ item, damaged_quantity, lost_quantity }) => ({ item, damaged_quantity: damaged_quantity || 0, lost_quantity: lost_quantity || 0 })),
    });
    order.value = data;
    returnForm.value = null;
    toast.success("Retour enregistré. Le stock a été mis à jour.");
  } catch (e) {
    toast.error(e?.response?.data?.detail || "Impossible d'enregistrer le retour.");
  } finally {
    updating.value = false;
  }
}

function printInvoice() {
  window.print();
}

function formatDate(value) {
  return new Date(value).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
}

onMounted(loadOrder);
</script>

<template>
  <div class="ie-invoice-page">
    <ShopBar :crumbs="[{ label: 'Mes commandes', to: { name: 'sale-orders' } }, ...(order ? [{ label: order.number }] : [])]" />

    <div v-if="loading" class="ie-skeleton" style="height: 520px; border-radius: 18px;" aria-busy="true"></div>
    <EmptyState v-else-if="notFound" icon="fa-solid fa-file-circle-xmark" text="Cette facture est introuvable." />

    <template v-else-if="order">
      <div v-if="isNew" class="ie-invoice-success">
        <span><i class="fa-solid fa-check"></i></span>
        <div>
          <strong>Commande enregistrée !</strong>
          <p>Votre facture {{ order.number }} est prête. L'équipe InnovEvent vous contacte au {{ order.delivery_phone }} pour la livraison et le paiement.</p>
        </div>
      </div>

      <div class="ie-invoice-actions">
        <button type="button" class="ie-btn ie-btn-primary" :disabled="downloading" @click="downloadPdf">
          <i class="fa-solid fa-file-arrow-down"></i> {{ downloading ? "Préparation…" : "Télécharger en PDF" }}
        </button>
        <button type="button" class="ie-btn ie-btn-ghost" @click="printInvoice"><i class="fa-solid fa-print"></i> Imprimer</button>
        <template v-if="auth.role === 'admin' && order.status !== 'cancelled'">
          <button v-if="isRental && order.rental_status === 'reserved'" type="button" class="ie-btn ie-btn-secondary" :disabled="updating" @click="markOut">
            <i class="fa-solid fa-truck-fast"></i> Marquer sortie / livrée
          </button>
          <button v-if="isRental && order.rental_status === 'out'" type="button" class="ie-btn ie-btn-secondary" :disabled="updating" @click="openReturn">
            <i class="fa-solid fa-warehouse"></i> Enregistrer le retour
          </button>
          <button v-if="order.status === 'pending_payment'" type="button" class="ie-btn ie-btn-secondary" :disabled="updating" @click="setStatus('paid')"><i class="fa-solid fa-circle-check"></i> Marquer payée</button>
          <button
            v-if="order.status === 'pending_payment' && (!isRental || order.rental_status === 'reserved')"
            type="button" class="ie-btn ie-btn-danger" :disabled="updating" @click="setStatus('cancelled')"
          ><i class="fa-solid fa-ban"></i> Annuler</button>
        </template>
        <router-link :to="{ name: 'sale-shop' }" class="ie-btn ie-btn-ghost ie-invoice-continue"><i class="fa-solid fa-store"></i> Continuer mes achats</router-link>
      </div>

      <section v-if="isRental && order.status !== 'cancelled'" class="ie-rental-track">
        <div class="ie-rental-track-head">
          <strong><i class="fa-solid fa-calendar-days"></i> Location du {{ formatDay(order.rental_start) }} au {{ formatDay(order.rental_end) }}</strong>
          <span>{{ order.rental_days }} jour{{ order.rental_days > 1 ? "s" : "" }} · {{ order.delivery_city }}</span>
        </div>
        <ol class="ie-rental-steps">
          <li v-for="(step, index) in RENTAL_STEPS" :key="step.value" :class="{ done: index <= rentalStepIndex, current: index === rentalStepIndex }">
            <span><i :class="step.icon"></i></span>
            <strong>{{ step.label }}</strong>
            <small v-if="step.value === 'out' && order.out_at">{{ formatDate(order.out_at) }}</small>
            <small v-if="step.value === 'returned' && order.returned_at">{{ formatDate(order.returned_at) }}</small>
          </li>
        </ol>
        <p v-if="order.rental_status === 'returned' && damagedTotal" class="ie-rental-damage">
          <i class="fa-solid fa-triangle-exclamation"></i> {{ damagedTotal }} pièce{{ damagedTotal > 1 ? "s" : "" }} abîmée{{ damagedTotal > 1 ? "s" : "" }} ou perdue{{ damagedTotal > 1 ? "s" : "" }} au retour.
          <template v-if="order.return_notes"> {{ order.return_notes }}</template>
        </p>
      </section>

      <div v-if="returnForm" class="ie-return">
        <h3><i class="fa-solid fa-warehouse"></i> Retour du matériel</h3>
        <p class="ie-field-hint">Indiquez les pièces abîmées ou perdues : elles seront retirées du stock. Les autres reviennent automatiquement en disponibilité.</p>
        <div class="ie-return-table">
          <div class="ie-return-row ie-return-header"><span>Produit</span><span>Louées</span><span>Abîmées</span><span>Perdues</span></div>
          <div v-for="line in returnForm.items" :key="line.item" class="ie-return-row">
            <span>{{ line.title }}</span>
            <span>{{ line.quantity }}</span>
            <input v-model.number="line.damaged_quantity" type="number" min="0" :max="line.quantity" class="ie-input" aria-label="Pièces abîmées" />
            <input v-model.number="line.lost_quantity" type="number" min="0" :max="line.quantity" class="ie-input" aria-label="Pièces perdues" />
          </div>
        </div>
        <label class="ie-label" style="margin-top: 12px;">Remarques (optionnel)</label>
        <textarea v-model="returnForm.notes" class="ie-input" rows="2" placeholder="État général, retard, facturation de la casse…"></textarea>
        <div class="ie-return-actions">
          <button type="button" class="ie-btn ie-btn-ghost" @click="returnForm = null">Annuler</button>
          <button type="button" class="ie-btn ie-btn-primary" :disabled="updating" @click="submitReturn"><i class="fa-solid fa-check"></i> Valider le retour</button>
        </div>
      </div>

      <article class="ie-invoice">
        <header class="ie-invoice-head">
          <div class="ie-invoice-brand">
            <img :src="logo" alt="" />
            <div>
              <strong>InnovEvent&amp;Home groupe</strong>
              <span>Boutique de l'événementiel</span>
            </div>
          </div>
          <div class="ie-invoice-id">
            <span>Facture · {{ order.order_type_display }}</span>
            <strong>{{ order.number }}</strong>
            <em class="ie-invoice-status" :class="order.status">{{ order.status_display }}</em>
          </div>
        </header>

        <div class="ie-invoice-meta">
          <div>
            <small>Facturé à</small>
            <strong>{{ order.delivery_name }}</strong>
            <span>{{ order.buyer_email }}</span>
            <span>{{ order.delivery_phone }}</span>
          </div>
          <div>
            <small>{{ isRental ? "Lieu de l'événement" : "Livraison" }}</small>
            <strong>{{ order.delivery_city }}</strong>
            <span class="ie-invoice-address">{{ order.delivery_address }}</span>
          </div>
          <div>
            <small>{{ isRental ? "Période de location" : "Date" }}</small>
            <strong v-if="isRental">{{ formatDay(order.rental_start) }} → {{ formatDay(order.rental_end) }}</strong>
            <strong v-else>{{ formatDate(order.created_at) }}</strong>
            <span v-if="isRental">{{ order.rental_days }} jour{{ order.rental_days > 1 ? "s" : "" }} · commandée le {{ formatDate(order.created_at) }}</span>
            <span>{{ order.paid_at ? `Payée le ${formatDate(order.paid_at)}` : order.status === "cancelled" ? "Commande annulée" : "À payer à la livraison" }}</span>
          </div>
        </div>

        <div class="ie-invoice-table-wrap">
          <table class="ie-invoice-table">
            <thead>
              <tr>
                <th>Produit</th><th class="num">Qté</th>
                <th class="num">{{ isRental ? "Prix / jour" : "Prix unit." }}</th>
                <th v-if="isRental" class="num">Jours</th>
                <th class="num">Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in order.items" :key="item.id">
                <td>
                  <span class="ie-invoice-product">
                    <span class="ie-invoice-thumb">
                      <img v-if="item.photo" v-img="item.photo" :alt="item.title" />
                      <i v-else class="fa-solid fa-box-open"></i>
                    </span>
                    {{ item.title }}
                  </span>
                </td>
                <td class="num">{{ item.quantity }}</td>
                <td class="num">{{ formatMoney(item.unit_price, order.currency) }}</td>
                <td v-if="isRental" class="num">{{ item.days }}</td>
                <td class="num"><strong>{{ formatMoney(item.line_total, order.currency) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="ie-invoice-bottom">
          <div class="ie-invoice-note">
            <template v-if="order.notes"><small>Note</small><p>{{ order.notes }}</p></template>
          </div>
          <div class="ie-invoice-totals">
            <div><span>Sous-total ({{ pieces }} pièce{{ pieces > 1 ? "s" : "" }})</span><span>{{ formatMoney(order.total, order.currency) }}</span></div>
            <div><span>Livraison</span><span>À convenir</span></div>
            <div class="ie-invoice-grand">
              <span>{{ order.status === "pending_payment" ? "Total à payer" : "Total" }}</span>
              <strong>{{ formatMoney(order.total, order.currency) }}</strong>
            </div>
          </div>
        </div>

        <footer class="ie-invoice-foot">Facture émise via la plateforme InnovEvent — règlement auprès d'InnovEvent ou à la livraison.</footer>
      </article>
    </template>
  </div>
</template>

<style scoped>
.ie-invoice-page { max-width: 920px; margin: 0 auto; min-width: 0; }
.ie-invoice-success { display: flex; gap: 14px; align-items: center; margin-bottom: 16px; padding: 16px 18px; border: 1px solid #cfe7d9; border-radius: 14px; background: var(--ie-success-soft); }
.ie-invoice-success > span { display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; border-radius: 50%; background: var(--ie-success); color: #fff; font-size: 18px; }
.ie-invoice-success strong { color: var(--ie-navy); font-size: 15px; }
.ie-invoice-success p { margin: 3px 0 0; color: #4b5a6a; font-size: 13px; }
.ie-invoice-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.ie-invoice-continue { margin-left: auto; }

.ie-rental-track { margin-bottom: 16px; padding: 18px 20px; border: 1px solid var(--ie-line); border-radius: 16px; background: #fff; }
.ie-rental-track-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.ie-rental-track-head strong { color: var(--ie-navy); font-size: 15px; }
.ie-rental-track-head strong i { color: var(--ie-red); margin-right: 6px; }
.ie-rental-track-head span { color: var(--ie-muted); font-size: 13px; }
.ie-rental-steps { display: grid; grid-template-columns: repeat(3, 1fr); margin: 16px 0 0; padding: 0; list-style: none; }
.ie-rental-steps li { position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; }
.ie-rental-steps li + li::before { content: ""; position: absolute; top: 18px; right: 50%; width: 100%; height: 3px; background: var(--ie-line); z-index: 0; }
.ie-rental-steps li.done + li.done::before { background: var(--ie-success); }
.ie-rental-steps span { position: relative; z-index: 1; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; background: #eef0f2; color: var(--ie-muted); }
.ie-rental-steps li.done span { background: var(--ie-success); color: #fff; }
.ie-rental-steps li.current span { box-shadow: 0 0 0 4px var(--ie-success-soft); }
.ie-rental-steps strong { color: var(--ie-navy); font-size: 12.5px; }
.ie-rental-steps small { color: var(--ie-muted); font-size: 11px; }
.ie-rental-damage { margin: 14px 0 0; padding: 9px 12px; border-radius: 10px; background: var(--ie-warning-soft); color: #7a4f00; font-size: 13px; }
.ie-return { margin-bottom: 16px; padding: 18px 20px; border: 2px solid var(--ie-navy); border-radius: 16px; background: #fff; }
.ie-return h3 { margin: 0 0 4px; color: var(--ie-navy); font-size: 16px; }
.ie-return-table { display: grid; gap: 6px; margin-top: 12px; }
.ie-return-row { display: grid; grid-template-columns: minmax(0, 1fr) 70px 90px 90px; gap: 8px; align-items: center; font-size: 13px; }
.ie-return-header { color: var(--ie-muted); font-size: 11px; font-weight: 800; text-transform: uppercase; }
.ie-return-row .ie-input { padding: 6px 8px; }
.ie-return-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.ie-invoice { overflow: hidden; border: 1px solid var(--ie-line); border-radius: 18px; background: #fff; box-shadow: var(--ie-shadow); }
.ie-invoice-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 24px 28px; background: var(--ie-hero-gradient); color: #fff; }
.ie-invoice-brand { display: flex; align-items: center; gap: 12px; }
.ie-invoice-brand img { width: 46px; height: 46px; object-fit: contain; border-radius: 10px; background: #fff; padding: 4px; }
.ie-invoice-brand strong { display: block; font-size: 15px; }
.ie-invoice-brand span { color: #cfd8e2; font-size: 12px; }
.ie-invoice-id { text-align: right; }
.ie-invoice-id span { display: block; color: #cfd8e2; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
.ie-invoice-id strong { display: block; font-size: 20px; letter-spacing: 0.02em; }
.ie-invoice-status { display: inline-block; margin-top: 6px; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 800; font-style: normal; text-transform: uppercase; }
.ie-invoice-status.pending_payment { background: #fff3d6; color: #8a5a00; }
.ie-invoice-status.paid { background: #dff3e7; color: #1e7b4d; }
.ie-invoice-status.cancelled { background: #eceff2; color: #5d6771; }

.ie-invoice-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; padding: 22px 28px; border-bottom: 1px solid var(--ie-line); }
.ie-invoice-meta div { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ie-invoice-meta small, .ie-invoice-note small { color: var(--ie-muted); font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.ie-invoice-meta strong { color: var(--ie-navy); font-size: 14.5px; }
.ie-invoice-meta span { color: #4b5a6a; font-size: 13px; overflow-wrap: anywhere; }
.ie-invoice-address { white-space: pre-line; }

.ie-invoice-table-wrap { overflow-x: auto; padding: 8px 28px 0; }
.ie-invoice-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.ie-invoice-table th { padding: 12px 8px; border-bottom: 2px solid var(--ie-navy); color: var(--ie-navy); font-size: 11px; letter-spacing: 0.06em; text-align: left; text-transform: uppercase; }
.ie-invoice-table td { padding: 12px 8px; border-bottom: 1px solid var(--ie-line); color: var(--ie-ink); }
.ie-invoice-table .num { text-align: right; white-space: nowrap; }
.ie-invoice-product { display: flex; align-items: center; gap: 10px; }
.ie-invoice-thumb { display: grid; place-items: center; width: 40px; height: 40px; flex: 0 0 40px; overflow: hidden; border-radius: 8px; background: #f2f4f6; color: #9aa3ac; }
.ie-invoice-thumb img { width: 100%; height: 100%; object-fit: cover; }

.ie-invoice-bottom { display: grid; grid-template-columns: 1fr minmax(260px, 340px); gap: 20px; padding: 20px 28px 24px; }
.ie-invoice-note p { margin: 4px 0 0; color: #4b5a6a; font-size: 13px; white-space: pre-line; }
.ie-invoice-totals { display: grid; gap: 8px; font-size: 13.5px; color: #4b5a6a; }
.ie-invoice-totals div { display: flex; justify-content: space-between; gap: 10px; }
.ie-invoice-grand { margin-top: 4px; padding: 12px 14px; border-radius: 10px; background: var(--ie-red); color: #fff; font-weight: 700; align-items: baseline; }
.ie-invoice-grand strong { font-size: 20px; }
.ie-invoice-foot { padding: 14px 28px; border-top: 1px solid var(--ie-line); background: #fafbfc; color: var(--ie-muted); font-size: 11.5px; text-align: center; }

@media (max-width: 720px) {
  .ie-invoice-head { flex-direction: column; align-items: flex-start; padding: 20px; }
  .ie-invoice-id { text-align: left; }
  .ie-invoice-meta { grid-template-columns: 1fr; padding: 18px 20px; }
  .ie-invoice-table-wrap { padding: 4px 12px 0; }
  .ie-invoice-thumb { display: none; }
  .ie-invoice-bottom { grid-template-columns: 1fr; padding: 16px 20px 20px; }
  .ie-invoice-continue { margin-left: 0; }
}
@media print {
  .ie-invoice-success, .ie-invoice-actions, .ie-rental-track, .ie-return { display: none; }
  .ie-invoice { box-shadow: none; border: 0; }
}
</style>
