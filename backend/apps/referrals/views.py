from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin

from .models import CommissionRecord, Referral, ReferralCampaign, ReferralConversion, RewardCoupon
from .serializers import (
    CouponValidateSerializer,
    ReferralAdminSerializer,
    ReferralCampaignSerializer,
    ReferralConversionAdminSerializer,
    RewardCouponSerializer,
)
from .services import apply_coupon, get_or_create_profile


class MyReferralView(APIView):
    """« Mon parrainage » — code, compteurs, progression par campagne active,
    coupons. Crée le `ReferralProfile` à la volée si absent (même pattern que
    `CarrierViewSet.me`/`DriverViewSet.me` déjà utilisés dans ce projet)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = get_or_create_profile(user)

        referrals = Referral.objects.filter(referrer=user)
        invited_count = referrals.count()
        converted_qs = referrals.filter(status=Referral.Status.CONVERTED)
        converted_count = converted_qs.count()

        campaigns_data = []
        for campaign in ReferralCampaign.objects.filter(active=True).prefetch_related("tiers"):
            if not campaign.is_currently_active():
                continue
            matching = 0
            for conversion in ReferralConversion.objects.filter(
                referral__referrer=user, referral__status=Referral.Status.CONVERTED,
                is_first_qualifying=True, is_reversed=False,
            ):
                context = {
                    "category": conversion.category, "provider_id": conversion.provider_id,
                    "professional_profile_id": conversion.professional_profile_id,
                    "marketplace_type": conversion.marketplace_type, "service_id": None,
                }
                if campaign.matches_context(context):
                    matching += 1

            tiers = list(campaign.tiers.all().order_by("threshold_referrals"))
            next_tier = next((t for t in tiers if t.threshold_referrals > matching), None)
            campaigns_data.append({
                "id": campaign.id, "name": campaign.name, "description": campaign.description,
                "progress": matching,
                "next_tier": {
                    "threshold_referrals": next_tier.threshold_referrals, "discount_percent": next_tier.discount_percent,
                    "label": next_tier.label, "remaining": next_tier.threshold_referrals - matching,
                } if next_tier else None,
                "tiers": [
                    {"threshold_referrals": t.threshold_referrals, "discount_percent": t.discount_percent, "label": t.label}
                    for t in tiers
                ],
            })

        coupons = RewardCoupon.objects.filter(owner=user)
        return Response({
            "code": profile.code,
            "stats": {
                "invited": invited_count,
                "signed_up": invited_count,
                "active_referrals": converted_count,
            },
            "campaigns": campaigns_data,
            "coupons": {
                "available": RewardCouponSerializer(coupons.filter(status=RewardCoupon.Status.AVAILABLE), many=True).data,
                "used": RewardCouponSerializer(coupons.filter(status=RewardCoupon.Status.USED), many=True).data,
                "expired": RewardCouponSerializer(
                    coupons.filter(status__in=[RewardCoupon.Status.EXPIRED, RewardCoupon.Status.CANCELLED]), many=True,
                ).data,
            },
        })


class ReferralCampaignViewSet(viewsets.ModelViewSet):
    """Lecture ouverte aux authentifiés (affichage de la progression côté
    client) ; écriture réservée à l'administration (« Configuration des
    campagnes », section 10 du CDC)."""

    serializer_class = ReferralCampaignSerializer
    queryset = ReferralCampaign.objects.all().prefetch_related("tiers", "providers", "professional_profiles", "services")

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_admin_role:
            return qs
        return qs.filter(active=True)


class CouponValidateView(APIView):
    """Aperçu de réduction avant paiement (mode dry-run) — utilisé par les
    modales de checkout pour afficher le total recalculé avant soumission.
    Limité en débit : sans cela, un compte authentifié pourrait essayer un
    grand nombre de codes au hasard pour découvrir un coupon valide d'un
    autre utilisateur (les codes sont aléatoires mais l'endpoint n'était pas
    limité avant cet audit)."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "coupon_validate"

    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = {
            "category": data["category"], "provider_id": data["provider_id"],
            "professional_profile_id": data["professional_profile_id"], "service_id": data["service_id"],
            "marketplace_type": data["marketplace_type"],
        }
        final_amount, discount_amount, coupon = apply_coupon(data["coupon_code"], request.user, data["amount"], context)
        return Response({
            "final_amount": final_amount, "discount_amount": discount_amount,
            "discount_percent": coupon.discount_percent, "coupon_code": coupon.code,
        })


class ReferralAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """« Gestion des parrainages » (section 9 du CDC) — lecture admin, filtrable
    par période/utilisateur/statut, avec actions de modération."""

    serializer_class = ReferralAdminSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = Referral.objects.select_related("referrer", "referred_user").all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["status", "is_flagged", "referrer"]
    search_fields = ["referrer__username", "referred_user__username"]

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        referral = self.get_object()
        referral.is_flagged = True
        referral.flag_reason = request.data.get("reason", "Signalé manuellement par l'administration.")
        referral.save(update_fields=["is_flagged", "flag_reason"])
        return Response(ReferralAdminSerializer(referral).data)

    @action(detail=True, methods=["post"], url_path="unflag")
    def unflag(self, request, pk=None):
        referral = self.get_object()
        referral.is_flagged = False
        referral.flag_reason = ""
        referral.save(update_fields=["is_flagged", "flag_reason"])
        return Response(ReferralAdminSerializer(referral).data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        referrals = Referral.objects.all()
        conversions = ReferralConversion.objects.filter(is_reversed=False)
        coupons = RewardCoupon.objects.all()
        revenue = conversions.aggregate(total=Sum("amount"))["total"] or 0
        commission = CommissionRecord.objects.aggregate(total=Sum("commission_amount"))["total"] or 0
        return Response({
            "total_referrers": referrals.values("referrer").distinct().count(),
            "total_referred": referrals.count(),
            "active_referrals": referrals.filter(status=Referral.Status.CONVERTED).count(),
            "flagged_referrals": referrals.filter(is_flagged=True).count(),
            "revenue_generated": revenue,
            "commission_generated": commission,
            "coupons_issued": coupons.count(),
            "coupons_used": coupons.filter(status=RewardCoupon.Status.USED).count(),
            "coupons_available": coupons.filter(status=RewardCoupon.Status.AVAILABLE).count(),
            "coupons_expired": coupons.filter(status__in=[RewardCoupon.Status.EXPIRED, RewardCoupon.Status.CANCELLED]).count(),
        })


class RewardCouponAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RewardCouponSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = RewardCoupon.objects.select_related("owner", "campaign").all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["status", "campaign"]
    search_fields = ["code", "owner__username"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        coupon = self.get_object()
        coupon.status = RewardCoupon.Status.CANCELLED
        coupon.save(update_fields=["status"])
        return Response(RewardCouponSerializer(coupon).data)


class ReferralConversionAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReferralConversionAdminSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = ReferralConversion.objects.select_related("referral__referrer", "referral__referred_user", "payment").all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["category", "marketplace_type", "is_reversed"]
    search_fields = ["referral__referrer__username", "referral__referred_user__username"]
