from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.utils import get_client_ip, log_action

from .models import (
    CommissionRecord,
    Referral,
    ReferralCampaign,
    ReferralConversion,
    ReferralProfile,
    RewardCoupon,
    generate_coupon_code,
    generate_referral_code,
)

# Un compte dont le numéro de téléphone est déjà utilisé par un autre, ou dont
# plusieurs parrainages partent de la même adresse IP en peu de temps, n'est
# pas bloqué (un même foyer/cybercafé peut légitimement inscrire plusieurs
# comptes) — il est seulement signalé pour revue admin (section 8 : détection,
# pas blocage automatique aveugle).
DUPLICATE_IP_WINDOW_MINUTES = 60
DUPLICATE_IP_THRESHOLD = 3


def get_or_create_profile(user):
    profile = getattr(user, "referral_profile", None)
    if profile:
        return profile
    code = generate_referral_code(user.username)
    while ReferralProfile.objects.filter(code=code).exists():
        code = generate_referral_code(user.username)
    return ReferralProfile.objects.create(user=user, code=code)


def register_referral(code, referred_user, request=None):
    """Appelé juste après la création d'un compte (voir `RegisterSerializer`).
    Ne lève jamais d'erreur bloquante pour l'inscription elle-même : un code
    invalide/expiré est simplement ignoré (l'inscription réussit quand même)."""
    if not code:
        return None

    try:
        profile = ReferralProfile.objects.select_related("user").get(code__iexact=code.strip())
    except ReferralProfile.DoesNotExist:
        return None

    referrer = profile.user
    if referrer.id == referred_user.id:
        # Impossible en pratique (le compte vient d'être créé) — garde-fou
        # explicite quand même (section 8 : « impossibilité de se parrainer
        # soi-même »).
        return None

    ip_address = get_client_ip(request) if request else None
    is_flagged = False
    flag_reason = ""

    if referred_user.phone:
        from apps.accounts.models import User

        duplicate_phone = User.objects.filter(phone=referred_user.phone).exclude(id=referred_user.id).exists()
        if duplicate_phone:
            is_flagged = True
            flag_reason = "Numéro de téléphone déjà utilisé par un autre compte."

    if ip_address:
        recent_count = Referral.objects.filter(
            signup_ip=ip_address, created_at__gte=timezone.now() - timezone.timedelta(minutes=DUPLICATE_IP_WINDOW_MINUTES),
        ).count()
        if recent_count >= DUPLICATE_IP_THRESHOLD:
            is_flagged = True
            flag_reason = (flag_reason + " " if flag_reason else "") + "Plusieurs inscriptions parrainées depuis la même adresse IP."

    referral = Referral.objects.create(
        referrer=referrer, referred_user=referred_user, signup_ip=ip_address,
        is_flagged=is_flagged, flag_reason=flag_reason,
    )

    from apps.notifications.services import notify_referral_signup

    notify_referral_signup(referral)
    log_action(actor=referred_user, action="referral.signup", metadata={"referral": referral.id, "referrer": referrer.id})
    return referral


def resolve_purchase_context(payment):
    """Détermine catégorie/prestataire/service/marketplace_type/montant à
    partir du `purpose` du paiement — évite d'interroger les 5 relations
    inverses possibles (bookings/marketplace_orders/quotes/...) pour chaque
    paiement, on ne suit que celle pertinente à son `purpose`."""
    context = {
        "category": "", "provider_id": None, "professional_profile_id": None,
        "service_id": None, "marketplace_type": "", "amount": payment.amount,
        "provider": None, "professional_profile": None,
    }

    if payment.purpose == "booking":
        booking = payment.bookings.select_related("provider").first()
        if booking and booking.provider_id:
            context["provider_id"] = booking.provider_id
            context["provider"] = booking.provider
            context["category"] = booking.provider.category
    elif payment.purpose == "marketplace_order":
        order = payment.marketplace_orders.select_related("listing", "listing__provider").first()
        if order:
            context["marketplace_type"] = order.listing.marketplace_type
            if order.listing.provider_id:
                context["provider_id"] = order.listing.provider_id
                context["provider"] = order.listing.provider
                context["category"] = order.listing.provider.category
    elif payment.purpose == "marketplace_quote":
        quote = payment.quotes.select_related("booking_request__profile", "booking_request__service").first()
        if quote:
            profile = quote.booking_request.profile
            context["professional_profile_id"] = profile.id
            context["professional_profile"] = profile
            context["marketplace_type"] = profile.marketplace_type
            context["category"] = profile.category
            if quote.booking_request.service_id:
                context["service_id"] = quote.booking_request.service_id

    return context


