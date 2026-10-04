from rest_framework import serializers

from .models import Ticket, TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    sold_count = serializers.SerializerMethodField()
    remaining_quota = serializers.SerializerMethodField()
    event_title = serializers.CharField(source="event.title", read_only=True)

    def get_sold_count(self, obj):
        if hasattr(obj, "marketplace_sold_count"):
            return obj.marketplace_sold_count
        return obj.sold_count

    def get_remaining_quota(self, obj):
        return obj.quota - self.get_sold_count(obj)

    class Meta:
        model = TicketType
        fields = [
            "id", "event", "event_title", "name", "price", "currency", "quota",
            "sold_count", "remaining_quota", "sale_start", "sale_end", "is_active", "is_premium", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    ticket_type_name = serializers.CharField(source="ticket_type.name", read_only=True)
    event = serializers.IntegerField(source="ticket_type.event_id", read_only=True)
    event_title = serializers.CharField(source="ticket_type.event.title", read_only=True)
    event_start_date = serializers.DateTimeField(source="ticket_type.event.start_date", read_only=True)
    event_photo = serializers.ImageField(source="ticket_type.event.photo", read_only=True, default=None)
    venue_name = serializers.CharField(source="ticket_type.event.venue.name", read_only=True, default=None)
    price = serializers.DecimalField(source="ticket_type.price", max_digits=12, decimal_places=2, read_only=True)
    currency = serializers.CharField(source="ticket_type.currency", read_only=True)
    is_premium = serializers.BooleanField(source="ticket_type.is_premium", read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id", "ticket_type", "ticket_type_name", "event", "event_title", "event_start_date", "event_photo", "venue_name",
            "owner", "code", "status", "price", "currency", "is_premium",
            "buyer_first_name", "buyer_last_name", "buyer_email", "buyer_phone",
            "purchased_at", "checked_in_at",
        ]
        read_only_fields = fields


class TicketPurchaseSerializer(serializers.Serializer):
    ticket_type = serializers.PrimaryKeyRelatedField(queryset=TicketType.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=20, default=1)
    payment_provider = serializers.ChoiceField(choices=["demo", "paypal", "mobile_money", "freemopay", "kob"], default="demo")
    buyer_first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    buyer_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    buyer_email = serializers.EmailField(required=False, allow_blank=True)
    buyer_phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate(self, attrs):
        ticket_type = attrs["ticket_type"]
        unavailability_reason = ticket_type.sale_unavailability_reason()
        if unavailability_reason:
            raise serializers.ValidationError(unavailability_reason)
        if attrs["quantity"] > ticket_type.remaining_quota:
            raise serializers.ValidationError(
                f"Il ne reste que {ticket_type.remaining_quota} billet(s) disponible(s)."
            )
        return attrs


class TicketScanSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="Contenu signé encodé dans le QR code")
