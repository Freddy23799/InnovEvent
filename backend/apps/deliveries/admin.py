from django.contrib import admin

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


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ["name", "base_fee", "price_per_km", "price_per_kg", "is_active"]


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ["name", "carrier_type", "phone", "status", "is_active"]
    list_filter = ["carrier_type", "status"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "vehicle_type", "carrier", "status"]
    list_filter = ["vehicle_type", "status"]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "carrier", "status"]
    list_filter = ["status"]


class ParcelInline(admin.TabularInline):
    model = Parcel
    extra = 0


class DeliveryStatusHistoryInline(admin.TabularInline):
    model = DeliveryStatusHistory
    extra = 0
    readonly_fields = ["actor", "old_status", "new_status", "comment", "created_at"]


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ["reference", "tracking_code", "status", "carrier", "driver", "amount", "created_at"]
    list_filter = ["status", "delivery_type", "priority"]
    search_fields = ["reference", "tracking_code", "client_phone", "recipient_phone"]
    inlines = [ParcelInline, DeliveryStatusHistoryInline]


@admin.register(DeliveryProof)
class DeliveryProofAdmin(admin.ModelAdmin):
    list_display = ["delivery", "receiver_name", "confirmed_at"]


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ["label", "zone", "vehicle_type", "priority", "extra_fee", "multiplier_percent", "is_active"]
    list_filter = ["zone", "vehicle_type", "priority", "is_active"]


@admin.register(DeliveryReturn)
class DeliveryReturnAdmin(admin.ModelAdmin):
    list_display = ["delivery", "reason", "refund_status", "created_at"]
    list_filter = ["reason", "refund_status"]


@admin.register(DeliveryExpense)
class DeliveryExpenseAdmin(admin.ModelAdmin):
    list_display = ["category", "amount", "carrier", "vehicle", "delivery", "expense_date"]
    list_filter = ["category", "carrier"]