def _matching_active_campaigns(context):
    campaigns = ReferralCampaign.objects.filter(active=True).prefetch_related("tiers", "providers", "professional_profiles", "services")
    return [c for c in campaigns if c.is_currently_active() and c.matches_context(context)]


def _reevaluate_campaign(referrer, campaign):
    """Compte les conversions actives (non-reversées, `is_first_qualifying`)
    du parrain qui correspondent aux filtres de cette campagne, et émet le
    coupon du palier le plus élevé nouvellement atteint (un seul coupon par
    palier et par parrain, jamais réémis)."""
    conversions = ReferralConversion.objects.filter(
        referral__referrer=referrer, referral__status=Referral.Status.CONVERTED,
        is_first_qualifying=True, is_reversed=False,
    )
    matching_count = 0
    for conversion in conversions:
        context = {
            "category": conversion.category, "provider_id": conversion.provider_id,
            "professional_profile_id": conversion.professional_profile_id, "marketplace_type": conversion.marketplace_type,
            "service_id": None,
        }
        if campaign.matches_context(context):
            matching_count += 1

    tiers = list(campaign.tiers.filter(threshold_referrals__lte=matching_count).order_by("-threshold_referrals"))
    if not tiers:
        return
    tier = tiers[0]
    already_issued = RewardCoupon.objects.filter(owner=referrer, campaign=campaign, tier=tier).exists()
    if already_issued:
        return

    expires_at = timezone.now() + timezone.timedelta(days=campaign.coupon_validity_days) if campaign.coupon_validity_days else None
    code = generate_coupon_code(tier.discount_percent)
    while RewardCoupon.objects.filter(code=code).exists():
        code = generate_coupon_code(tier.discount_percent)

    coupon = RewardCoupon.objects.create(
        code=code, campaign=campaign, tier=tier, owner=referrer,
        discount_percent=tier.discount_percent, max_discount_amount=tier.max_discount_amount,
        max_uses=campaign.max_uses_per_coupon, expires_at=expires_at,
    )

    from apps.notifications.services import notify_reward_unlocked

    notify_reward_unlocked(coupon)
    log_action(actor=referrer, action="referral.reward_unlocked", metadata={"coupon": coupon.code, "campaign": campaign.id})


def process_payment_completed(payment):
    referral = Referral.objects.filter(referred_user_id=payment.user_id, status=Referral.Status.PENDING).select_related("referrer").first()
    if not referral:
        return

    context = resolve_purchase_context(payment)

    referral.status = Referral.Status.CONVERTED
    referral.converted_at = timezone.now()
    referral.first_conversion_payment = payment
    referral.save(update_fields=["status", "converted_at", "first_conversion_payment"])

    conversion = ReferralConversion.objects.create(
        referral=referral, payment=payment, is_first_qualifying=True,
        category=context["category"], provider=context["provider"], professional_profile=context["professional_profile"],
        marketplace_type=context["marketplace_type"], amount=payment.amount,
    )

    CommissionRecord.objects.create(
        payment=payment, referral=referral, gross_amount=payment.amount, purpose=payment.purpose,
    )

    from apps.notifications.services import notify_referral_progress

    notify_referral_progress(referral)
    log_action(
        actor=referral.referrer, action="referral.converted",
        metadata={"referral": referral.id, "payment": payment.transaction_ref, "conversion": conversion.id},
    )

    for campaign in _matching_active_campaigns(context):
        _reevaluate_campaign(referral.referrer, campaign)
    # Les campagnes sans aucun filtre (catégorie/prestataire/service/marketplace
    # vides) matchent déjà tout contexte via `matches_context` — la campagne
    # marquée `is_default` n'a donc besoin d'aucun traitement séparé.


