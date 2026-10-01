from django.conf import settings
from django.db import models


class Event(models.Model):
    """Événement organisé par un client, ou directement par l'administration (section 7)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publié"
        ONGOING = "ongoing", "En cours"
        COMPLETED = "completed", "Terminé"
        CANCELLED = "cancelled", "Annulé"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organized_events"
    )
    venue = models.ForeignKey(
        "venues.Venue", on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    budget_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_public = models.BooleanField(default=False, help_text="Visible sur le marché public de billetterie")
    photo = models.ImageField(upload_to="events/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["start_date"])]

    def __str__(self):
        return self.title

    @property
    def spent_amount(self):
        return self.expenses.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def remaining_budget(self):
        return self.budget_total - self.spent_amount

    @property
    def progress_percent(self):
        total_tasks = self.tasks.count()
        if not total_tasks:
            return 0
        done_tasks = self.tasks.filter(status=EventTask.Status.DONE).count()
        return round((done_tasks / total_tasks) * 100)


class EventTask(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "À faire"
        IN_PROGRESS = "in_progress", "En cours"
        DONE = "done", "Terminée"
        LATE = "late", "En retard"

    class Priority(models.TextChoices):
        LOW = "low", "Basse"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Haute"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.title} ({self.event.title})"


class EventParticipant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="event_participations"
    )
    full_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("event", "user")]

    def __str__(self):
        return self.full_name or (self.user.get_full_name() if self.user else self.email)


class EventExpense(models.Model):
    class Category(models.TextChoices):
        VENUE = "venue", "Salle"
        PROVIDER = "provider", "Prestataire"
        EQUIPMENT = "equipment", "Matériel"
        OTHER = "other", "Autre"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="expenses")
    label = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.label} — {self.amount}"
