from django.contrib import admin

from .models import Equipment, Expense, StockMovement


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "quantity_total", "price_per_unit", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["equipment", "movement_type", "reason", "quantity", "recorded_by", "created_at"]
    list_filter = ["movement_type", "reason"]
    search_fields = ["equipment__name"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["label", "category", "amount", "equipment", "incurred_at", "recorded_by"]
    list_filter = ["category"]
    search_fields = ["label"]
