from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["id", "event", "resource_type", "start_datetime", "end_datetime", "status"]
    list_filter = ["resource_type", "status"]
