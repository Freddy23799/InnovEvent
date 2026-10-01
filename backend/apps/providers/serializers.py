from rest_framework import serializers

from apps.bookings.utils import upcoming_unavailability

from .models import Provider


class ProviderSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    upcoming_unavailability = serializers.SerializerMethodField()
    has_active_discount = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = [
            "id", "name", "category", "contact_email", "contact_phone", "address", "city", "photo", "identity_number",
            "description", "price_range", "is_active", "is_available", "upcoming_unavailability",
            "discount_percent", "discount_label", "discount_valid_until", "has_active_discount",
            "average_rating", "review_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_available(self, obj):
        return obj.is_currently_available()

    def get_upcoming_unavailability(self, obj):
        return upcoming_unavailability(obj)

    def get_has_active_discount(self, obj):
        return obj.has_active_discount()

    def get_average_rating(self, obj):
        avg = obj.average_rating()
        return round(float(avg), 1) if avg is not None else None

    def get_review_count(self, obj):
        return obj.review_count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not (request and request.user and request.user.is_authenticated):
            # Pièce d'identité/immatriculation réservée aux utilisateurs connectés
            # (usage interne : signature des badges) — jamais exposée à la consultation publique.
            data.pop("identity_number", None)
        return data


class ProviderScanSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="Contenu signé encodé dans le QR du badge prestataire")
