import hmac

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.utils import get_client_ip, log_action
from apps.documents.reports import build_table_report_pdf

from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des paiements (section 10) : un utilisateur voit ses propres
    transactions, un administrateur voit tout."""

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "provider"]

    def get_queryset(self):
        user = self.request.user
        qs = Payment.objects.select_related("user")
        if user.is_admin_role:
            return qs
        return qs.filter(user=user)

    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request):
        payments = self.filter_queryset(self.get_queryset())
        headers = ["Référence", "Utilisateur", "Montant", "Devise", "Passerelle", "Statut", "Date"]
        rows = [
            [
                p.transaction_ref,
                p.user.get_full_name() or p.user.username,
                f"{p.amount:,.0f}".replace(",", " "),
                p.currency,
                p.get_provider_display(),
                p.get_status_display(),
                p.created_at.strftime("%d/%m/%Y %H:%M"),
            ]
            for p in payments
        ]
        pdf_bytes = build_table_report_pdf("Rapport des paiements", headers, rows)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="rapport-paiements.pdf"'
        return response


class BasePaymentWebhookView(APIView):
    """Point d'entrée générique pour les webhooks de passerelle.

    Sécurité (audit de sécurité — voir aussi `PAYMENT_WEBHOOK_SECRET` dans
    `config/settings.py`) :
    - authenticité : un en-tête `X-Webhook-Secret` doit correspondre exactement
      à `settings.PAYMENT_WEBHOOK_SECRET` (comparaison à temps constant) — sans
      quoi n'importe qui connaissant une `transaction_ref` (renvoyée au client
      propriétaire du paiement dans les réponses API normales) pourrait
      auparavant marquer lui-même son propre paiement « complété » sans
      passerelle réelle. À remplacer par la vérification de signature propre à
      chaque fournisseur (PayPal, FreemoPay, KOB) dès que ses secrets de
      webhook réels sont fournis — le principe (rejeter tout appel non
      authentifié) reste le même.
    - idempotence : un paiement déjà dans un état terminal (`completed`/
      `failed`) n'est plus jamais modifié par un rejeu du même webhook — évite
      un double traitement des effets de bord (parrainage, commissions).
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_webhook"
    provider = None

    def post(self, request):
        provided_secret = request.headers.get("X-Webhook-Secret", "")
        expected_secret = settings.PAYMENT_WEBHOOK_SECRET
        if not expected_secret or not hmac.compare_digest(provided_secret, expected_secret):
            log_action(
                action=f"payment.webhook.{self.provider}.rejected",
                ip_address=get_client_ip(request),
                metadata={"reason": "invalid_or_missing_secret"},
            )
            return Response({"detail": "Non autorisé."}, status=403)

        transaction_ref = request.data.get("transaction_ref")
        payment = Payment.objects.filter(transaction_ref=transaction_ref, provider=self.provider).first()
        log_action(
            action=f"payment.webhook.{self.provider}",
            ip_address=get_client_ip(request),
            metadata={"transaction_ref": transaction_ref, "status": request.data.get("status")},
        )
        if not payment:
            return Response({"detail": "Référence de transaction inconnue."}, status=404)

        if payment.status != Payment.Status.PENDING:
            # Déjà dans un état terminal — un rejeu du même webhook (ou un
            # appel tardif après une mise à jour manuelle) ne doit jamais
            # redéclencher les effets de bord (parrainage, commissions).
            return Response({"detail": "Paiement déjà traité — aucune action."})

        event_status = request.data.get("status")
        if event_status == "completed":
            payment.status = Payment.Status.COMPLETED
            payment.completed_at = timezone.now()
        elif event_status == "failed":
            payment.status = Payment.Status.FAILED
            payment.failure_reason = request.data.get("reason", "")
        else:
            return Response({"detail": "Statut d'événement inconnu."}, status=400)
        payment.raw_response = request.data
        payment.save()
        return Response({"detail": "Webhook traité."})


class PayPalWebhookView(BasePaymentWebhookView):
    provider = Payment.Provider.PAYPAL


class MobileMoneyWebhookView(BasePaymentWebhookView):
    provider = Payment.Provider.MOBILE_MONEY


class KobWebhookView(BasePaymentWebhookView):
    provider = Payment.Provider.KOB
