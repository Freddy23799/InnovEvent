from django.contrib import admin

from .models import Badge, Certificate, Enrollment, Settlement, Training, TrainingFormula


class SettlementInline(admin.TabularInline):
    model = Settlement
    extra = 0
    readonly_fields = ["paid_at"]


class TrainingFormulaInline(admin.TabularInline):
    model = TrainingFormula
    extra = 0


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ["name", "session_label", "level", "fee_amount", "is_active", "start_date", "end_date"]
    list_filter = ["is_active"]
    search_fields = ["name", "specialty"]
    inlines = [TrainingFormulaInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["matricule", "participant", "training", "formula", "schedule", "status", "amount_due"]
    list_filter = ["status", "schedule"]
    search_fields = ["matricule", "participant__username"]
    inlines = [SettlementInline]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "issued_at", "validated_by"]


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ["matricule", "user", "purpose", "valid_from", "valid_until", "is_active"]
    list_filter = ["purpose", "is_active"]
    search_fields = ["matricule", "user__username"]
