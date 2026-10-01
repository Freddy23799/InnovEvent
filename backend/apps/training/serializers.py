from decimal import Decimal

from rest_framework import serializers

from .models import Badge, Certificate, Enrollment, Settlement, Training, TrainingFormula


class TrainingFormulaSerializer(serializers.ModelSerializer):
    total_fee = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = TrainingFormula
        fields = [
            "id", "training", "label", "duration_months",
            "registration_fee", "tuition_fee", "total_fee", "is_active",
        ]
        read_only_fields = ["id"]


class TrainingSerializer(serializers.ModelSerializer):
    enrolled_count = serializers.IntegerField(source="enrollments.count", read_only=True)
    formulas = TrainingFormulaSerializer(many=True, read_only=True)

    class Meta:
        model = Training
        fields = [
            "id", "name", "specialty", "level", "session_label", "description", "photo",
            "fee_amount", "schedule_options", "perks", "is_active",
            "start_date", "end_date", "formulas", "enrolled_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "enrollment", "amount", "method", "payment", "paid_at", "recorded_by"]
        read_only_fields = ["id", "payment", "paid_at", "recorded_by"]


class EnrollmentSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source="participant.get_full_name", read_only=True)
    training_name = serializers.CharField(source="training.name", read_only=True)
    formula_label = serializers.CharField(source="formula.label", read_only=True, default=None)
    schedule_display = serializers.CharField(source="get_schedule_display", read_only=True, default="")
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    settlements = SettlementSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "training", "training_name", "formula", "formula_label", "schedule", "schedule_display",
            "participant", "participant_name", "matricule", "photo",
            "status", "amount_due", "amount_paid", "balance", "settlements", "enrolled_at",
        ]
        read_only_fields = ["id", "matricule", "status", "amount_due", "enrolled_at"]

    def validate(self, attrs):
        formula = attrs.get("formula")
        training = attrs.get("training") or getattr(self.instance, "training", None)
        if formula and training and formula.training_id != training.id:
            raise serializers.ValidationError("La formule choisie n'appartient pas à cette filière.")
        return attrs


class EnrollmentPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1"))
    payment_provider = serializers.ChoiceField(choices=["demo", "paypal", "mobile_money", "freemopay", "kob"], default="demo")


class CertificateSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source="enrollment.participant.get_full_name", read_only=True)
    training_name = serializers.CharField(source="enrollment.training.name", read_only=True)

    class Meta:
        model = Certificate
        fields = ["id", "enrollment", "participant_name", "training_name", "issued_at", "validated_by"]
        read_only_fields = fields


class BadgeSerializer(serializers.ModelSerializer):
    holder_name = serializers.CharField(source="user.get_full_name", read_only=True)
    is_currently_valid = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = [
            "id", "user", "holder_name", "matricule", "purpose",
            "valid_from", "valid_until", "is_active", "is_currently_valid", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_is_currently_valid(self, obj):
        return obj.is_currently_valid()
