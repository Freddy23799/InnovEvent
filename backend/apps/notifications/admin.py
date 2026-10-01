from django.contrib import admin

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["recipient_email", "subject", "template_name", "status", "sent_at"]
    list_filter = ["status", "template_name"]
    search_fields = ["recipient_email", "subject"]

    def has_add_permission(self, request):
        return False
