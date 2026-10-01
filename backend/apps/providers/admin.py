from django.contrib import admin

from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "contact_phone", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name"]
