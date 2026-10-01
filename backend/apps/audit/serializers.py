from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "actor_name", "action", "method", "path", "status_code", "ip_address", "metadata", "created_at"]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor:
            return "Anonyme"
        return obj.actor.get_full_name() or obj.actor.username
