from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminClientOrOrganizer, IsOwnerOrAdmin
from apps.documents.reports import build_table_report_pdf
from apps.notifications.services import send_event_invitation_email

from .models import Event, EventExpense, EventParticipant, EventTask
from .serializers import (
    EventExpenseSerializer,
    EventParticipantSerializer,
    EventSerializer,
    EventTaskSerializer,
)


class EventViewSet(viewsets.ModelViewSet):
    """CRUD événements avec isolation stricte par rôle (section 4/7 du CDC) :
    - admin : accès total ;
    - client : uniquement ses propres événements privés (jamais publics) ;
    - organisateur : uniquement ses propres événements, publics ou privés ;
    - participant/employé : lecture seule des événements publics/publiés.
    """

    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "is_public"]
    search_fields = ["title", "description"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    owner_field = "organizer"

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdminClientOrOrganizer(), IsOwnerOrAdmin()]
        if self.action in ["retrieve", "marketplace"]:
            # Lien de billetterie partageable par l'organisateur : consultable sans
            # connexion (l'achat, lui, reste protégé par IsAuthenticated).
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Event.objects.select_related("organizer", "venue")
        if not user.is_authenticated:
            return qs.filter(status=Event.Status.PUBLISHED, is_public=True)
        if user.is_admin_role:
            return qs
        if user.is_client_role or user.is_organizer_role:
            return qs.filter(organizer=user)
        return qs.filter(status=Event.Status.PUBLISHED, is_public=True)

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @action(detail=False, methods=["get"], url_path="marketplace")
    def marketplace(self, request):
        """Marché public des événements (billetterie) : accessible à tout
        utilisateur authentifié quel que soit son rôle, indépendamment de la
        restriction « mes propres événements » qui s'applique à la liste standard."""
        qs = Event.objects.select_related("organizer", "venue").filter(
            status=Event.Status.PUBLISHED, is_public=True
        )
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request):
        events = self.filter_queryset(self.get_queryset())
        headers = ["Titre", "Organisateur", "Lieu", "Début", "Statut", "Budget (XAF)", "Avancement"]
        rows = [
            [
                e.title,
                e.organizer.get_full_name() or e.organizer.username,
                e.venue.name if e.venue else "—",
                e.start_date.strftime("%d/%m/%Y %H:%M"),
                e.get_status_display(),
                f"{e.budget_total:,.0f}".replace(",", " "),
                f"{e.progress_percent}%",
            ]
            for e in events
        ]
        pdf_bytes = build_table_report_pdf("Rapport des événements", headers, rows)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="rapport-evenements.pdf"'
        return response


def _check_event_ownership(request, event):
    """IDOR : `get_queryset()` ne protège que la lecture — sans ce contrôle
    explicite en écriture, n'importe quel client/organisateur authentifié
    pourrait rattacher une tâche/un participant/une dépense à l'événement d'un
    autre utilisateur en fournissant simplement son id."""
    user = request.user
    if not user.is_admin_role and event.organizer_id != user.id:
        raise PermissionDenied("Vous ne pouvez pas gérer les données d'un événement qui ne vous appartient pas.")


class EventTaskViewSet(viewsets.ModelViewSet):
    serializer_class = EventTaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "status", "priority", "assignee"]
    permission_classes = [permissions.IsAuthenticated, IsAdminClientOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        qs = EventTask.objects.select_related("event", "assignee")
        if user.is_admin_role:
            return qs
        return qs.filter(event__organizer=user)

    def perform_create(self, serializer):
        _check_event_ownership(self.request, serializer.validated_data["event"])
        serializer.save()

    def perform_update(self, serializer):
        event = serializer.validated_data.get("event", serializer.instance.event)
        _check_event_ownership(self.request, event)
        serializer.save()


class EventParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = EventParticipantSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "checked_in"]
    permission_classes = [permissions.IsAuthenticated, IsAdminClientOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        qs = EventParticipant.objects.select_related("event", "user")
        if user.is_admin_role:
            return qs
        return qs.filter(event__organizer=user)

    def perform_create(self, serializer):
        _check_event_ownership(self.request, serializer.validated_data["event"])
        participant = serializer.save()
        send_event_invitation_email(participant)

    def perform_update(self, serializer):
        event = serializer.validated_data.get("event", serializer.instance.event)
        _check_event_ownership(self.request, event)
        serializer.save()

    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request):
        participants = self.filter_queryset(self.get_queryset())
        headers = ["Nom", "Email", "Événement", "Statut", "Inscrit le"]
        rows = [
            [
                p.full_name or (p.user.get_full_name() if p.user else "—"),
                p.email or "—",
                p.event.title,
                "Présent" if p.checked_in else "Inscrit",
                p.registered_at.strftime("%d/%m/%Y %H:%M"),
            ]
            for p in participants
        ]
        pdf_bytes = build_table_report_pdf("Rapport des participants", headers, rows)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="rapport-participants.pdf"'
        return response


class EventExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = EventExpenseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "category"]
    permission_classes = [permissions.IsAuthenticated, IsAdminClientOrOrganizer]

    def get_queryset(self):
        user = self.request.user
        qs = EventExpense.objects.select_related("event")
        if user.is_admin_role:
            return qs
        return qs.filter(event__organizer=user)

    def perform_create(self, serializer):
        _check_event_ownership(self.request, serializer.validated_data["event"])
        serializer.save()

    def perform_update(self, serializer):
        event = serializer.validated_data.get("event", serializer.instance.event)
        _check_event_ownership(self.request, event)
        serializer.save()
