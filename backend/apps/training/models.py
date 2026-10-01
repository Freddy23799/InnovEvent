from django.conf import settings
from django.db import models
from django.utils import timezone


class Training(models.Model):
    name = models.CharField(max_length=200)
    specialty = models.CharField(max_length=150, blank=True)
    level = models.CharField(max_length=100, blank=True)
    session_label = models.CharField(max_length=100, blank=True, help_text="Ex: Rentrée académique 2026")
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="trainings/", blank=True, null=True)
    fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Tarif de repli utilisé si aucune formule (durée) n'est définie pour cette filière",
    )
    schedule_options = models.JSONField(
        default=list, blank=True,
        help_text="Ex: [{\"label\": \"Cours du jour\", \"hours\": \"10H - 13H\"}, {\"label\": \"Cours du soir\", \"hours\": \"15H - 18H\"}]",
    )
    perks = models.JSONField(default=list, blank=True, help_text="Avantages affichés sur le catalogue (wifi, matériel, suivi…)")
    is_active = models.BooleanField(default=True, help_text="Visible dans le catalogue des inscriptions")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} — {self.session_label}" if self.session_label else self.name


class TrainingFormula(models.Model):
    """Formule de formation (durée + tarification) proposée pour une filière,
    ex : « 1 mois — formation accélérée » ou « 3 mois — formation complète ».
    Une même filière peut proposer plusieurs formules à des tarifs différents."""

    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name="formulas")
    label = models.CharField(max_length=150, help_text="Ex: Formation accélérée")
    duration_months = models.PositiveSmallIntegerField()
    registration_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Frais d'inscription")
    tuition_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Frais de formation")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["duration_months"]

    def __str__(self):
        return f"{self.training.name} — {self.label} ({self.duration_months} mois)"

    @property
    def total_fee(self):
        return self.registration_fee + self.tuition_fee


class Enrollment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente de validation"
        VALIDATED = "validated", "Validé"
        REJECTED = "rejected", "Rejeté"

    class Schedule(models.TextChoices):
        DAY = "day", "Cours du jour"
        EVENING = "evening", "Cours du soir"

    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name="enrollments")
    formula = models.ForeignKey(
        TrainingFormula, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments",
        help_text="Formule (durée/tarif) choisie ; si absente, le tarif de repli de la filière s'applique",
    )
    schedule = models.CharField(max_length=20, choices=Schedule.choices, blank=True)
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    matricule = models.CharField(max_length=30, unique=True, editable=False)
    photo = models.ImageField(upload_to="enrollments/", blank=True, null=True, help_text="Photo prise à l'enrôlement, reprise sur le badge")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="validated_enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enrolled_at"]
        unique_together = [("training", "participant")]

    def __str__(self):
        return f"{self.matricule} — {self.participant}"

    def save(self, *args, **kwargs):
        if not self.matricule:
            self.matricule = self._generate_matricule()
        if not self.amount_due:
            self.amount_due = self.formula.total_fee if self.formula_id else self.training.fee_amount
        super().save(*args, **kwargs)

    def _generate_matricule(self):
        year = timezone.now().year
        last = Enrollment.objects.filter(matricule__startswith=f"IE-{year}-").order_by("-id").first()
        sequence = int(last.matricule.split("-")[-1]) + 1 if last else 1
        return f"IE-{year}-{sequence:06d}"

    @property
    def amount_paid(self):
        return self.settlements.aggregate(total=models.Sum("amount"))["total"] or 0

    @property
    def balance(self):
        return self.amount_due - self.amount_paid


class Settlement(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="settlements")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50, blank=True)
    payment = models.ForeignKey(
        "payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="training_settlements"
    )
    paid_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.enrollment.matricule} — {self.amount}"


class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="certificate")
    issued_at = models.DateTimeField(auto_now_add=True)
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    def __str__(self):
        return f"Attestation — {self.enrollment.matricule}"


class Badge(models.Model):
    class Purpose(models.TextChoices):
        TRAINING = "training", "Formation"
        EMPLOYMENT = "employment", "Employé"
        EVENT = "event", "Événement"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    matricule = models.CharField(max_length=30)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    valid_from = models.DateField()
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Badge {self.matricule} ({self.get_purpose_display()})"

    def is_currently_valid(self):
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_until
