import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.providers.models import Provider


def _random_suffix(length):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def generate_referral_code(base=""):
    prefix = "".join(ch for ch in (base or "").upper() if ch.isalnum())[:4] or "USER"
    return f"{prefix}{_random_suffix(4)}"


def generate_coupon_code(discount_percent):
    pct = int(discount_percent)
    return f"REF-{pct}PCT-{_random_suffix(5)}"


class ReferralProfile(models.Model):
    """Un code de parrainage unique par compte — créé paresseusement (voir
    `apps.referrals.services.get_or_create_profile`), jamais en masse par
    migration, pour ne pas générer de codes inutiles pour des comptes qui ne
    parraineront jamais personne."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_profile")
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.code}"


class Referral(models.Model):
    """Lien parrain → filleul, créé à l'inscription. `referred_user` est
    OneToOne : un compte n'a qu'un seul parrain, jamais modifiable après coup
    (aucun endpoint d'update n'expose ce champ — section 8 du cahier des
    charges : « impossibilité de modifier son parrain après validation »)."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente (inscrit, pas encore de transaction validée)"
        CONVERTED = "converted", "Converti (filleul actif)"
        REVERSED = "reversed", "Annulé (remboursement/annulation de la transaction)"

    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_made")
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referred_by")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    signup_ip = models.GenericIPAddressField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False, help_text="Suspecté de fraude — visible dans le tableau de bord admin.")
    flag_reason = models.CharField(max_length=300, blank=True)
    first_conversion_payment = models.ForeignKey(
        "payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(check=~Q(referrer=F("referred_user")), name="referral_no_self_referral"),
        ]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["referrer"])]

    def __str__(self):
        return f"{self.referrer} → {self.referred_user} ({self.get_status_display()})"


class ReferralCampaign(models.Model):
    """Campagne de parrainage entièrement configurable par l'administration
    (section 3/10 du cahier des charges) — plusieurs campagnes peuvent
    coexister, chacune avec ses propres filtres et paliers de récompense."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    terms_text = models.TextField(blank=True, help_text="Conditions d'utilisation affichées au filleul/parrain.")
    active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False, help_text="Campagne appliquée par défaut aux conversions qui ne correspondent à aucune campagne ciblée.",
    )
    category = models.CharField(
        max_length=30, choices=Provider.Category.choices, blank=True, help_text="Vide = toutes catégories.",
    )
    providers = models.ManyToManyField(Provider, blank=True, related_name="referral_campaigns")
    professional_profiles = models.ManyToManyField(
        "marketplace.ProfessionalProfile", blank=True, related_name="referral_campaigns",
    )
    services = models.ManyToManyField("marketplace.ProfessionalService", blank=True, related_name="referral_campaigns")
    marketplace_type = models.CharField(max_length=20, blank=True, help_text="Vide = tous les marketplaces.")
    min_purchase_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_validity_days = models.PositiveIntegerField(default=30)
    max_uses_per_coupon = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def is_currently_active(self):
        if not self.active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def matches_context(self, context):
        """`context` : dict optionnellement rempli de `category`, `provider_id`,
        `professional_profile_id`, `service_id`, `marketplace_type` — un filtre
        vide sur la campagne signifie « toutes valeurs acceptées »."""
        if self.category and context.get("category") != self.category:
            return False
        if self.marketplace_type and context.get("marketplace_type") != self.marketplace_type:
            return False
        if self.providers.exists() and context.get("provider_id") not in set(self.providers.values_list("id", flat=True)):
            return False
        if self.professional_profiles.exists() and context.get("professional_profile_id") not in set(
            self.professional_profiles.values_list("id", flat=True)
        ):
            return False
        if self.services.exists() and context.get("service_id") not in set(self.services.values_list("id", flat=True)):
            return False
        return True


class ReferralCampaignTier(models.Model):
    """Un palier de récompense au sein d'une campagne — plusieurs paliers
    (5/10/20 filleuls...) permettent l'exemple 5%/10%/avantage spécial de la
    spec au sein d'une même campagne."""

    campaign = models.ForeignKey(ReferralCampaign, on_delete=models.CASCADE, related_name="tiers")
    threshold_referrals = models.PositiveIntegerField(help_text="Nombre de filleuls actifs nécessaires pour débloquer ce palier.")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    label = models.CharField(max_length=150, blank=True, help_text="Ex : « Avantage spécial » — affiché au lieu du pourcentage si renseigné.")

    class Meta:
        ordering = ["threshold_referrals"]
        constraints = [models.UniqueConstraint(fields=["campaign", "threshold_referrals"], name="unique_tier_threshold_per_campaign")]

    def __str__(self):
        return f"{self.campaign.name} — {self.threshold_referrals} filleuls → {self.discount_percent}%"


class RewardCoupon(models.Model):
    """Récompense concrète émise pour un parrain lorsqu'il franchit un palier
    — identifiant unique de type `REF-5PCT-8F72K` (section 7 du cahier des
    charges). Les valeurs de réduction sont figées (« snapshot ») au moment de
    l'émission : un changement ultérieur de la campagne ne modifie jamais un
    coupon déjà émis."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        USED = "used", "Utilisé"
        EXPIRED = "expired", "Expiré"
        CANCELLED = "cancelled", "Annulé"

    code = models.CharField(max_length=40, unique=True)
    campaign = models.ForeignKey(ReferralCampaign, on_delete=models.CASCADE, related_name="coupons")
    tier = models.ForeignKey(ReferralCampaignTier, on_delete=models.CASCADE, related_name="coupons")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reward_coupons")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_uses = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    redeemed_payment = models.ForeignKey(
        "payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="redeemed_coupons",
        help_text="Dernier paiement ayant utilisé ce coupon (historique complet non nécessaire : la plupart des coupons sont à usage unique).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["owner"])]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"

    def is_valid_now(self):
        if self.status != self.Status.AVAILABLE:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.times_used >= self.max_uses:
            return False
        return True

    def compute_discount(self, amount):
        amount = Decimal(amount)
        discount = (amount * self.discount_percent / Decimal("100")).quantize(Decimal("0.01"))
        if self.max_discount_amount is not None:
            discount = min(discount, self.max_discount_amount)
        return min(discount, amount)


class ReferralConversion(models.Model):
    """Une ligne par transaction validée d'un filleul — sert au calcul de
    progression (filtrer sur `is_first_qualifying=True`, seule la première
    transaction d'un filleul compte pour débloquer une récompense — section 12
    du cahier des charges) ET au reporting admin (CA total généré par un
    filleul, même après sa première transaction)."""

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="conversions")
    payment = models.OneToOneField("payments.Payment", on_delete=models.CASCADE, related_name="referral_conversion")
    is_first_qualifying = models.BooleanField(default=False)
    category = models.CharField(max_length=30, blank=True)
    provider = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    professional_profile = models.ForeignKey(
        "marketplace.ProfessionalProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    marketplace_type = models.CharField(max_length=20, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_reversed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conversion #{self.pk} — {self.referral}"


class CommissionRecord(models.Model):
    """Mesure purement informative (section 11) du chiffre d'affaires et de la
    commission générés par une transaction issue du parrainage — alimente le
    tableau de bord admin, sans logique de versement réel."""

    payment = models.OneToOneField("payments.Payment", on_delete=models.CASCADE, related_name="commission_record")
    referral = models.ForeignKey(Referral, on_delete=models.SET_NULL, null=True, blank=True, related_name="commission_records")
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    purpose = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commission #{self.pk} — {self.commission_amount}"
