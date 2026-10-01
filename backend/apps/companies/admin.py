from django.contrib import admin

from .models import CompanyDocument, CompanyProfile


class CompanyDocumentInline(admin.TabularInline):
    model = CompanyDocument
    extra = 0


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ["raison_sociale", "representant", "verification_status", "is_active", "created_at"]
    list_filter = ["verification_status", "is_active"]
    search_fields = ["raison_sociale", "rccm", "niu", "representant"]
    inlines = [CompanyDocumentInline]
