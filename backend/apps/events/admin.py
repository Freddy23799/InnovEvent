from django.contrib import admin

from .models import Event, EventExpense, EventParticipant, EventTask


class EventTaskInline(admin.TabularInline):
    model = EventTask
    extra = 0


class EventExpenseInline(admin.TabularInline):
    model = EventExpense
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "organizer", "status", "start_date", "end_date", "budget_total", "is_public"]
    list_filter = ["status", "is_public"]
    search_fields = ["title", "organizer__username"]
    inlines = [EventTaskInline, EventExpenseInline]


@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ["event", "full_name", "email", "checked_in"]
    list_filter = ["checked_in"]
