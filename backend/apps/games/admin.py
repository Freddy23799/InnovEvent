from django.contrib import admin

from .models import Quiz, QuizAttempt, QuizQuestion


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "event", "is_active", "question_count"]
    list_filter = ["category", "is_active"]
    search_fields = ["title"]
    inlines = [QuizQuestionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ["quiz", "participant", "score", "total_questions", "completed_at"]
    list_filter = ["quiz"]
    search_fields = ["participant__username"]
