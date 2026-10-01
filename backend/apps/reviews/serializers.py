from rest_framework import serializers

from .models import EquipmentReview, ProfessionalReview, ProviderReview, VenueReview


class VenueReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = VenueReview
        fields = ["id", "venue", "author", "author_name", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def validate_rating(self, value):
        if (value * 2) % 1 != 0:
            raise serializers.ValidationError("La note doit être exprimée par pas de 0,5 étoile.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        venue = attrs.get("venue") or getattr(self.instance, "venue", None)
        if request and not self.instance and VenueReview.objects.filter(venue=venue, author=request.user).exists():
            raise serializers.ValidationError("Vous avez déjà publié un avis pour cette salle. Modifiez-le plutôt.")
        return attrs


class ProviderReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ProviderReview
        fields = ["id", "provider", "author", "author_name", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def validate_rating(self, value):
        if (value * 2) % 1 != 0:
            raise serializers.ValidationError("La note doit être exprimée par pas de 0,5 étoile.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        provider = attrs.get("provider") or getattr(self.instance, "provider", None)
        if request and not self.instance and ProviderReview.objects.filter(provider=provider, author=request.user).exists():
            raise serializers.ValidationError("Vous avez déjà publié un avis pour ce prestataire. Modifiez-le plutôt.")
        return attrs


class EquipmentReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentReview
        fields = ["id", "equipment", "author", "author_name", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def validate_rating(self, value):
        if (value * 2) % 1 != 0:
            raise serializers.ValidationError("La note doit être exprimée par pas de 0,5 étoile.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        equipment = attrs.get("equipment") or getattr(self.instance, "equipment", None)
        if request and not self.instance and EquipmentReview.objects.filter(equipment=equipment, author=request.user).exists():
            raise serializers.ValidationError("Vous avez déjà publié un avis pour ce matériel. Modifiez-le plutôt.")
        return attrs


class ProfessionalReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ProfessionalReview
        fields = ["id", "profile", "author", "author_name", "rating", "comment", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def validate_rating(self, value):
        if (value * 2) % 1 != 0:
            raise serializers.ValidationError("La note doit être exprimée par pas de 0,5 étoile.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        profile = attrs.get("profile") or getattr(self.instance, "profile", None)
        if request and not self.instance:
            if ProfessionalReview.objects.filter(profile=profile, author=request.user).exists():
                raise serializers.ValidationError("Vous avez déjà publié un avis pour ce profil. Modifiez-le plutôt.")
            from apps.marketplace.views import has_active_subscription

            if not (request.user.is_admin_role or has_active_subscription(request.user, profile.marketplace_type)):
                raise serializers.ValidationError("Un abonnement actif à ce marketplace est requis pour laisser un avis.")
        return attrs
