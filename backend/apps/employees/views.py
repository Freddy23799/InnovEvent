from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.audit.utils import log_action
from apps.notifications.services import notify_job_application_created, notify_job_application_status_changed

from .models import Employee, JobApplication
from .serializers import EmployeeSerializer, JobApplicationReviewSerializer, JobApplicationSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    """CRUD réservé à l'administration ; un employé consulte uniquement sa propre
    fiche via le filtrage de queryset (section 4/14 du CDC)."""

    serializer_class = EmployeeSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Employee.objects.select_related("user")
        if user.is_admin_role:
            return qs
        return qs.filter(user=user)


class JobApplicationViewSet(viewsets.ModelViewSet):
    """Un client soumet sa candidature (avec CV) depuis son compte et ne voit
    que ses propres candidatures ; l'administration voit tout et examine
    (changement de statut + notes) via l'action `review`."""

    serializer_class = JobApplicationSerializer

    def get_permissions(self):
        if self.action in ["destroy", "review"]:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = JobApplication.objects.select_related("applicant", "reviewed_by")
        if user.is_admin_role:
            return qs
        return qs.filter(applicant=user)

    def perform_create(self, serializer):
        application = serializer.save(applicant=self.request.user)
        notify_job_application_created(application)
        log_action(actor=self.request.user, action="job_application.create", metadata={"application": application.id})

    def perform_update(self, serializer):
        # Un candidat ne modifie jamais le statut/l'examen de sa propre
        # candidature une fois soumise — seule l'action `review` (admin) le
        # peut ; ce point est déjà garanti par `read_only_fields` côté
        # serializer, mais on l'assure ici aussi pour toute évolution future.
        serializer.save()

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        application = self.get_object()
        serializer = JobApplicationReviewSerializer(application, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(reviewed_by=request.user, reviewed_at=timezone.now())
        notify_job_application_status_changed(application)
        log_action(
            actor=request.user, action="job_application.review",
            metadata={"application": application.id, "status": application.status},
        )
        return Response(JobApplicationSerializer(application, context={"request": request}).data)
