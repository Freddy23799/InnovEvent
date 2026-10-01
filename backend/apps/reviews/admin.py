from django.contrib import admin

from .models import EquipmentReview, ProviderReview, VenueReview


@admin.register(VenueReview)
class VenueReviewAdmin(admin.ModelAdmin):
    list_display = ["venue", "author", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["venue__name", "author__username"]


@admin.register(ProviderReview)
class ProviderReviewAdmin(admin.ModelAdmin):
    list_display = ["provider", "author", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["provider__name", "author__username"]


@admin.register(EquipmentReview)
class EquipmentReviewAdmin(admin.ModelAdmin):
    list_display = ["equipment", "author", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["equipment__name", "author__username"]
