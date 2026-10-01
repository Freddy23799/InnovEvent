from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin, IsAdminOrPublicReadOnly, IsAdminOrReadOnly, IsEmployee
from apps.audit.utils import log_action
from apps.documents.signing import verify_payload

from .models import Provider
from .pdf import build_provider_badge_pdf
from .serializers import ProviderScanSerializer, ProviderSerializer


class ProviderViewSet(viewsets.ModelViewSet):
    """CRUD réservé à l'administration ; liste/détail consultables publiquement
    (page d'accueil, parcours de réservation). Les actions sensibles (badge,
    écriture) restent réservées aux utilisateurs authentifiés/administrateurs."""

    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "category"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminOrPublicReadOnly()]
        return super().get_permissions()

    @action(detail=True, methods=["get"], url_path="badge")
    def badge(self, request, pk=None):
        provider = self.get_object()
        pdf_bytes = build_provider_badge_pdf(provider)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="badge-prestataire-{provider.id}.pdf"'
        return response


class ProviderScanView(APIView):
    """Contrôle d'identité d'un prestataire à son arrivée sur site, par scan de
    son badge QR (même principe que le contrôle des billets)."""

    permission_classes = [permissions.IsAuthenticated, IsEmployee | IsAdmin]

    def post(self, request):
        serializer = ProviderScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider_id = verify_payload(serializer.validated_data["token"], kind="provider-badge")

        if not provider_id:
            return Response({"valid": False, "reason": "Signature invalide ou badge falsifié."}, status=status.HTTP_400_BAD_REQUEST)

        provider = Provider.objects.filter(pk=provider_id).first()
        if not provider:
            return Response({"valid": False, "reason": "Prestataire introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if not provider.is_active:
            return Response({"valid": False, "reason": "Ce prestataire n'est plus actif."}, status=status.HTTP_200_OK)

        log_action(actor=request.user, action="provider.scan.valid", metadata={"provider": provider.id})

        return Response({
            "valid": True,
            "name": provider.name,
            "category": provider.get_category_display(),
            "identity_number": provider.identity_number,
        })
