from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets

from .models import EquipmentReview, ProfessionalReview, ProviderReview, VenueReview
from .serializers import (
    EquipmentReviewSerializer,
    ProfessionalReviewSerializer,
    ProviderReviewSerializer,
    VenueReviewSerializer,
)


class IsReviewAuthorOrAdminOrReadOnly(permissions.BasePermission):
    message = "Seul l'auteur de l'avis (ou un administrateur) peut le modifier."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if view.action == "create":
            return bool(
                request.user and request.user.is_authenticated
                and (request.user.is_client_role or request.user.is_organizer_role or request.user.is_admin_role)
            )
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_admin_role or obj.author == request.user


class VenueReviewViewSet(viewsets.ModelViewSet):
    """Avis clients sur les salles (section « satisfaction client » du CDC) :
    lecture ouverte à tout utilisateur authentifié, écriture réservée à
    l'auteur de l'avis (un client) ou à l'administrateur."""

    serializer_class = VenueReviewSerializer
    permission_classes = [IsReviewAuthorOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["venue"]
    queryset = VenueReview.objects.select_related("author", "venue")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ProviderReviewViewSet(viewsets.ModelViewSet):
    """Avis clients sur les prestataires (DJ, traiteur, décoration…)."""

    serializer_class = ProviderReviewSerializer
    permission_classes = [IsReviewAuthorOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["provider"]
    queryset = ProviderReview.objects.select_related("author", "provider")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class EquipmentReviewViewSet(viewsets.ModelViewSet):
    """Avis clients sur le matériel du catalogue."""

    serializer_class = EquipmentReviewSerializer
    permission_classes = [IsReviewAuthorOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["equipment"]
    queryset = EquipmentReview.objects.select_related("author", "equipment")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ProfessionalReviewViewSet(viewsets.ModelViewSet):
    """Avis clients sur les profils professionnels (marketplaces premium)."""

    serializer_class = ProfessionalReviewSerializer
    permission_classes = [IsReviewAuthorOrAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["profile"]
    queryset = ProfessionalReview.objects.select_related("author", "profile")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