def process_payment_reversed(payment):
    conversion = ReferralConversion.objects.filter(payment=payment, is_reversed=False).select_related("referral", "referral__referrer").first()
    if not conversion:
        return

    conversion.is_reversed = True
    conversion.save(update_fields=["is_reversed"])

    referral = conversion.referral
    if conversion.is_first_qualifying:
        referral.status = Referral.Status.REVERSED
        referral.save(update_fields=["status"])

    coupons_from_this_conversion = RewardCoupon.objects.filter(owner=referral.referrer, campaign__isnull=False)
    for coupon in coupons_from_this_conversion:
        remaining = ReferralConversion.objects.filter(
            referral__referrer=referral.referrer, referral__status=Referral.Status.CONVERTED,
            is_first_qualifying=True, is_reversed=False,
        ).count()
        if remaining >= coupon.tier.threshold_referrals:
            continue  # le parrain a assez d'autres filleuls actifs pour garder ce palier
        if coupon.status == RewardCoupon.Status.AVAILABLE:
            coupon.status = RewardCoupon.Status.CANCELLED
            coupon.save(update_fields=["status"])
            log_action(actor=None, action="referral.reward_auto_cancelled", metadata={"coupon": coupon.code, "reason": "conversion_reversed"})
        elif coupon.status == RewardCoupon.Status.USED:
            referral.is_flagged = True
            referral.flag_reason = (referral.flag_reason + " " if referral.flag_reason else "") + (
                f"Récompense {coupon.code} déjà utilisée alors que la transaction d'origine a été annulée/remboursée — à examiner."
            )
            referral.save(update_fields=["is_flagged", "flag_reason"])

    log_action(actor=None, action="referral.conversion_reversed", metadata={"payment": payment.transaction_ref, "referral": referral.id})


def apply_coupon(code, user, amount, context=None):
    """Valide un code et calcule la réduction — ne modifie JAMAIS le coupon
    (utilisé aussi bien pour l'aperçu avant paiement que pour calculer le
    montant à débiter). Retourne (final_amount, discount_amount, coupon) ou
    lève une `ValidationError` DRF (traduite automatiquement en 400)."""
    context = context or {}
    amount = Decimal(amount)
    try:
        coupon = RewardCoupon.objects.select_related("campaign", "tier").get(code__iexact=code.strip())
    except RewardCoupon.DoesNotExist:
        raise ValidationError({"coupon_code": "Ce code de réduction est invalide."})

    if coupon.owner_id != user.id:
        raise ValidationError({"coupon_code": "Ce code de réduction ne vous appartient pas."})
    if not coupon.is_valid_now():
        raise ValidationError({"coupon_code": "Ce code de réduction n'est plus valide (utilisé, expiré ou annulé)."})
    if amount < coupon.campaign.min_purchase_amount:
        raise ValidationError({
            "coupon_code": f"Montant minimum de {coupon.campaign.min_purchase_amount} XAF requis pour utiliser ce code.",
        })
    if not coupon.campaign.matches_context(context):
        raise ValidationError({"coupon_code": "Ce code de réduction ne s'applique pas à cet achat."})

    discount = coupon.compute_discount(amount)
    return amount - discount, discount, coupon


def redeem_coupon(coupon, payment):
    """Consomme réellement le coupon — appelé UNIQUEMENT une fois le paiement
    confirmé (`status=COMPLETED`) par la passerelle, jamais avant : un
    paiement qui échoue ne doit pas consommer la récompense du parrain.

    Verrouille la ligne (`select_for_update`) avant d'incrémenter le compteur :
    les vues appelantes (`Booking.pay`, `Quote.pay`, commande Marketplace)
    verrouillent déjà la ressource achetée, ce qui suffit à empêcher un double
    paiement sur UNE MÊME réservation/devis ; ce verrou supplémentaire évite en
    plus une perte de mise à jour si le même code de coupon est utilisé sur
    deux achats différents lancés en parallèle."""
    from django.db import transaction

    with transaction.atomic():
        locked = RewardCoupon.objects.select_for_update().get(pk=coupon.pk)
        locked.times_used += 1
        if locked.times_used >= locked.max_uses:
            locked.status = RewardCoupon.Status.USED
        locked.redeemed_payment = payment
        locked.save(update_fields=["times_used", "status", "redeemed_payment"])
    log_action(actor=coupon.owner, action="referral.reward_redeemed", metadata={"coupon": coupon.code, "payment": payment.transaction_ref})
