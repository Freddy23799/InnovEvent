from django.contrib import admin

from .models import Ticket, TicketType


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "event", "price", "currency", "quota", "sold_count", "is_active"]
    list_filter = ["is_active", "currency"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["code", "ticket_type", "owner", "status", "purchased_at", "checked_in_at"]
    list_filter = ["status"]
    search_fields = ["code", "owner__username"]
    readonly_fields = ["code"]
