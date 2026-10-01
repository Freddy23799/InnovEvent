from django.contrib import admin

from .models import Venue


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "capacity", "price_per_day", "is_active"]
    list_filter = ["is_active", "city"]
    search_fields = ["name", "city"]
