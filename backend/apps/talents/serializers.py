from rest_framework import serializers

from .models import TalentMission, TalentPortfolioItem, TalentProfile


class TalentPortfolioItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentPortfolioItem
        fields = ["id", "profile", "image", "caption", "created_at"]
        read_only_fields = ["id", "created_at"]


class TalentProfileSerializer(serializers.ModelSerializer):
    portfolio_items = TalentPortfolioItemSerializer(many=True, read_only=True)
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)
    disponibilite_display = serializers.CharField(source="get_disponibilite_display", read_only=True)
    opportunity_type_display = serializers.CharField(source="get_opportunity_type_display", read_only=True)

    class Meta:
        model = TalentProfile
        fields = [
            "id", "user", "full_name", "formation", "competences", "experience", "city",
            "disponibilite", "disponibilite_display", "opportunity_type", "opportunity_type_display",
            "photo", "verification_status", "verification_status_display", "is_verified",
            "is_active", "portfolio_items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user", "verification_status", "verification_status_display", "is_verified", "created_at", "updated_at",
        ]


class TalentVerificationSerializer(serializers.ModelSerializer):
    """Réservé à l'administration."""

    class Meta:
        model = TalentProfile
        fields = ["verification_status"]


class TalentMissionSerializer(serializers.ModelSerializer):
    mission_type_display = serializers.CharField(source="get_mission_type_display", read_only=True)

    class Meta:
        model = TalentMission
        fields = ["id", "title", "provider_name", "city", "description", "mission_type", "mission_type_display", "starts_at", "compensation", "skills", "is_active", "is_demo", "created_at"]


class TalentMissionManageSerializer(serializers.ModelSerializer):
    mission_type_display = serializers.CharField(source="get_mission_type_display", read_only=True)

    class Meta:
        model = TalentMission
        fields = ["id", "title", "provider_name", "city", "description", "mission_type", "mission_type_display", "starts_at", "compensation", "skills", "is_active", "is_demo", "created_at"]
        read_only_fields = ["id", "provider_name", "mission_type_display", "is_demo", "created_at"]
