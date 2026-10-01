<script setup>
import { computed, reactive, ref, watch } from "vue";
import mastercardLogo from "../assets/images/payment/mastercard.svg";
import mtnLogo from "../assets/images/payment/mtn.svg";
import orangeMoneyLogo from "../assets/images/payment/orange-money.svg";
import visaLogo from "../assets/images/payment/visa.svg";
import api from "../services/api";

const props = defineProps({
  booking: { type: Object, required: true },
});
const emit = defineEmits(["close", "paid"]);

// Mêmes moyens de paiement, dans le même ordre, que la Marketplace (Mobile
// Money en premier — le plus utilisé au Cameroun — puis carte, puis PayPal).
const PAYMENT_METHODS = [
  { value: "mtn_momo", label: "MTN Mobile Money", logos: [mtnLogo] },
  { value: "orange_money", label: "Orange Money", logos: [orangeMoneyLogo] },
  { value: "card", label: "Carte bancaire", logos: [visaLogo, mastercardLogo] },
  { value: "paypal", label: "PayPal", logos: [] },
];

const selectedPayment = ref("mtn_momo");
const phoneNumber = ref("");
const submitting = ref(false);
const errorMessage = ref("");
const success = ref(false);
const cardFields = reactive({ number: "", expiry: "", cvv: "", name: "" });

const couponCode = ref("");
const appliedCoupon = ref(null);
const couponError = ref("");
const validatingCoupon = ref(false);

const discountedTotal = computed(() => {
  if (!appliedCoupon.value) return Number(props.booking.estimated_cost);
  return Number(appliedCoupon.value.final_amount);
});

async function applyCoupon() {
  couponError.value = "";
  appliedCoupon.value = null;
  if (!couponCode.value.trim()) return;
  validatingCoupon.value = true;
  try {
    const { data } = await api.post("/referrals/coupons/validate/", {
      coupon_code: couponCode.value.trim(), amount: props.booking.estimated_cost,
    });
    appliedCoupon.value = data;
  } catch (e) {
    couponError.value = e?.response?.data?.coupon_code?.[0] || e?.response?.data?.detail || "Ce code n'est pas valide.";
  } finally {
    validatingCoupon.value = false;
  }
}

const requiresPhone = computed(() => selectedPayment.value === "mtn_momo" || selectedPayment.value === "orange_money");
const requiresCard = computed(() => selectedPayment.value === "card");

watch(selectedPayment, () => { phoneNumber.value = ""; Object.assign(cardFields, { number: "", expiry: "", cvv: "", name: "" }); });

const canSubmit = computed(() => {
  if (requiresPhone.value) return phoneNumber.value.trim().length >= 9;
  if (requiresCard.value) {
    return Boolean(cardFields.number.trim() && cardFields.expiry.trim() && cardFields.cvv.trim() && cardFields.name.trim());
  }
  return true;
});

async function confirmPayment() {
  errorMessage.value = "";
  if (!canSubmit.value) {
    errorMessage.value = requiresPhone.value
      ? "Entrez un numéro de téléphone valide pour ce moyen de paiement."
      : "Complétez les informations de votre carte bancaire.";
    return;
  }
  submitting.value = true;
  try {
    const payload = { payment_provider: selectedPayment.value };
    if (appliedCoupon.value) payload.coupon_code = couponCode.value.trim();
    const { data } = await api.post(`/bookings/${props.booking.id}/pay/`, payload);
    success.value = true;
    setTimeout(() => emit("paid", data), 1200);
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
        <p>Votre réservation « {{ booking.resource_label }} » est confirmée.</p>
      </div>

      <template v-else>
        <div class="ie-checkout-header">
          <span class="ie-checkout-eyebrow">Réservation</span>
          <h2>{{ booking.resource_label }}</h2>
          <p class="ie-checkout-context">
            {{ new Date(booking.start_datetime).toLocaleString('fr-FR') }} → {{ new Date(booking.end_datetime).toLocaleString('fr-FR') }}
          </p>
        </div>

        <section class="ie-checkout-section">
          <h3>Choisissez votre moyen de paiement</h3>
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

        <section class="ie-checkout-section">
          <h3>J'ai un code de réduction</h3>
          <div style="display: flex; gap: 8px;">
            <input v-model="couponCode" class="ie-input" placeholder="Ex : REF-5PCT-8F72K" style="flex: 1;" />
            <button type="button" class="ie-btn ie-btn-ghost ie-btn-sm" :disabled="validatingCoupon" @click="applyCoupon">
              {{ validatingCoupon ? "…" : "Appliquer" }}
            </button>
          </div>
          <p v-if="couponError" class="ie-field-hint" style="color: var(--ie-red);">{{ couponError }}</p>
          <p v-else-if="appliedCoupon" class="ie-field-hint" style="color: var(--ie-success, #1E7B4D);">
            Code appliqué : -{{ Number(appliedCoupon.discount_amount).toLocaleString('fr-FR') }} XAF ({{ appliedCoupon.discount_percent }}%).
          </p>
        </section>

        <p v-if="errorMessage" class="ie-alert ie-alert-danger">{{ errorMessage }}</p>

        <div class="ie-checkout-footer">
          <div class="ie-checkout-total">
            <span>Total</span>
            <strong>{{ discountedTotal.toLocaleString('fr-FR') }} XAF</strong>
          </div>
          <button type="button" class="ie-btn ie-btn-primary ie-checkout-submit" :disabled="submitting || !canSubmit" @click="confirmPayment">
            <i class="fa-solid fa-lock"></i> {{ submitting ? "Paiement en cours…" : `Payer ${discountedTotal.toLocaleString('fr-FR')} XAF` }}
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
  position: relative; background: #fff; border-radius: 18px; max-width: 480px; width: 100%;
  padding: 32px; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.3); max-height: min(90vh, 90dvh); overflow-y: auto; overscroll-behavior: contain;
}
.ie-checkout-close {
  position: absolute; top: 16px; right: 16px; width: 32px; height: 32px; border-radius: 999px;
  border: 0; background: var(--ie-navy-soft); color: var(--ie-navy); cursor: pointer; font-size: 14px;
}
.ie-checkout-close:hover { background: var(--ie-red-soft); color: var(--ie-red); }

.ie-checkout-header { margin-bottom: 24px; }
.ie-checkout-eyebrow { font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ie-red); }
.ie-checkout-header h2 { margin: 4px 0 0; font-size: 20px; color: var(--ie-navy); }
.ie-checkout-context { margin: 4px 0 0; font-size: 12px; color: var(--ie-muted); }

.ie-checkout-section { margin-bottom: 26px; }
.ie-checkout-section h3 { font-size: 13px; color: var(--ie-navy); margin: 0 0 12px; font-weight: 700; }

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
  .ie-checkout-payments { grid-template-columns: 1fr; }
  .ie-checkout-backdrop { align-items: flex-end; padding: 10px; padding-bottom: max(10px, env(safe-area-inset-bottom)); }
  .ie-checkout-modal { padding: 20px 16px; border-radius: 16px; max-height: 92vh; max-height: 92dvh; }
}
</style>
