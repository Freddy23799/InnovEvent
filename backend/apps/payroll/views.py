from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin

from .models import Payslip
from .pdf import build_payslip_pdf
from .serializers import PayslipSerializer


class PayslipViewSet(viewsets.ModelViewSet):
    serializer_class = PayslipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["employee", "period_month", "period_year"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Payslip.objects.select_related("employee")
        if user.is_admin_role:
            return qs
        return qs.filter(employee__user=user)

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        payslip = self.get_object()
        if not request.user.is_admin_role and payslip.employee.user_id != request.user.id:
            return Response({"detail": "Accès refusé."}, status=403)
        pdf_bytes = build_payslip_pdf(payslip)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="paie-{payslip.employee.last_name}-{payslip.period_month:02d}-{payslip.period_year}.pdf"'
        return response
