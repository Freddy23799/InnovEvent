from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.messaging.models import Conversation
from apps.messaging.serializers import ConversationSerializer

from apps.accounts.permissions import IsAdmin
from apps.audit.utils import log_action

from apps.marketplace.models import MarketplaceSubscription, MarketplaceType
from django.utils import timezone

from .models import TalentMission, TalentPortfolioItem, TalentProfile
from .serializers import TalentMissionManageSerializer, TalentMissionSerializer, TalentPortfolioItemSerializer, TalentProfileSerializer, TalentVerificationSerializer


class TalentProfileViewSet(viewsets.ModelViewSet):
    """Profil « Talent » (section 5/6/7 du CDC) : consultable publiquement
    (annuaire des talents sur la page d'accueil), géré par son titulaire,
    vérifié uniquement par l'administration."""

    serializer_class = TalentProfileSerializer
    filterset_fields = ["verification_status", "is_active", "opportunity_type", "city"]
    search_fields = ["full_name", "competences", "city"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        if self.action == "verify":
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = TalentProfile.objects.select_related("user").prefetch_related("portfolio_items")
        user = self.request.user
        if user.is_authenticated and user.is_admin_role:
            return qs
        if self.action in ["list", "retrieve"]:
            # Annuaire public (section 7 — rubrique « Talents » de la page
            # d'accueil) : seuls les profils actifs sont visibles, sauf pour
            # le titulaire lui-même qui doit voir/gérer le sien même inactif.
            if user.is_authenticated:
                return qs.filter(Q(is_active=True) | Q(user=user))
            return qs.filter(is_active=True)
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


class TalentPortfolioItemViewSet(viewsets.ModelViewSet):
    serializer_class = TalentPortfolioItemSerializer
    filterset_fields = ["profile"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = TalentPortfolioItem.objects.select_related("profile")
        user = self.request.user
        if self.action in ["list", "retrieve"]:
            return qs.filter(profile__is_active=True)
        if user.is_authenticated and user.is_admin_role:
            return qs
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        profile = TalentProfile.objects.filter(user=self.request.user).first()
        if not profile:
            raise PermissionDenied("Vous devez d'abord créer votre profil talent.")
        serializer.save(profile=profile)


class TalentMissionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not TalentProfile.objects.filter(user=request.user, is_active=True).exists():
            return Response({"detail": "Cette rubrique est réservée aux comptes talent."}, status=status.HTTP_403_FORBIDDEN)
        subscription = MarketplaceSubscription.objects.filter(
            user=request.user, marketplace_type=MarketplaceType.TALENT_MISSIONS, expires_at__gt=timezone.now(),
        ).first()
        if not subscription:
            return Response({"detail": "Un abonnement actif est nécessaire pour consulter les missions."}, status=status.HTTP_402_PAYMENT_REQUIRED)
        missions = TalentMission.objects.filter(is_active=True)
        return Response(TalentMissionSerializer(missions, many=True).data)


class TalentMissionContactView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, mission_id):
        if not TalentProfile.objects.filter(user=request.user, is_active=True).exists():
            return Response({"detail": "Cette rubrique est réservée aux comptes talent."}, status=status.HTTP_403_FORBIDDEN)
        if not MarketplaceSubscription.objects.filter(
            user=request.user, marketplace_type=MarketplaceType.TALENT_MISSIONS, expires_at__gt=timezone.now(),
        ).exists():
            return Response({"detail": "Un abonnement actif est nécessaire pour contacter le prestataire."}, status=status.HTTP_402_PAYMENT_REQUIRED)
        mission = TalentMission.objects.filter(pk=mission_id, is_active=True).select_related("provider_user").first()
        if not mission or not mission.provider_user or not mission.provider_user.is_active:
            return Response({"detail": "Le prestataire de cette mission n'est pas joignable."}, status=status.HTTP_404_NOT_FOUND)
        if mission.provider_user_id == request.user.id:
            return Response({"detail": "Vous ne pouvez pas vous contacter vous-même."}, status=status.HTTP_400_BAD_REQUEST)
        conversation = Conversation.get_or_create_between(request.user, mission.provider_user)
        return Response(ConversationSerializer(conversation, context={"request": request}).data)


class TalentMissionManageViewSet(viewsets.ModelViewSet):
    serializer_class = TalentMissionManageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = TalentMission.objects.select_related("provider_user")
        if self.request.user.is_admin_role:
            return qs
        return qs.filter(provider_user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "partner":
            raise PermissionDenied("Seuls les comptes prestataire peuvent publier une mission.")
        try:
            from apps.marketplace.models import ProfessionalProfile
            provider_name = ProfessionalProfile.objects.get(user=user).business_name
        except Exception:
            provider_name = user.get_full_name() or user.username
        serializer.save(provider_user=user, provider_name=provider_name, is_demo=False)
