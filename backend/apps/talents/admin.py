from django.contrib import admin

from .models import TalentPortfolioItem, TalentProfile


class TalentPortfolioItemInline(admin.TabularInline):
    model = TalentPortfolioItem
    extra = 0


@admin.register(TalentProfile)
class TalentProfileAdmin(admin.ModelAdmin):
    list_display = ["full_name", "city", "opportunity_type", "verification_status", "is_active", "created_at"]
    list_filter = ["verification_status", "opportunity_type", "is_active"]
    search_fields = ["full_name", "competences", "city"]
    inlines = [TalentPortfolioItemInline]
