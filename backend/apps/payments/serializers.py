from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "user", "user_name", "amount", "currency", "provider", "status",
            "transaction_ref", "provider_reference", "purpose",
            "failure_reason", "created_at", "completed_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
