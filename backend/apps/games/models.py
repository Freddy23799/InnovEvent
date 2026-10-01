from django.conf import settings
from django.db import models


class Quiz(models.Model):
    """Jeu-questionnaire proposé aux participants : soit sur l'entreprise
    (culture générale InnovEvent-GS), soit lié à un événement précis."""

    class Category(models.TextChoices):
        COMPANY = "company", "Quiz entreprise"
        EVENT = "event", "Jeu événementiel"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)
    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, null=True, blank=True, related_name="quizzes",
        help_text="Événement concerné, pour un jeu événementiel",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "title"]
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return self.title

    @property
    def question_count(self):
        return self.questions.count()


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=300)
    choices = models.JSONField(default=list, help_text="Liste des options de réponse, ex: [\"Oui\", \"Non\"]")
    correct_index = models.PositiveSmallIntegerField(help_text="Index (0-based) de la bonne réponse dans `choices`")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.quiz.title} — Q{self.order + 1}"


class QuizAttempt(models.Model):
    """Résultat d'une participation à un quiz (une tentative complète)."""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    answers = models.JSONField(default=dict, help_text="Réponses soumises : {question_id: chosen_index}")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.participant} — {self.quiz.title} ({self.score}/{self.total_questions})"

    @property
    def percent(self):
        if not self.total_questions:
            return 0
        return round(self.score / self.total_questions * 100)
