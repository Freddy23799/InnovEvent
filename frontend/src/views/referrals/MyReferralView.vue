<script setup>
import { computed, onMounted, ref } from "vue";
import EmptyState from "../../components/EmptyState.vue";
import api from "../../services/api";
import { useToastStore } from "../../stores/toast";

const toast = useToastStore();

const loading = ref(true);
const data = ref(null);

const SHARE_MESSAGE_INTRO = "🎉 Découvrez cette plateforme pour réserver facilement vos services et équipements pour vos événements.";

const referralLink = computed(() => {
  if (!data.value) return "";
  return `${window.location.origin}/register?ref=${data.value.code}`;
});

const shareText = computed(() => {
  if (!referralLink.value) return "";
  return `${SHARE_MESSAGE_INTRO}\n\nInscrivez-vous avec mon lien et profitez de vos avantages :\n${referralLink.value}`;
});

async function loadData() {
  loading.value = true;
  try {
    const { data: response } = await api.get("/referrals/me/");
    data.value = response;
  } finally {
    loading.value = false;
  }
}

async function shareNative() {
  if (navigator.share) {
    try {
      await navigator.share({ title: "Rejoignez-moi sur InnovEvent", text: shareText.value, url: referralLink.value });
    } catch (e) {
      // partage annulé par l'utilisateur — rien à faire
    }
    return;
  }
  await copyLink();
}

function shareWhatsapp() {
  window.open(`https://wa.me/?text=${encodeURIComponent(shareText.value)}`, "_blank");
}

