from rest_framework import serializers

from .models import Event, EventExpense, EventParticipant, EventTask


class EventTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventTask
        fields = ["id", "event", "title", "description", "assignee", "due_date", "status", "priority", "created_at"]
        read_only_fields = ["id", "created_at"]


class EventParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventParticipant
        fields = ["id", "event", "user", "full_name", "email", "checked_in", "checked_in_at", "registered_at"]
        read_only_fields = ["id", "checked_in_at", "registered_at"]
        extra_kwargs = {"user": {"required": False}}
        # Un invité externe n'a pas de compte (user=NULL) : PostgreSQL ne considère pas deux
        # NULL comme égaux, donc la contrainte unique_together (event, user) reste correcte
        # sans le validateur DRF automatique, qui exigerait sinon `user` sur chaque requête.
        validators = []


class EventExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventExpense
        fields = ["id", "event", "label", "category", "amount", "date", "created_at"]
        read_only_fields = ["id", "created_at"]


class EventSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source="organizer.get_full_name", read_only=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True, default=None)
    venue_address = serializers.CharField(source="venue.address", read_only=True, default=None)
    venue_city = serializers.CharField(source="venue.city", read_only=True, default=None)
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_budget = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)
    tasks_count = serializers.IntegerField(source="tasks.count", read_only=True)
    participants_count = serializers.IntegerField(source="participants.count", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id", "title", "description", "organizer", "organizer_name", "venue", "venue_name",
            "venue_address", "venue_city", "status",
            "start_date", "end_date", "budget_total", "is_public", "photo",
            "spent_amount", "remaining_budget", "progress_percent",
            "tasks_count", "participants_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organizer", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "La date de fin doit être postérieure à la date de début."})

        is_public = attrs.get("is_public", getattr(self.instance, "is_public", False))
        request = self.context.get("request")
        if is_public and request and not (request.user.is_admin_role or request.user.is_organizer_role):
            raise serializers.ValidationError({
                "is_public": "Seul un organisateur peut publier un événement public avec billetterie. "
                             "Un client crée uniquement des événements privés."
            })
        return attrs
