<script setup>
import { computed, reactive, ref, watch } from "vue";
import mastercardLogo from "../assets/images/payment/mastercard.svg";
import mtnLogo from "../assets/images/payment/mtn.svg";
import orangeMoneyLogo from "../assets/images/payment/orange-money.svg";
import visaLogo from "../assets/images/payment/visa.svg";
import api from "../services/api";

const props = defineProps({
  marketplaceType: { type: String, required: true },
  marketplaceLabel: { type: String, required: true },
  plans: { type: Array, required: true },
  tiers: { type: Array, default: () => [] },
});
const emit = defineEmits(["close", "subscribed"]);

// Moyens de paiement disponibles au Cameroun — Mobile Money en premier (le
// plus utilisé), puis carte bancaire internationale, puis PayPal en secours.
const PAYMENT_METHODS = [
  { value: "mtn_momo", label: "MTN Mobile Money", logos: [mtnLogo] },
  { value: "orange_money", label: "Orange Money", logos: [orangeMoneyLogo] },
  { value: "card", label: "Carte bancaire", logos: [visaLogo, mastercardLogo] },
  { value: "paypal", label: "PayPal", logos: [] },
];

const selectedPlanCode = ref(props.plans.find((p) => p.code === "1_month")?.code || props.plans[0]?.code);
const selectedTierId = ref(props.tiers.find((tr) => tr.is_default)?.id ?? props.tiers[0]?.id ?? null);
const selectedPayment = ref("mtn_momo");
const phoneNumber = ref("");
const submitting = ref(false);
const errorMessage = ref("");
const success = ref(false);

const selectedPlan = computed(() => props.plans.find((p) => p.code === selectedPlanCode.value));
const monthlyEquivalent = computed(() => {
  if (!selectedPlan.value) return 0;
  return Math.round(selectedPlan.value.price / selectedPlan.value.months);
});
const requiresPhone = computed(() => selectedPayment.value === "mtn_momo" || selectedPayment.value === "orange_money");
const requiresCard = computed(() => selectedPayment.value === "card");
const cardFields = reactive({ number: "", expiry: "", cvv: "", name: "" });

// Un abonnement en cours change de méthode de paiement : on efface les
// champs de l'ancienne pour ne pas soumettre des informations obsolètes.
watch(selectedPayment, () => { phoneNumber.value = ""; Object.assign(cardFields, { number: "", expiry: "", cvv: "", name: "" }); });

// Le paiement (même simulé) exige les informations correspondant au moyen
// choisi : un numéro de téléphone pour Mobile Money, les champs de carte pour
// une carte bancaire — jamais de paiement « à vide ».
const canSubmit = computed(() => {
  if (requiresPhone.value) return phoneNumber.value.trim().length >= 9;
  if (requiresCard.value) {
    return Boolean(cardFields.number.trim() && cardFields.expiry.trim() && cardFields.cvv.trim() && cardFields.name.trim());
  }
  return true;
});

