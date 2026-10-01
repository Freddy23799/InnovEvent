from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.audit.utils import log_action

from .models import CompanyDocument, CompanyProfile
from .serializers import CompanyDocumentSerializer, CompanyProfileSerializer, CompanyVerificationSerializer


class CompanyProfileViewSet(viewsets.ModelViewSet):
    """Profil « Entreprise » (section 5/6 du CDC) : le titulaire gère son
    propre profil, l'administration voit tout et peut seule faire évoluer
    `verification_status` (action dédiée, même principe que
    `ProfessionalProfileViewSet.badges`)."""

    serializer_class = CompanyProfileSerializer
    filterset_fields = ["verification_status", "is_active"]

    def get_permissions(self):
        if self.action == "verify":
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = CompanyProfile.objects.select_related("user").prefetch_related("documents")
        if user.is_admin_role:
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        if CompanyProfile.objects.filter(user=self.request.user).exists():
            raise PermissionDenied("Vous avez déjà un profil entreprise.")
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        profile = CompanyProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({"detail": "Aucun profil entreprise pour ce compte."}, status=404)
        return Response(CompanyProfileSerializer(profile).data)

    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        profile = self.get_object()
        serializer = CompanyVerificationSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            actor=request.user, action="company.verification_status_changed",
            metadata={"company": profile.id, "status": profile.verification_status},
        )
        return Response(CompanyProfileSerializer(profile).data)


class CompanyDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyDocumentSerializer
    filterset_fields = ["profile"]

    def get_queryset(self):
        user = self.request.user
        qs = CompanyDocument.objects.select_related("profile")
        if user.is_admin_role:
            return qs
        return qs.filter(profile__user=user)

    def perform_create(self, serializer):
        profile = CompanyProfile.objects.filter(user=self.request.user).first()
        if not profile:
            raise PermissionDenied("Vous devez d'abord créer votre profil entreprise.")
        serializer.save(profile=profile)
