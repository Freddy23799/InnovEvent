from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Carrier,
    Delivery,
    DeliveryExpense,
    DeliveryProof,
    DeliveryReturn,
    DeliveryStatusHistory,
    DeliveryZone,
    Driver,
    Parcel,
    PricingRule,
    Vehicle,
)

User = get_user_model()


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = ["id", "name", "base_fee", "price_per_km", "price_per_kg", "urgent_surcharge_percent", "order", "is_active"]
        read_only_fields = ["id"]


class CarrierSerializer(serializers.ModelSerializer):
    service_zone_name = serializers.CharField(source="service_zone.name", read_only=True, default=None)
    deliveries_count = serializers.IntegerField(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = Carrier
        fields = [
            "id", "user", "username", "name", "company_name", "carrier_type", "phone", "whatsapp", "email", "address",
            "service_zone", "service_zone_name", "transport_type", "id_number", "status", "documents",
            "is_active", "created_at", "deliveries_count",
        ]
        read_only_fields = ["id", "created_at"]


class AdminCreateCarrierSerializer(serializers.Serializer):
    """Réservé à l'administration : crée un compte transporteur, soit en le
    rattachant à un compte `partner` existant sans transporteur, soit en
    créant ce compte dans la foulée — même pattern que
    `AdminCreateProfileSerializer` (apps.marketplace) pour les prestataires."""

    name = serializers.CharField(max_length=150)
    company_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    carrier_type = serializers.ChoiceField(choices=Carrier.CarrierType.choices, default=Carrier.CarrierType.INDEPENDENT)
    phone = serializers.CharField(max_length=30)
    whatsapp = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    service_zone = serializers.PrimaryKeyRelatedField(queryset=DeliveryZone.objects.all(), required=False, allow_null=True)
    transport_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    id_number = serializers.CharField(max_length=50, required=False, allow_blank=True)

    owner_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.PARTNER, carrier_profile__isnull=True),
        required=False, allow_null=True,
    )
    new_owner_username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    new_owner_email = serializers.EmailField(required=False, allow_blank=True)
    new_owner_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    new_owner_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("owner_user") and not attrs.get("new_owner_username"):
            raise serializers.ValidationError(
                "Choisissez un compte transporteur existant ou renseignez un identifiant pour en créer un nouveau."
            )
        return attrs


class VehicleSerializer(serializers.ModelSerializer):
    carrier_name = serializers.CharField(source="carrier.name", read_only=True, default=None)
    is_insurance_expiring_soon = serializers.BooleanField(read_only=True)
    is_inspection_expiring_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id", "plate_number", "brand", "model", "year", "vehicle_type", "capacity_kg", "max_volume_m3",
            "mileage_km", "consumption_l_100km", "carrier", "carrier_name", "insurance_expiry",
            "technical_inspection_expiry", "status", "photo", "is_active", "created_at",
            "is_insurance_expiring_soon", "is_inspection_expiring_soon",
        ]
        read_only_fields = ["id", "created_at"]