function shareFacebook() {
  window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(referralLink.value)}`, "_blank");
}

function shareSms() {
  window.open(`sms:?body=${encodeURIComponent(shareText.value)}`, "_blank");
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(referralLink.value);
    toast.success("Lien de parrainage copié.");
  } catch (e) {
    toast.error("Impossible de copier le lien.");
  }
}

const COUPON_STATUS_LABELS = { available: "Disponible", used: "Utilisé", expired: "Expiré", cancelled: "Annulé" };

onMounted(loadData);
</script>

<template>
  <div>
    <div class="ie-page-header">
      <div>
        <h1><i class="fa-solid fa-user-plus" style="color: var(--ie-red); margin-right: 8px;"></i>Mon parrainage</h1>
        <p class="ie-page-subtitle">Partagez votre lien, invitez vos amis, gagnez des réductions dès qu'ils réservent.</p>
      </div>
    </div>

    <div v-if="loading" class="ie-skeleton" style="height: 220px;"></div>

    <template v-else-if="data">
      <div class="ie-card ie-card-body ie-referral-hero">
        <div>
          <p class="ie-referral-label">Votre code de parrainage</p>
          <p class="ie-referral-code">{{ data.code }}</p>
          <p class="ie-referral-link">{{ referralLink }}</p>
        </div>
        <div class="ie-referral-actions">
          <button class="ie-btn ie-btn-primary" @click="shareNative">
            <i class="fa-solid fa-share-nodes"></i> Inviter un ami
          </button>
          <div class="ie-referral-share-row">
            <button class="ie-share-btn ie-share-whatsapp" title="WhatsApp" @click="shareWhatsapp"><i class="fa-brands fa-whatsapp"></i></button>
            <button class="ie-share-btn ie-share-facebook" title="Facebook" @click="shareFacebook"><i class="fa-brands fa-facebook"></i></button>
            <button class="ie-share-btn ie-share-sms" title="SMS" @click="shareSms"><i class="fa-solid fa-comment-sms"></i></button>
            <button class="ie-share-btn ie-share-copy" title="Copier le lien" @click="copyLink"><i class="fa-solid fa-copy"></i></button>
          </div>
        </div>
      </div>

      <div class="ie-referral-stats">
        <div class="ie-card ie-card-body ie-referral-stat">
          <span class="ie-referral-stat-value">{{ data.stats.invited }}</span>
          <span class="ie-referral-stat-label">Personnes inscrites</span>
        </div>
        <div class="ie-card ie-card-body ie-referral-stat">
          <span class="ie-referral-stat-value">{{ data.stats.active_referrals }}</span>
          <span class="ie-referral-stat-label">Filleuls actifs (transaction validée)</span>
        </div>
        <div class="ie-card ie-card-body ie-referral-stat">
          <span class="ie-referral-stat-value">{{ data.coupons.available.length }}</span>
          <span class="ie-referral-stat-label">Récompenses disponibles</span>
        </div>
      </div>

      <div v-if="data.campaigns.length" class="ie-card ie-card-body" style="margin-top: 20px;">
        <h3>Votre progression</h3>
        <div v-for="campaign in data.campaigns" :key="campaign.id" class="ie-campaign-progress">
          <p class="ie-campaign-name">{{ campaign.name }}</p>
          <template v-if="campaign.next_tier">
            <div class="ie-progress-bar">
              <div
                class="ie-progress-fill"
                :style="{ width: `${Math.min(100, (campaign.progress / campaign.next_tier.threshold_referrals) * 100)}%` }"
              ></div>
            </div>
            <p class="ie-progress-caption">
              {{ campaign.progress }}/{{ campaign.next_tier.threshold_referrals }} —
              Plus que {{ campaign.next_tier.remaining }} filleul(s) actif(s) pour débloquer
              {{ campaign.next_tier.label || `${campaign.next_tier.discount_percent}% de réduction` }}.
            </p>
          </template>
          <p v-else class="ie-progress-caption">Tous les paliers de cette campagne sont débloqués ! 🎉</p>
        </div>
      </div>

      <div class="ie-card ie-card-body" style="margin-top: 20px;">
        <h3>Mes récompenses</h3>
        <div v-if="data.coupons.available.length || data.coupons.used.length || data.coupons.expired.length" class="ie-coupon-list">
          <div
            v-for="coupon in [...data.coupons.available, ...data.coupons.used, ...data.coupons.expired]"
            :key="coupon.id" class="ie-coupon-row"
          >
            <div>
              <strong class="ie-coupon-code">{{ coupon.code }}</strong>
              <p class="ie-coupon-meta">{{ coupon.campaign_name }} — {{ coupon.discount_percent }}% de réduction</p>
              <p v-if="coupon.expires_at" class="ie-coupon-meta">Expire le {{ new Date(coupon.expires_at).toLocaleDateString('fr-FR') }}</p>
            </div>
            <span class="ie-badge" :class="{
              'ie-badge-success': coupon.status === 'available',
              'ie-badge-neutral': coupon.status === 'used',
              'ie-badge-danger': coupon.status === 'expired' || coupon.status === 'cancelled',
            }">{{ COUPON_STATUS_LABELS[coupon.status] }}</span>
          </div>
        </div>
        <EmptyState v-else icon="fa-solid fa-gift" text="Aucune récompense pour le moment — invitez vos amis pour en débloquer." />
      </div>
    </template>
  </div>
</template>

<style scoped>
.ie-referral-hero { display: flex; justify-content: space-between; align-items: center; gap: 20px; flex-wrap: wrap; background: var(--ie-navy-soft); }
.ie-referral-label { margin: 0; font-size: 12.5px; color: var(--ie-muted); }
.ie-referral-code { margin: 4px 0; font-size: 28px; font-weight: 800; color: var(--ie-red); letter-spacing: 0.04em; }
.ie-referral-link { margin: 0; font-size: 12.5px; color: var(--ie-navy); word-break: break-all; }
.ie-referral-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
.ie-referral-share-row { display: flex; gap: 8px; }
.ie-share-btn {
  width: 38px; height: 38px; border-radius: 50%; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px;
  transition: transform 0.15s ease;
}
.ie-share-btn:hover { transform: translateY(-2px); }
.ie-share-whatsapp { background: #25d366; }
.ie-share-facebook { background: #1877f2; }
.ie-share-sms { background: var(--ie-navy); }
.ie-share-copy { background: var(--ie-muted); }

.ie-referral-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 16px; }
.ie-referral-stat { display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; }
.ie-referral-stat-value { font-size: 26px; font-weight: 800; color: var(--ie-navy); }
.ie-referral-stat-label { font-size: 12.5px; color: var(--ie-muted); }

.ie-campaign-progress { margin-bottom: 16px; }
.ie-campaign-name { font-weight: 700; font-size: 13.5px; color: var(--ie-navy); margin: 0 0 6px; }
.ie-progress-bar { width: 100%; height: 10px; border-radius: 6px; background: var(--ie-border); overflow: hidden; }
.ie-progress-fill { height: 100%; background: var(--ie-red); border-radius: 6px; transition: width 0.3s ease; }
.ie-progress-caption { margin: 6px 0 0; font-size: 12.5px; color: var(--ie-muted); }

.ie-coupon-list { display: flex; flex-direction: column; gap: 10px; }
.ie-coupon-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--ie-border); gap: 10px; }
.ie-coupon-code { font-size: 14px; color: var(--ie-ink); letter-spacing: 0.02em; }
.ie-coupon-meta { margin: 2px 0 0; font-size: 11.5px; color: var(--ie-muted); }

@media (max-width: 720px) {
  .ie-referral-hero { flex-direction: column; align-items: flex-start; }
  .ie-referral-actions { align-items: flex-start; width: 100%; }
  .ie-referral-stats { grid-template-columns: 1fr; }
}
</style>
