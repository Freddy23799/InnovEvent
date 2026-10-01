from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class InnovEventUserAdmin(UserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "role", "is_verified", "is_active"]
    list_filter = ["role", "is_active", "is_verified"]
    fieldsets = UserAdmin.fieldsets + (
        ("InnovEvent", {"fields": ("role", "phone", "avatar", "is_verified")}),
    )
