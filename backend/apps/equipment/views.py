from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.accounts.permissions import IsAdmin, IsAdminOrPublicReadOnly

from .models import Equipment, Expense, StockMovement
from .serializers import EquipmentSerializer, ExpenseSerializer, StockMovementSerializer


class EquipmentViewSet(viewsets.ModelViewSet):
    """CRUD réservé à l'administration ; consultable publiquement (page d'accueil,
    parcours de réservation)."""

    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [IsAdminOrPublicReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "price_per_unit"]


class StockMovementViewSet(viewsets.ModelViewSet):
    """Historique des entrées/sorties de stock (section « gestion de stock »),
    réservé à l'administration."""

    queryset = StockMovement.objects.select_related("equipment", "recorded_by")
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["equipment", "movement_type", "reason"]
    search_fields = ["equipment__name", "notes"]
    ordering_fields = ["created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    """Journal des dépenses liées au matériel (achats, réparations, logistique…),
    réservé à l'administration pour un contrôle financier centralisé."""

    queryset = Expense.objects.select_related("equipment", "stock_movement", "recorded_by")
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "equipment"]
    search_fields = ["label", "notes"]
    ordering_fields = ["incurred_at", "amount", "created_at"]

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
