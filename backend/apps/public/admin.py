from django.contrib import admin

from .models import LandingMedia


@admin.register(LandingMedia)
class LandingMediaAdmin(admin.ModelAdmin):
    list_display = ["label", "category", "scope", "tag", "tier", "order", "is_active", "created_at"]
    list_filter = ["category", "scope", "tag", "tier", "is_active"]
    search_fields = ["label", "caption"]