async function confirmSubscription() {
  errorMessage.value = "";
  if (!canSubmit.value) {
    errorMessage.value = requiresPhone.value
      ? "Entrez un numéro de téléphone valide pour ce moyen de paiement."
      : "Complétez les informations de votre carte bancaire.";
    return;
  }
  submitting.value = true;
  try {
    const { data } = await api.post("/marketplace/subscriptions/", {
      marketplace_type: props.marketplaceType,
      plan: selectedPlanCode.value,
      payment_provider: selectedPayment.value,
      tier: selectedTierId.value,
    });
    success.value = true;
    setTimeout(() => emit("subscribed", data), 1200);
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || "Le paiement a échoué. Réessayez ou choisissez un autre moyen de paiement.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="ie-checkout-backdrop" @click.self="$emit('close')">
    <div class="ie-checkout-modal">
      <button type="button" class="ie-checkout-close" @click="$emit('close')" aria-label="Fermer">
        <i class="fa-solid fa-xmark"></i>
      </button>

      <div v-if="success" class="ie-checkout-success">
        <i class="fa-solid fa-circle-check"></i>
        <h2>Paiement confirmé</h2>
        <p>Votre abonnement « {{ marketplaceLabel }} » est actif.</p>
      </div>

      <template v-else>
        <div class="ie-checkout-header">
          <span class="ie-checkout-eyebrow">Abonnement</span>
          <h2>{{ marketplaceLabel }}</h2>
        </div>

        <section class="ie-checkout-section">
          <h3>1. Choisissez la durée</h3>
          <div class="ie-checkout-plans">
            <button
              v-for="plan in plans" :key="plan.code" type="button"
              class="ie-checkout-plan" :class="{ 'is-selected': selectedPlanCode === plan.code }"
              @click="selectedPlanCode = plan.code"
            >
              <span v-if="plan.discount_percent" class="ie-checkout-plan-badge">-{{ plan.discount_percent }}%</span>
              <strong>{{ plan.label }}</strong>
              <span class="ie-checkout-plan-price">{{ Number(plan.price).toLocaleString('fr-FR') }} {{ plan.currency }}</span>
              <span class="ie-checkout-plan-sub">soit {{ Math.round(plan.price / plan.months).toLocaleString('fr-FR') }} {{ plan.currency }}/mois</span>
            </button>
          </div>
        </section>

        <section v-if="tiers.length > 1" class="ie-checkout-section">
          <h3>2. Choisissez votre formule</h3>
          <div class="ie-checkout-tiers">
            <button
              v-for="tier in tiers" :key="tier.id" type="button"
              class="ie-checkout-tier" :class="{ 'is-selected': selectedTierId === tier.id }"
              @click="selectedTierId = tier.id"
            >
              <span v-if="tier.is_default" class="ie-checkout-tier-badge">Recommandée</span>
              <strong>{{ tier.label }}</strong>
              <span v-if="tier.description" class="ie-checkout-tier-desc">{{ tier.description }}</span>
            </button>
          </div>
        </section>

        <section class="ie-checkout-section">
          <h3>3. Choisissez votre moyen de paiement</h3>
          <div class="ie-checkout-payments">
            <button
              v-for="method in PAYMENT_METHODS" :key="method.value" type="button"
              class="ie-checkout-payment" :class="{ 'is-selected': selectedPayment === method.value }"
              @click="selectedPayment = method.value"
            >
              <div class="ie-checkout-payment-logos">
                <img v-for="(logo, i) in method.logos" :key="i" :src="logo" :alt="method.label" />
                <i v-if="!method.logos.length" class="fa-brands fa-paypal"></i>
              </div>
              <span>{{ method.label }}</span>
            </button>
          </div>

          <div v-if="requiresPhone" class="ie-checkout-field">
            <label class="ie-label">Numéro {{ selectedPayment === 'mtn_momo' ? 'MTN' : 'Orange' }} <span class="ie-required">*</span></label>
            <input v-model="phoneNumber" class="ie-input" placeholder="Ex : 6XX XXX XXX" required />
            <p class="ie-field-hint">Requis pour confirmer le paiement {{ selectedPayment === 'mtn_momo' ? 'MTN Mobile Money' : 'Orange Money' }}.</p>
          </div>
          <div v-else-if="requiresCard" class="ie-checkout-card-fields">
            <div class="ie-form-row">
              <div>
                <label class="ie-label">Numéro de carte <span class="ie-required">*</span></label>
                <input v-model="cardFields.number" class="ie-input" placeholder="•••• •••• •••• ••••" maxlength="19" required />
              </div>
              <div>
                <label class="ie-label">Titulaire <span class="ie-required">*</span></label>
                <input v-model="cardFields.name" class="ie-input" placeholder="NOM Prénom" required />
              </div>
            </div>
            <div class="ie-form-row" style="margin-top: 10px;">
              <div>
                <label class="ie-label">Expiration <span class="ie-required">*</span></label>
                <input v-model="cardFields.expiry" class="ie-input" placeholder="MM/AA" maxlength="5" required />
              </div>
              <div>
                <label class="ie-label">CVV <span class="ie-required">*</span></label>
                <input v-model="cardFields.cvv" class="ie-input" placeholder="•••" maxlength="4" required />
              </div>
            </div>
          </div>
        </section>

        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>

        <div class="ie-checkout-footer">
          <div class="ie-checkout-total">
            <span>Total</span>
            <strong>{{ selectedPlan ? Number(selectedPlan.price).toLocaleString('fr-FR') : 0 }} XAF</strong>
          </div>
          <button type="button" class="ie-btn ie-btn-primary ie-checkout-submit" :disabled="submitting || !canSubmit" @click="confirmSubscription">
            <i class="fa-solid fa-lock"></i> {{ submitting ? "Paiement en cours…" : `Payer ${selectedPlan ? Number(selectedPlan.price).toLocaleString('fr-FR') : 0} XAF` }}
          </button>
          <p class="ie-checkout-secure"><i class="fa-solid fa-shield-halved"></i> Paiement sécurisé — aucune donnée bancaire n'est stockée sur InnovEvent.</p>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.ie-checkout-backdrop {
  position: fixed; inset: 0; background: rgba(23, 27, 38, 0.6); z-index: 200;
  display: flex; align-items: center; justify-content: center; padding: 20px; overflow-y: auto;
}
.ie-checkout-modal {
  position: relative; background: #fff; border-radius: 18px; max-width: 560px; width: 100%;
  padding: 32px; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.3); max-height: min(90vh, 90dvh); overflow-y: auto; overscroll-behavior: contain;
}
.ie-checkout-close {
  position: absolute; top: 16px; right: 16px; width: 32px; height: 32px; border-radius: 999px;
  border: 0; background: var(--ie-navy-soft); color: var(--ie-navy); cursor: pointer; font-size: 14px;
}
.ie-checkout-close:hover { background: var(--ie-red-soft); color: var(--ie-red); }