class DriverSerializer(serializers.ModelSerializer):
    carrier_name = serializers.CharField(source="carrier.name", read_only=True, default=None)
    current_vehicle_plate = serializers.CharField(source="current_vehicle.plate_number", read_only=True, default=None)
    is_license_expiring_soon = serializers.BooleanField(read_only=True)
    deliveries_count = serializers.IntegerField(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = Driver
        fields = [
            "id", "user", "username", "full_name", "photo", "id_card_photo", "license_photo", "phone", "whatsapp", "email",
            "license_number", "license_category", "license_expiry", "address", "carrier", "carrier_name",
            "current_vehicle", "current_vehicle_plate", "status", "documents", "is_active", "created_at",
            "is_license_expiring_soon", "deliveries_count",
        ]
        read_only_fields = ["id", "created_at"]


class ParcelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcel
        fields = [
            "id", "delivery", "description", "category", "quantity", "weight_kg", "dimensions",
            "declared_value", "is_fragile", "is_insured", "special_instructions", "photo",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {"delivery": {"required": False}}


class DeliveryStatusHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True, default=None)
    old_status_display = serializers.CharField(source="get_old_status_display", read_only=True)
    new_status_display = serializers.CharField(source="get_new_status_display", read_only=True)

    class Meta:
        model = DeliveryStatusHistory
        fields = ["id", "actor", "actor_name", "old_status", "old_status_display", "new_status", "new_status_display", "comment", "created_at"]
        read_only_fields = fields


class DeliveryProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryProof
        fields = [
            "id", "delivery", "signature_image", "photo", "otp_code", "receiver_name", "receiver_phone",
            "latitude", "longitude", "confirmed_at",
        ]
        read_only_fields = ["id", "confirmed_at"]


class DeliveryListSerializer(serializers.ModelSerializer):
    """Aperçu léger pour les listes — pas de colis/historique imbriqués."""

    client_name = serializers.CharField(source="client.get_full_name", read_only=True, default=None)
    carrier_name = serializers.CharField(source="carrier.name", read_only=True, default=None)
    driver_name = serializers.CharField(source="driver.full_name", read_only=True, default=None)
    vehicle_plate = serializers.CharField(source="vehicle.plate_number", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    parcels_count = serializers.IntegerField(source="parcels.count", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id", "reference", "tracking_code", "client", "client_name", "client_phone",
            "pickup_address", "destination_address", "delivery_type", "priority", "amount",
            "payment_mode", "carrier", "carrier_name", "driver", "driver_name", "vehicle", "vehicle_plate",
            "status", "status_display", "scheduled_date", "scheduled_time", "parcels_count", "created_at",
        ]
        read_only_fields = ["id", "reference", "tracking_code", "created_at"]


class DeliverySerializer(serializers.ModelSerializer):
    """Détail complet, avec colis imbriqués (créés/mis à jour avec la
    livraison, même convention que `ProfessionalBookingRequestSerializer` /
    `RequestedEquipmentItem` dans apps.marketplace)."""

    parcels = ParcelSerializer(many=True, required=False)
    status_history = DeliveryStatusHistorySerializer(many=True, read_only=True)
    proof = DeliveryProofSerializer(read_only=True)
    client_name = serializers.CharField(source="client.get_full_name", read_only=True, default=None)
    carrier_name = serializers.CharField(source="carrier.name", read_only=True, default=None)
    driver_name = serializers.CharField(source="driver.full_name", read_only=True, default=None)
    vehicle_plate = serializers.CharField(source="vehicle.plate_number", read_only=True, default=None)
    zone_name = serializers.CharField(source="zone.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    estimated_amount = serializers.SerializerMethodField()
    return_record = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id", "reference", "tracking_code", "client", "client_name", "client_phone",
            "sender_name", "sender_phone", "pickup_address", "recipient_name", "recipient_phone",
            "destination_address", "delivery_type", "priority", "description", "special_instructions",
            "zone", "zone_name", "distance_km", "amount", "estimated_amount", "payment_mode", "payment",
            "carrier", "carrier_name", "driver", "driver_name", "vehicle", "vehicle_plate",
            "status", "status_display", "scheduled_date", "scheduled_time", "internal_notes",
            "related_booking", "related_marketplace_order",
            "last_latitude", "last_longitude", "last_location_at",
            "client_latitude", "client_longitude", "client_location_at",
            "parcels", "status_history", "proof", "return_record",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "tracking_code", "created_by", "created_at", "updated_at",
            "last_latitude", "last_longitude", "last_location_at",
            "client_latitude", "client_longitude", "client_location_at",
        ]

    def get_estimated_amount(self, obj):
        return obj.estimate_amount()

    def get_return_record(self, obj):
        try:
            return DeliveryReturnSerializer(obj.return_record).data
        except DeliveryReturn.DoesNotExist:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # « Notes internes » : réservées à l'administration, jamais visibles
        # par un transporteur ou un chauffeur même lorsqu'ils consultent
        # leurs propres livraisons.
        request = self.context.get("request")
        if request and not request.user.is_admin_role:
            data.pop("internal_notes", None)
        return data

    def create(self, validated_data):
        parcels_data = validated_data.pop("parcels", [])
        delivery = Delivery.objects.create(**validated_data)
        for parcel_data in parcels_data:
            Parcel.objects.create(delivery=delivery, **parcel_data)
        return delivery

    def update(self, instance, validated_data):
        parcels_data = validated_data.pop("parcels", None)
        instance = super().update(instance, validated_data)
        if parcels_data is not None:
            instance.parcels.all().delete()
            for parcel_data in parcels_data:
                Parcel.objects.create(delivery=instance, **parcel_data)
        return instance


class DeliveryAssignSerializer(serializers.Serializer):
    carrier = serializers.PrimaryKeyRelatedField(queryset=Carrier.objects.all(), required=False, allow_null=True)
    driver = serializers.PrimaryKeyRelatedField(queryset=Driver.objects.all(), required=False, allow_null=True)
    vehicle = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.all(), required=False, allow_null=True)
    force = serializers.BooleanField(default=False, help_text="Ignore les avertissements de disponibilité/capacité.")


class DeliveryChangeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Delivery.Status.choices)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


