from rest_framework import serializers

from apps.bookings.utils import upcoming_unavailability

from .models import Equipment, Expense, StockMovement


class EquipmentSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    upcoming_unavailability = serializers.SerializerMethodField()
    has_active_discount = serializers.SerializerMethodField()
    discounted_price_per_unit = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = [
            "id", "name", "category", "quantity_total", "price_per_unit", "photo",
            "description", "is_active", "is_available", "upcoming_unavailability",
            "discount_percent", "discount_label", "discount_valid_until", "has_active_discount", "discounted_price_per_unit",
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

    def get_discounted_price_per_unit(self, obj):
        return obj.discounted_price_per_unit()

    def get_average_rating(self, obj):
        avg = obj.average_rating()
        return round(float(avg), 1) if avg is not None else None

    def get_review_count(self, obj):
        return obj.review_count()

    def update(self, instance, validated_data):
        # La quantité en stock ne se modifie plus qu'via un mouvement de stock
        # (entrée/sortie), afin de garder un historique complet et fiable.
        validated_data.pop("quantity_total", None)
        return super().update(instance, validated_data)


class StockMovementSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source="equipment.name", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()
    resulting_quantity = serializers.IntegerField(source="equipment.quantity_total", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id", "equipment", "equipment_name", "movement_type", "reason", "quantity", "notes",
            "recorded_by", "recorded_by_name", "resulting_quantity", "created_at",
        ]
        read_only_fields = ["id", "recorded_by", "created_at"]

    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() if obj.recorded_by else ""

    def validate(self, attrs):
        equipment = attrs.get("equipment")
        movement_type = attrs.get("movement_type")
        quantity = attrs.get("quantity")
        if movement_type == StockMovement.MovementType.OUT and equipment and quantity and quantity > equipment.quantity_total:
            raise serializers.ValidationError(
                f"Stock insuffisant pour « {equipment.name} » : {equipment.quantity_total} unité(s) disponible(s)."
            )
        return attrs


class ExpenseSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source="equipment.name", read_only=True, default=None)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id", "category", "label", "amount", "equipment", "equipment_name", "stock_movement",
            "notes", "incurred_at", "recorded_by", "recorded_by_name", "created_at",
        ]
        read_only_fields = ["id", "recorded_by", "created_at"]

    def get_recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() if obj.recorded_by else ""
