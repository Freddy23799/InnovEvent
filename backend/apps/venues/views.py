from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.accounts.permissions import IsAdminOrPublicReadOnly
from apps.marketplace.feature_engine import resolve_features
from apps.marketplace.models import MarketplaceType

from .models import Venue
from .serializers import VenueSerializer


class VenueViewSet(viewsets.ModelViewSet):
    """CRUD réservé à l'administration. Consultable librement par un visiteur
    anonyme (page marketing publique « Nos services ») ; mais une fois connecté
    dans l'espace client/organisateur, les salles rejoignent le même modèle
    d'abonnement que les autres marketplaces premium (Décoration & design
    intérieur, Marketplace des acteurs) : rien n'est visible — ni la liste, ni
    la fiche — pour un compte non abonné au marketplace « Salles de
    réception » (l'administration voit toujours tout)."""

    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAdminOrPublicReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "city"]
    search_fields = ["name", "city"]
    ordering_fields = ["price_per_day", "capacity", "name"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated or user.is_admin_role:
            # Visiteur anonyme (page marketing publique) ou administration :
            # accès inchangé, sans lien avec le système d'abonnement.
            return qs
        feature = next(
            (f for f in resolve_features(user, MarketplaceType.VENUES) if f["key"] == "browse"), None
        )
        if feature and feature["visible"]:
            return qs
        return qs.none()
