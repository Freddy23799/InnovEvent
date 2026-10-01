from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["transaction_ref", "user", "amount", "currency", "provider", "status", "created_at"]
    list_filter = ["provider", "status", "currency"]
    search_fields = ["transaction_ref", "user__username"]
    readonly_fields = ["transaction_ref", "raw_response", "created_at", "completed_at"]
