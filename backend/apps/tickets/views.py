from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin, IsAdminOrOrganizer, IsEmployee
from apps.audit.utils import log_action
from apps.notifications.services import notify_user, send_ticket_confirmation_email
from apps.payments.gateways import PaymentGatewayError, get_gateway
from apps.payments.models import Payment

from .models import Ticket, TicketType
from .pdf import build_ticket_pdf
from .qr import build_qr_png_bytes, sign_ticket_code, verify_ticket_token
from .serializers import (
    TicketPurchaseSerializer,
    TicketScanSerializer,
    TicketSerializer,
    TicketTypeSerializer,
)


class TicketTypeViewSet(viewsets.ModelViewSet):
    """Types de billets : seul un organisateur (ou l'administration) vend des
    billets — un client « particulier » n'a pas d'événement public à billeter."""

    serializer_class = TicketTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "is_active"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdminOrOrganizer()]
        if self.action in ["retrieve", "marketplace"]:
            # Lien de billetterie partageable par l'organisateur : consultable sans
            # connexion (l'achat, lui, reste protégé par IsAuthenticated).
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = TicketType.objects.select_related("event")
        if not user.is_authenticated:
            return qs.filter(is_active=True, event__status="published", event__is_public=True)
        if user.is_admin_role:
            return qs
        if user.is_organizer_role:
            return qs.filter(event__organizer=user)
        # Marché public : billets actifs des événements publiés et publics
        return qs.filter(is_active=True, event__status="published", event__is_public=True)

    def _check_event_ownership(self, event):
        # IDOR : get_queryset() ne protège que la lecture — sans ce contrôle,
        # un organisateur authentifié pourrait créer un type de billet sur
        # l'événement d'un autre organisateur en connaissant son id.
        user = self.request.user
        if not user.is_admin_role and event.organizer_id != user.id:
            raise PermissionDenied("Vous ne pouvez pas gérer la billetterie d'un événement qui ne vous appartient pas.")

    def perform_create(self, serializer):
        self._check_event_ownership(serializer.validated_data["event"])
        serializer.save()

    def perform_update(self, serializer):
        event = serializer.validated_data.get("event", serializer.instance.event)
        self._check_event_ownership(event)
        serializer.save()

    @action(detail=False, methods=["get"], url_path="marketplace")
    def marketplace(self, request):
        """Billets disponibles à l'achat, tous organisateurs confondus — accessible
        à tout utilisateur authentifié indépendamment de son propre rôle/événements."""
        now = timezone.now()
        qs = TicketType.objects.select_related("event").annotate(
            marketplace_sold_count=Count(
                "tickets",
                filter=Q(tickets__status__in=[Ticket.Status.VALID, Ticket.Status.USED]),
            )
        ).filter(
            is_active=True,
            sale_start__lte=now,
            sale_end__gte=now,
            event__status="published",
            event__is_public=True,
            quota__gt=F("marketplace_sold_count"),
        )
        event_id = request.query_params.get("event")
        if event_id:
            qs = qs.filter(event_id=event_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class MyTicketsViewSet(viewsets.ReadOnlyModelViewSet):
    """« Mes billets » : uniquement les billets de l'utilisateur connecté."""

    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Ticket.objects.select_related("ticket_type__event__venue", "owner").filter(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        ticket = self.get_object()
        pdf_bytes = build_ticket_pdf(ticket)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="billet-{ticket.code}.pdf"'
        return response

    @action(detail=True, methods=["get"], url_path="qr")
    def qr_code(self, request, pk=None):
        ticket = self.get_object()
        png_bytes = build_qr_png_bytes(sign_ticket_code(ticket.code))
        return HttpResponse(png_bytes, content_type="image/png")


class TicketPurchaseView(APIView):
    """Parcours complet d'achat (section 9, étapes 1 à 6) :
    sélection -> paiement -> génération du/des billet(s) avec QR -> email de confirmation.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ticket_purchase"

    @transaction.atomic
    def post(self, request):
        serializer = TicketPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_type = serializer.validated_data["ticket_type"]
        quantity = serializer.validated_data["quantity"]
        provider = serializer.validated_data["payment_provider"]
        buyer_first_name = serializer.validated_data.get("buyer_first_name") or request.user.first_name
        buyer_last_name = serializer.validated_data.get("buyer_last_name") or request.user.last_name
        buyer_email = serializer.validated_data.get("buyer_email") or request.user.email
        buyer_phone = serializer.validated_data.get("buyer_phone") or request.user.phone

        # Verrouille la ligne pour éviter une survente en cas d'achats concurrents.
        ticket_type = TicketType.objects.select_for_update().get(pk=ticket_type.pk)
        unavailability_reason = ticket_type.sale_unavailability_reason()
        if unavailability_reason:
            return Response({"detail": unavailability_reason}, status=status.HTTP_409_CONFLICT)
        if quantity > ticket_type.remaining_quota:
            return Response(
                {"detail": f"Il ne reste que {ticket_type.remaining_quota} billet(s). Réduisez la quantité puis réessayez."},
                status=status.HTTP_409_CONFLICT,
            )

        payment = Payment.objects.create(
            user=request.user,
            amount=ticket_type.price * quantity,
            currency=ticket_type.currency,
            provider=provider,
            purpose="ticket_purchase",
        )

        try:
            gateway = get_gateway(provider)
            success, provider_reference, raw_response = gateway.charge(payment)
        except PaymentGatewayError as exc:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = str(exc)
            payment.save(update_fields=["status", "failure_reason"])
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not success:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            return Response({"detail": "Le paiement a échoué."}, status=status.HTTP_402_PAYMENT_REQUIRED)

        payment.status = Payment.Status.COMPLETED
        payment.provider_reference = provider_reference
        payment.raw_response = raw_response
        payment.completed_at = timezone.now()
        payment.save()

        tickets = [
            Ticket.objects.create(
                ticket_type=ticket_type, owner=request.user, payment=payment,
                buyer_first_name=buyer_first_name, buyer_last_name=buyer_last_name,
                buyer_email=buyer_email, buyer_phone=buyer_phone,
            )
            for _ in range(quantity)
        ]

        log_action(
            actor=request.user,
            action="ticket.purchase",
            metadata={"ticket_type": ticket_type.id, "quantity": quantity, "payment": payment.transaction_ref},
        )
        send_ticket_confirmation_email(request.user, tickets)

        return Response(TicketSerializer(tickets, many=True).data, status=status.HTTP_201_CREATED)


class TicketScanView(APIView):
    """Contrôle d'accès à l'entrée : scan du QR code et validation côté serveur
    (section 9). Réservé à l'administration et aux employés en poste de contrôle."""

    permission_classes = [permissions.IsAuthenticated, IsEmployee | IsAdmin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr_scan"

    @transaction.atomic
    def post(self, request):
        serializer = TicketScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_code = verify_ticket_token(serializer.validated_data["token"])

        if not ticket_code:
            return Response({"valid": False, "reason": "Signature invalide ou QR falsifié."}, status=status.HTTP_400_BAD_REQUEST)

        ticket = Ticket.objects.select_for_update().filter(code=ticket_code).select_related("ticket_type__event", "owner").first()
        if not ticket:
            return Response({"valid": False, "reason": "Billet introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if ticket.status == Ticket.Status.CANCELLED:
            return Response({"valid": False, "reason": "Billet annulé."}, status=status.HTTP_200_OK)
        if ticket.status == Ticket.Status.USED:
            return Response({"valid": False, "reason": "Billet déjà utilisé.", "checked_in_at": ticket.checked_in_at}, status=status.HTTP_200_OK)

        ticket.status = Ticket.Status.USED
        ticket.checked_in_at = timezone.now()
        ticket.save(update_fields=["status", "checked_in_at"])

        log_action(actor=request.user, action="ticket.scan.valid", metadata={"ticket_code": str(ticket.code)})

        # Confirmation immédiate au titulaire (reçu d'entrée) : le scan ne passe que
        # par ce point de contrôle serveur, jamais par une simple lecture caméra.
        notify_user(
            ticket.owner,
            title="Entrée validée",
            message=(
                f"Votre billet pour « {ticket.ticket_type.event.title} » a été scanné et validé "
                f"le {ticket.checked_in_at:%d/%m/%Y à %H:%M}. Bienvenue !"
            ),
            link="/",
            send_email_too=True,
        )

        return Response({
            "valid": True,
            "ticket": TicketSerializer(ticket).data,
            "event": ticket.ticket_type.event.title,
            "holder": ticket.owner.get_full_name() or ticket.owner.username,
        })
