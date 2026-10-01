from rest_framework import serializers

from .models import Booking

ACTIVE_STATUSES = [Booking.Status.PENDING, Booking.Status.CONFIRMED]


class BookingSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)
    resource_label = serializers.SerializerMethodField()
    estimated_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, allow_null=True)
    payment_status = serializers.CharField(source="payment.status", read_only=True, default=None)
    payment_ref = serializers.CharField(source="payment.transaction_ref", read_only=True, default=None)

    class Meta:
        model = Booking
        fields = [
            "id", "event", "event_title", "resource_type", "venue", "provider", "equipment",
            "resource_label", "quantity", "start_datetime", "end_datetime", "status", "notes",
            "estimated_cost", "payment_status", "payment_ref",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_resource_label(self, obj):
        resource = obj.resource
        return str(resource) if resource else None

    def validate(self, attrs):
        resource_type = attrs.get("resource_type", getattr(self.instance, "resource_type", None))
        venue = attrs.get("venue", getattr(self.instance, "venue", None))
        provider = attrs.get("provider", getattr(self.instance, "provider", None))
        equipment = attrs.get("equipment", getattr(self.instance, "equipment", None))
        start = attrs.get("start_datetime", getattr(self.instance, "start_datetime", None))
        end = attrs.get("end_datetime", getattr(self.instance, "end_datetime", None))
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 1))

        if end and start and end <= start:
            raise serializers.ValidationError({"end_datetime": "La date de fin doit être postérieure à la date de début."})

        resource_map = {
            Booking.ResourceType.VENUE: venue,
            Booking.ResourceType.PROVIDER: provider,
            Booking.ResourceType.EQUIPMENT: equipment,
        }
        selected = resource_map.get(resource_type)
        if not selected:
            raise serializers.ValidationError({"resource_type": "La ressource correspondant au type sélectionné est requise."})
        others = [v for k, v in resource_map.items() if k != resource_type and v]
        if others:
            raise serializers.ValidationError("Une seule ressource (salle, prestataire ou matériel) doit être renseignée par réservation.")

        exclude_id = self.instance.pk if self.instance else None

        if resource_type in (Booking.ResourceType.VENUE, Booking.ResourceType.PROVIDER):
            field_name = resource_type
            overlapping = Booking.objects.filter(
                **{field_name: selected},
                status__in=ACTIVE_STATUSES,
                start_datetime__lt=end,
                end_datetime__gt=start,
            )
            if exclude_id:
                overlapping = overlapping.exclude(pk=exclude_id)
            if overlapping.exists():
                raise serializers.ValidationError(
                    f"Conflit détecté : {selected} est déjà réservé(e) sur ce créneau."
                )
        elif resource_type == Booking.ResourceType.EQUIPMENT:
            available = equipment.available_quantity(start, end, exclude_booking_id=exclude_id)
            if quantity > available:
                raise serializers.ValidationError(
                    f"Conflit détecté : seulement {available} unité(s) disponible(s) pour « {equipment} » sur ce créneau."
                )

        return attrs


class BookingPaymentSerializer(serializers.Serializer):
    payment_provider = serializers.ChoiceField(
        choices=["demo", "mtn_momo", "orange_money", "card", "paypal", "mobile_money", "freemopay", "kob"],
        default="demo",
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True)