.ie-checkout-header { margin-bottom: 24px; }
.ie-checkout-eyebrow { font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ie-red); }
.ie-checkout-header h2 { margin: 4px 0 0; font-size: 22px; color: var(--ie-navy); }

.ie-checkout-section { margin-bottom: 26px; }
.ie-checkout-section h3 { font-size: 13px; color: var(--ie-navy); margin: 0 0 12px; font-weight: 700; }

.ie-checkout-plans { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.ie-checkout-plan {
  position: relative; display: flex; flex-direction: column; gap: 3px; text-align: left;
  background: #fff; border: 1.5px solid var(--ie-line); border-radius: 12px; padding: 14px;
  cursor: pointer; transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ie-checkout-plan:hover { border-color: var(--ie-navy); }
.ie-checkout-plan.is-selected { border-color: var(--ie-red); box-shadow: 0 0 0 3px var(--ie-red-soft); }
.ie-checkout-plan strong { font-size: 13.5px; color: var(--ie-navy); }
.ie-checkout-plan-price { font-size: 16px; font-weight: 800; color: var(--ie-red); }
.ie-checkout-plan-sub { font-size: 10.5px; color: var(--ie-muted); }
.ie-checkout-plan-badge {
  position: absolute; top: -8px; right: 10px; background: var(--ie-red); color: #fff;
  font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 999px;
}

.ie-checkout-tiers { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.ie-checkout-tier {
  position: relative; display: flex; flex-direction: column; gap: 4px; text-align: left;
  background: #fff; border: 1.5px solid var(--ie-line); border-radius: 12px; padding: 14px;
  cursor: pointer; transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ie-checkout-tier:hover { border-color: var(--ie-navy); }
.ie-checkout-tier.is-selected { border-color: var(--ie-red); box-shadow: 0 0 0 3px var(--ie-red-soft); }
.ie-checkout-tier strong { font-size: 13.5px; color: var(--ie-navy); }
.ie-checkout-tier-desc { font-size: 10.5px; color: var(--ie-muted); line-height: 1.4; }
.ie-checkout-tier-badge {
  position: absolute; top: -8px; right: 10px; background: var(--ie-navy); color: #fff;
  font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 999px;
}

.ie-checkout-payments { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 12px; }
.ie-checkout-payment {
  display: flex; align-items: center; gap: 10px; background: #fff; border: 1.5px solid var(--ie-line);
  border-radius: 12px; padding: 12px; cursor: pointer; transition: border-color 0.15s ease, box-shadow 0.15s ease;
  font-size: 12.5px; font-weight: 600; color: var(--ie-ink);
}
.ie-checkout-payment:hover { border-color: var(--ie-navy); }
.ie-checkout-payment.is-selected { border-color: var(--ie-red); box-shadow: 0 0 0 3px var(--ie-red-soft); }
.ie-checkout-payment-logos { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.ie-checkout-payment-logos img { height: 20px; width: auto; max-width: 34px; object-fit: contain; }
.ie-checkout-payment-logos i { font-size: 20px; color: #003087; }
.ie-checkout-field { margin-top: 4px; }
.ie-required { color: var(--ie-red); }
.ie-checkout-card-fields { margin-top: 4px; }

.ie-checkout-footer { border-top: 1px solid var(--ie-line); padding-top: 18px; }
.ie-checkout-total { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.ie-checkout-total span { font-size: 13px; color: var(--ie-muted); font-weight: 600; }
.ie-checkout-total strong { font-size: 22px; color: var(--ie-navy); }
.ie-checkout-submit { width: 100%; padding: 13px; font-size: 14px; }
.ie-checkout-secure { text-align: center; font-size: 11px; color: var(--ie-muted); margin: 10px 0 0; }

.ie-checkout-success { text-align: center; padding: 30px 10px; }
.ie-checkout-success i { font-size: 48px; color: var(--ie-success, #1E7B4D); margin-bottom: 14px; }
.ie-checkout-success h2 { color: var(--ie-navy); margin: 0 0 6px; }
.ie-checkout-success p { color: var(--ie-muted); margin: 0; }

@media (max-width: 480px) {
  .ie-checkout-plans, .ie-checkout-tiers, .ie-checkout-payments { grid-template-columns: 1fr; }
  .ie-checkout-backdrop { align-items: flex-end; padding: 10px; padding-bottom: max(10px, env(safe-area-inset-bottom)); }
  .ie-checkout-modal { padding: 20px 16px; border-radius: 16px; max-height: 92vh; max-height: 92dvh; }
}
</style>
