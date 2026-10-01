from rest_framework import serializers

from .models import CompanyDocument, CompanyProfile


class CompanyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDocument
        fields = ["id", "profile", "file", "label", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class CompanyProfileSerializer(serializers.ModelSerializer):
    documents = CompanyDocumentSerializer(many=True, read_only=True)
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)

    class Meta:
        model = CompanyProfile
        fields = [
            "id", "user", "raison_sociale", "activite", "rccm", "niu", "adresse", "representant",
            "phone", "email", "verification_status", "verification_status_display", "is_verified",
            "is_active", "documents", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "verification_status", "verification_status_display", "is_verified", "created_at", "updated_at"]


class CompanyVerificationSerializer(serializers.ModelSerializer):
    """Réservé à l'administration : seule habilitée à faire progresser le
    statut de vérification (même principe que `ProfessionalProfileBadgesSerializer`)."""

    class Meta:
        model = CompanyProfile
        fields = ["verification_status"]
