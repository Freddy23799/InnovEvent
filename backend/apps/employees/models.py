from django.conf import settings
from django.db import models

from apps.documents.validators import validate_document_file


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profile"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=150)
    contact = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.position}"


class JobApplication(models.Model):
    """Candidature envoyée par un client depuis son compte pour postuler à un
    poste dans l'entreprise — jointe à un CV, examinée par l'administration."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        REVIEWED = "reviewed", "Examinée"
        ACCEPTED = "accepted", "Acceptée"
        REJECTED = "rejected", "Refusée"

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_applications",
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    desired_position = models.CharField(max_length=150)
    motivation = models.TextField(blank=True)
    cv_file = models.FileField(upload_to="employees/job_applications/cv/", validators=[validate_document_file])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_job_applications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.desired_position} ({self.get_status_display()})"
