from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsAdminOrReadOnly
from apps.audit.utils import log_action
from apps.payments.gateways import PaymentGatewayError, get_gateway
from apps.payments.models import Payment

from .models import Badge, Certificate, Enrollment, Settlement, Training, TrainingFormula
from .pdf import build_badge_pdf, build_certificate_pdf
from .serializers import (
    BadgeSerializer,
    CertificateSerializer,
    EnrollmentPaymentSerializer,
    EnrollmentSerializer,
    SettlementSerializer,
    TrainingFormulaSerializer,
    TrainingSerializer,
)


class TrainingViewSet(viewsets.ModelViewSet):
    queryset = Training.objects.prefetch_related("formulas").all()
    serializer_class = TrainingSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "specialty"]


class TrainingFormulaViewSet(viewsets.ModelViewSet):
    """Formules (durée + tarification) rattachées à une filière (section « logique
    métier » de la rentrée académique : chaque filière peut proposer plusieurs
    durées de formation, à des tarifs distincts)."""

    queryset = TrainingFormula.objects.select_related("training")
    serializer_class = TrainingFormulaSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["training", "is_active"]


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["training", "status", "participant"]
    search_fields = ["matricule", "participant__username", "participant__last_name"]

    def get_permissions(self):
        if self.action in ["validate", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.select_related("training", "participant")
        if user.is_admin_role:
            return qs
        return qs.filter(participant=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_admin_role and serializer.validated_data.get("participant"):
            serializer.save()
        else:
            serializer.save(participant=user)

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = Enrollment.Status.VALIDATED
        enrollment.validated_by = request.user
        enrollment.save(update_fields=["status", "validated_by"])
        log_action(actor=request.user, action="enrollment.validate", metadata={"enrollment": enrollment.matricule})
        return Response(EnrollmentSerializer(enrollment).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Règle une tranche des frais de formation via une passerelle de paiement
        (section 13 du CDC : suivi des frais dus, montants versés, solde). Chaque
        paiement réussi crée automatiquement un règlement (une « tranche »)."""
        enrollment = self.get_object()
        if enrollment.balance <= 0:
            return Response({"detail": "Cette inscription est déjà entièrement réglée."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = EnrollmentPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        provider = serializer.validated_data["payment_provider"]

        if amount > enrollment.balance:
            return Response({"detail": f"Le montant dépasse le solde restant ({enrollment.balance} XAF)."}, status=status.HTTP_400_BAD_REQUEST)

        payment = Payment.objects.create(user=request.user, amount=amount, currency="XAF", provider=provider, purpose="training_fee")
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

        Settlement.objects.create(
            enrollment=enrollment, amount=amount, method=payment.get_provider_display(),
            payment=payment, recorded_by=request.user,
        )
        log_action(actor=request.user, action="enrollment.pay", metadata={"enrollment": enrollment.matricule, "amount": str(amount)})

        return Response(EnrollmentSerializer(enrollment).data)


class SettlementViewSet(viewsets.ModelViewSet):
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["enrollment"]
    queryset = Settlement.objects.select_related("enrollment")

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


class CertificateViewSet(viewsets.ModelViewSet):
    serializer_class = CertificateSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Certificate.objects.select_related("enrollment__participant", "enrollment__training")
        if user.is_admin_role:
            return qs
        return qs.filter(enrollment__participant=user)

    def create(self, request, *args, **kwargs):
        enrollment_id = request.data.get("enrollment")
        enrollment = Enrollment.objects.filter(pk=enrollment_id).first()
        if not enrollment:
            return Response({"detail": "Inscription introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if enrollment.status != Enrollment.Status.VALIDATED:
            return Response({"detail": "L'inscription doit être validée avant délivrance de l'attestation."}, status=status.HTTP_400_BAD_REQUEST)
        if enrollment.balance > 0:
            return Response(
                {"detail": f"Le solde ({enrollment.balance} XAF) doit être entièrement réglé avant délivrance de l'attestation."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        certificate, _ = Certificate.objects.get_or_create(enrollment=enrollment, defaults={"validated_by": request.user})
        log_action(actor=request.user, action="certificate.issue", metadata={"enrollment": enrollment.matricule})
        return Response(CertificateSerializer(certificate).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        certificate = self.get_object()
        pdf_bytes = build_certificate_pdf(certificate)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="attestation-{certificate.enrollment.matricule}.pdf"'
        return response


class BadgeViewSet(viewsets.ModelViewSet):
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["purpose", "is_active", "user"]
    search_fields = ["matricule"]
    queryset = Badge.objects.select_related("user")

    @action(detail=True, methods=["get"], url_path="pdf", permission_classes=[permissions.IsAuthenticated])
    def download_pdf(self, request, pk=None):
        badge = self.get_object()
        if not request.user.is_admin_role and badge.user_id != request.user.id:
            return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
        pdf_bytes = build_badge_pdf(badge)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="badge-{badge.matricule}.pdf"'
        return response
