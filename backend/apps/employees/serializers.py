from rest_framework import serializers

from .models import Employee, JobApplication


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id", "user", "first_name", "last_name", "position",
            "contact", "hire_date", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class JobApplicationSerializer(serializers.ModelSerializer):
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, default=None)

    class Meta:
        model = JobApplication
        fields = [
            "id", "applicant", "applicant_username", "full_name", "email", "phone",
            "desired_position", "motivation", "cv_file", "status", "status_display",
            "reviewer_notes", "reviewed_by", "reviewed_by_username", "reviewed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "applicant", "status", "reviewer_notes", "reviewed_by", "reviewed_at",
            "created_at", "updated_at",
        ]


class JobApplicationReviewSerializer(serializers.ModelSerializer):
    """Réservé à l'administration : changement de statut + notes d'examen."""

    class Meta:
        model = JobApplication
        fields = ["status", "reviewer_notes"]
