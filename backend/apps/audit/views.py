from django.db import connection
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Journal d'activité consultable par l'administrateur (section 22 du CDC) :
    toute écriture sur l'API est journalisée automatiquement par le middleware."""

    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = AuditLog.objects.select_related("actor")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["actor", "method", "status_code"]
    search_fields = ["action", "path"]


class HealthCheckView(APIView):
    """Utilisé par le reverse proxy / l'orchestrateur pour vérifier la disponibilité
    de l'application et de ses dépendances (section 22/24 du CDC)."""

    permission_classes = [AllowAny]

    def get(self, request):
        checks = {"database": self._check_database(), "cache": self._check_cache()}
        healthy = all(checks.values())
        return Response({"status": "ok" if healthy else "degraded", "checks": checks}, status=200 if healthy else 503)

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_cache(self):
        try:
            cache.set("healthcheck", "ok", timeout=5)
            return cache.get("healthcheck") == "ok"
        except Exception:
            return False
