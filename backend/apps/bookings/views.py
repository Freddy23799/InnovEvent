from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminClientOrOrganizer
from apps.audit.utils import log_action
from apps.notifications.services import notify_booking_created, notify_booking_status_changed, send_booking_receipt_email
from apps.payments.gateways import PaymentGatewayError, get_gateway
from apps.payments.models import Payment
from apps.referrals.services import apply_coupon, redeem_coupon

from .models import Booking
from .pdf import build_booking_receipt_pdf
from .serializers import BookingPaymentSerializer, BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminClientOrOrganizer]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "resource_type", "status", "venue", "provider", "equipment"]

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.select_related("event", "venue", "provider", "equipment", "created_by", "payment")
        if user.is_admin_role:
            return qs
        return qs.filter(event__organizer=user)

    def _check_event_ownership(self, event):
        user = self.request.user
        if not user.is_admin_role and event.organizer_id != user.id:
            # IDOR : sans ce contrôle, n'importe quel client/organisateur
            # authentifié peut rattacher une réservation à l'événement d'un
            # autre utilisateur en connaissant simplement son id (get_queryset
            # ne protège que la lecture, pas l'écriture).
            raise PermissionDenied("Vous ne pouvez pas gérer les réservations d'un événement qui ne vous appartient pas.")

    def perform_create(self, serializer):
        self._check_event_ownership(serializer.validated_data["event"])
        booking = serializer.save(created_by=self.request.user)
        notify_booking_created(booking)

    def perform_update(self, serializer):
        event = serializer.validated_data.get("event", serializer.instance.event)
        self._check_event_ownership(event)
        previous_status = serializer.instance.status
        booking = serializer.save()
        if booking.status != previous_status:
            notify_booking_status_changed(booking)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Règle une réservation à tarification numérique (salle, matériel) via une
        passerelle de paiement, puis confirme la réservation et génère le reçu.

        L'ensemble tient dans une transaction avec verrou de ligne
        (`select_for_update`) : sans cela, deux requêtes `pay` concurrentes sur
        la même réservation pouvaient toutes deux passer le contrôle « pas déjà
        payée » avant qu'aucune n'ait validé son paiement, créant deux
        `Payment` réels pour une seule réservation. Le verrou est maintenu le
        temps de l'appel à la passerelle (acceptable ici : `DemoGateway` répond
        en mémoire, et le volume de cette plateforme ne justifie pas une
        conception « réservation optimiste » plus complexe)."""
        booking_pk = self.get_object().pk

        serializer = BookingPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data["payment_provider"]
        coupon_code = serializer.validated_data.get("coupon_code")

        with transaction.atomic():
            # Pas de `select_related` ici, volontairement : un `SELECT ...
            # FOR UPDATE` bloqué puis débloqué par le commit d'une transaction
            # concurrente peut renvoyer des colonnes jointes (payment/provider)
            # obsolètes — reflet de l'état d'AVANT l'attente, pas d'après
            # (particularité PostgreSQL de ré-évaluation des jointures lors
            # d'un UPDATE concurrent — EvalPlanQual). `booking.payment`/
            # `booking.provider` ci-dessous déclenchent chacun une requête
            # séparée, forcément fraîche puisqu'exécutée après l'acquisition
            # du verrou.
            booking = Booking.objects.select_for_update(of=("self",)).get(pk=booking_pk)

            if booking.status == Booking.Status.CANCELLED:
                return Response({"detail": "Cette réservation est annulée."}, status=status.HTTP_400_BAD_REQUEST)
            if booking.payment_id and booking.payment.status == Payment.Status.COMPLETED:
                return Response({"detail": "Cette réservation est déjà payée."}, status=status.HTTP_400_BAD_REQUEST)
            cost = booking.estimated_cost
            if cost is None:
                return Response(
                    {"detail": "Ce type de ressource n'a pas de tarification numérique ; contactez l'administration pour un devis."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            amount = cost
            coupon = None
            if coupon_code:
                context = {"category": booking.provider.category if booking.provider_id else ""}
                amount, _discount, coupon = apply_coupon(coupon_code, request.user, cost, context)

            payment = Payment.objects.create(
                user=request.user, amount=amount, currency="XAF", provider=provider, purpose="booking",
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

            if coupon:
                redeem_coupon(coupon, payment)

            booking.payment = payment
            booking.status = Booking.Status.CONFIRMED
            booking.save(update_fields=["payment", "status"])

        log_action(actor=request.user, action="booking.pay", metadata={"booking": booking.id, "payment": payment.transaction_ref})
        send_booking_receipt_email(request.user, booking)
        notify_booking_status_changed(booking)

        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["get"], url_path="receipt")
    def receipt(self, request, pk=None):
        booking = self.get_object()
        if not booking.payment_id or booking.payment.status != Payment.Status.COMPLETED:
            return Response({"detail": "Aucun paiement complété pour cette réservation."}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes = build_booking_receipt_pdf(booking)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="recu-reservation-{booking.id}.pdf"'
        return response
