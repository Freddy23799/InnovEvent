from rest_framework import serializers

from django.utils import timezone

from apps.marketplace.models import MarketplaceSubscription, MarketplaceType

from .models import TalentPortfolioItem, TalentProfile


class TalentPortfolioItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentPortfolioItem
        fields = ["id", "profile", "image", "caption", "created_at"]
        # `profile` est imposé côté serveur (perform_create) : modifiable, il
        # permettait de déplacer une image vers le portfolio d'un autre talent.
        read_only_fields = ["id", "profile", "created_at"]


class TalentProfileSerializer(serializers.ModelSerializer):
    portfolio_items = TalentPortfolioItemSerializer(many=True, read_only=True)
    verification_status_display = serializers.CharField(source="get_verification_status_display", read_only=True)
    disponibilite_display = serializers.CharField(source="get_disponibilite_display", read_only=True)
    opportunity_type_display = serializers.CharField(source="get_opportunity_type_display", read_only=True)
    missing_fields = serializers.ListField(child=serializers.CharField(), read_only=True)
    visible_until = serializers.SerializerMethodField()

    class Meta:
        model = TalentProfile
        fields = [
            "id", "user", "full_name", "formation", "competences", "experience", "city",
            "disponibilite", "disponibilite_display", "opportunity_type", "opportunity_type_display",
            "photo", "verification_status", "verification_status_display", "is_verified",
            "is_active", "portfolio_items", "missing_fields", "visible_until", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user", "verification_status", "verification_status_display", "is_verified", "created_at", "updated_at",
        ]


    def get_visible_until(self, obj):
        """Fin de l'abonnement « Visibilité talent » en cours, sinon None."""
        subscription = MarketplaceSubscription.objects.filter(
            user_id=obj.user_id, marketplace_type=MarketplaceType.TALENT_MISSIONS, expires_at__gt=timezone.now(),
        ).order_by("-expires_at").first()
        return subscription.expires_at if subscription else None


class TalentVerificationSerializer(serializers.ModelSerializer):
    """Réservé à l'administration."""

    class Meta:
        model = TalentProfile
        fields = ["verification_status"]
