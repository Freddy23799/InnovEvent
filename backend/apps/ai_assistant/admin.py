from django.contrib import admin

from .models import AssistantConversation, AssistantMessage


class AssistantMessageInline(admin.TabularInline):
    model = AssistantMessage
    extra = 0
    readonly_fields = ["role", "content", "recommendations", "created_at"]


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "created_at"]
    inlines = [AssistantMessageInline]
