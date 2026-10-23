from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.audit.utils import log_action
from apps.marketplace.models import MarketplaceSubscription, MarketplaceType
from apps.messaging.models import Conversation
from apps.messaging.serializers import ConversationSerializer

from .models import TalentPortfolioItem, TalentProfile
from .serializers import TalentPortfolioItemSerializer, TalentProfileSerializer, TalentVerificationSerializer


def visible_talent_profiles(queryset):
    """Profils affichés aux prestataires : actifs et dont l'abonnement
    « Visibilité talent » est en cours. Le talent paie pour être vu ; le
    prestataire consulte gratuitement."""
    active_subscription = MarketplaceSubscription.objects.filter(
        user=OuterRef("user"), marketplace_type=MarketplaceType.TALENT_MISSIONS, expires_at__gt=timezone.now(),
    )
    return queryset.filter(is_active=True).filter(Exists(active_subscription))


def can_browse_talents(user):
    """Administration et comptes prestataire (partenaire sans profil talent)."""
    if user.is_admin_role:
        return True
    return user.role == "partner" and not TalentProfile.objects.filter(user=user).exists()


class TalentProfileViewSet(viewsets.ModelViewSet):
    """Profil « Talent » (section 5/6/7 du CDC) : géré par son titulaire,
    consultable par les prestataires tant que l'abonnement du talent est
    actif, vérifié uniquement par l'administration."""

    serializer_class = TalentProfileSerializer
    filterset_fields = {
        "verification_status": ["exact"], "is_active": ["exact"], "opportunity_type": ["exact"],
        "disponibilite": ["exact"], "city": ["icontains"],
    }
    search_fields = ["full_name", "competences", "city", "formation"]

    def get_permissions(self):
        if self.action == "verify":
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = TalentProfile.objects.select_related("user").prefetch_related("portfolio_items")
        user = self.request.user
        if user.is_admin_role:
            return qs
        if self.action in ["list", "retrieve", "contact"] and can_browse_talents(user):
            return visible_talent_profiles(qs)
        return qs.filter(user=user)

    def perform_create(self, serializer):
        if TalentProfile.objects.filter(user=self.request.user).exists():
            raise PermissionDenied("Vous avez déjà un profil talent.")
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        profile = TalentProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({"detail": "Aucun profil talent pour ce compte."}, status=404)
        return Response(TalentProfileSerializer(profile).data)

    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        profile = self.get_object()
        serializer = TalentVerificationSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            actor=request.user, action="talent.verification_status_changed",
            metadata={"talent": profile.id, "status": profile.verification_status},
        )
        return Response(TalentProfileSerializer(profile).data)

    @action(detail=True, methods=["post"])
    def contact(self, request, pk=None):
        """Ouvre (ou retrouve) la conversation entre le prestataire et le talent."""
        if not can_browse_talents(request.user):
            raise PermissionDenied("Seuls les comptes prestataire peuvent contacter un talent.")
        profile = self.get_object()
        if profile.user_id == request.user.id or not profile.user.is_active:
            raise PermissionDenied("Ce talent n'est pas joignable.")
        conversation = Conversation.get_or_create_between(request.user, profile.user)
        log_action(actor=request.user, action="talent.contacted", metadata={"talent": profile.id})
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class TalentPortfolioItemViewSet(viewsets.ModelViewSet):
    serializer_class = TalentPortfolioItemSerializer
    filterset_fields = ["profile"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TalentPortfolioItem.objects.select_related("profile")
        user = self.request.user
        if user.is_admin_role:
            return qs
        if self.action in ["list", "retrieve"] and can_browse_talents(user):
            return qs.filter(profile__in=visible_talent_profiles(TalentProfile.objects.all()))
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        profile = TalentProfile.objects.filter(user=self.request.user).first()
        if not profile:
            raise PermissionDenied("Vous devez d'abord créer votre profil talent.")
        serializer.save(profile=profile)