class DeliveryTrackSerializer(serializers.ModelSerializer):
    """Vue publique du suivi — jamais de téléphone/adresse complète/nom du
    client (consigne explicite section 6)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_history = serializers.SerializerMethodField()
    pickup_city = serializers.SerializerMethodField()
    destination_city = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "reference", "tracking_code", "status", "status_display", "created_at",
            "scheduled_date", "pickup_city", "destination_city", "status_history",
        ]

    def _city(self, address):
        return (address or "").split(",")[-1].strip() or address

    def get_pickup_city(self, obj):
        return self._city(obj.pickup_address)

    def get_destination_city(self, obj):
        return self._city(obj.destination_address)

    def get_status_history(self, obj):
        return [
            {"status": h.new_status, "status_display": h.get_new_status_display(), "created_at": h.created_at}
            for h in obj.status_history.all()
        ]


class PricingRuleSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True, default=None)

    class Meta:
        model = PricingRule
        fields = [
            "id", "zone", "zone_name", "vehicle_type", "priority", "min_weight_kg", "max_weight_kg",
            "extra_fee", "multiplier_percent", "label", "order", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DeliveryReturnSerializer(serializers.ModelSerializer):
    delivery_reference = serializers.CharField(source="delivery.reference", read_only=True)
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    refund_status_display = serializers.CharField(source="get_refund_status_display", read_only=True)
    initiated_by_name = serializers.CharField(source="initiated_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = DeliveryReturn
        fields = [
            "id", "delivery", "delivery_reference", "reason", "reason_display", "condition_notes",
            "refund_status", "refund_status_display", "refund_amount", "initiated_by", "initiated_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "delivery", "initiated_by", "created_at"]


class DeliveryExpenseSerializer(serializers.ModelSerializer):
    carrier_name = serializers.CharField(source="carrier.name", read_only=True, default=None)
    vehicle_plate = serializers.CharField(source="vehicle.plate_number", read_only=True, default=None)
    delivery_reference = serializers.CharField(source="delivery.reference", read_only=True, default=None)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = DeliveryExpense
        fields = [
            "id", "delivery", "delivery_reference", "carrier", "carrier_name", "vehicle", "vehicle_plate",
            "category", "category_display", "amount", "description", "expense_date",
            "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class DeliveryReturnCreateSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=DeliveryReturn.Reason.choices)
    condition_notes = serializers.CharField(required=False, allow_blank=True, default="")
    refund_status = serializers.ChoiceField(choices=DeliveryReturn.RefundStatus.choices, default=DeliveryReturn.RefundStatus.NONE)
    refund_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True, default=None)


class CreateDeliveryFromSourceSerializer(serializers.Serializer):
    """Pont depuis une commande existante (Phase 2, section 18) — pré-remplit
    une livraison à partir d'une réservation (`Booking`) ou d'une commande
    marketplace (`MarketplaceOrder`) déjà validée, sans dupliquer la logique
    de validation propre à ces modules."""

    pickup_address = serializers.CharField(default="Siège InnovEvent Group")
    destination_address = serializers.CharField(required=False, allow_blank=True, default="")
    scheduled_date = serializers.DateField(required=False, allow_null=True, default=None)
