from rest_framework import serializers

from .models import LandingMedia, PackItem


class LandingMediaSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(source="image")

    class Meta:
        model = LandingMedia
        fields = ["id", "category", "scope", "tag", "tier", "label", "caption", "price_label", "budget_label", "photo", "order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PackItemSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(read_only=True)
    resource_photo = serializers.SerializerMethodField()
    resource_price_label = serializers.SerializerMethodField()
    resource_price = serializers.SerializerMethodField()
    resource_is_active = serializers.SerializerMethodField()

    class Meta:
        model = PackItem
        fields = [
            "id", "pack", "resource_type", "venue", "provider", "equipment",
            "default_quantity", "is_optional", "order",
            "resource_name", "resource_photo", "resource_price_label", "resource_price", "resource_is_active",
        ]
        read_only_fields = ["id"]

    def get_resource_photo(self, obj):
        resource = obj.resource
        if not resource or not resource.photo:
            return None
        request = self.context.get("request")
        url = resource.photo.url
        return request.build_absolute_uri(url) if request else url

    def get_resource_price_label(self, obj):
        resource = obj.resource
        if not resource:
            return None
        if obj.resource_type == "venue":
            return f"{resource.price_per_day} XAF / jour"
        if obj.resource_type == "provider":
            return resource.price_range or None
        if obj.resource_type == "equipment":
            return f"{resource.price_per_unit} XAF / unité"
        return None

    def get_resource_price(self, obj):
        """Prix numérique unitaire, utilisé pour calculer un devis estimatif côté
        client. Absent pour les prestataires (price_range est une fourchette
        textuelle, pas un montant unique exploitable)."""
        resource = obj.resource
        if not resource:
            return None
        if obj.resource_type == "venue":
            return resource.price_per_day
        if obj.resource_type == "equipment":
            return resource.price_per_unit
        return None

    def get_resource_is_active(self, obj):
        resource = obj.resource
        return bool(resource and resource.is_active)

    def validate(self, attrs):
        resource_type = attrs.get("resource_type", getattr(self.instance, "resource_type", None))
        for field in ("venue", "provider", "equipment"):
            if field != resource_type:
                attrs[field] = None
        if not attrs.get(resource_type):
            raise serializers.ValidationError({resource_type: "Ce champ est requis pour ce type de ressource."})
        return attrs
