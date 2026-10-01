from rest_framework import serializers

from apps.bookings.utils import upcoming_unavailability

from .models import Venue


class VenueSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    upcoming_unavailability = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    has_active_discount = serializers.SerializerMethodField()
    discounted_price_per_day = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "id", "name", "address", "city", "capacity", "price_per_day",
            "amenities", "description", "photo", "is_active", "is_available", "upcoming_unavailability",
            "average_rating", "review_count",
            "discount_percent", "discount_label", "discount_valid_until", "has_active_discount", "discounted_price_per_day",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_available(self, obj):
        return obj.is_currently_available()

    def get_upcoming_unavailability(self, obj):
        return upcoming_unavailability(obj)

    def get_average_rating(self, obj):
        avg = obj.average_rating()
        return round(float(avg), 1) if avg is not None else None

    def get_review_count(self, obj):
        return obj.review_count()

    def get_has_active_discount(self, obj):
        return obj.has_active_discount()

    def get_discounted_price_per_day(self, obj):
        return obj.discounted_price_per_day()
