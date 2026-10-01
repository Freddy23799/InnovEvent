import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TicketType(models.Model):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="XAF")
    quota = models.PositiveIntegerField()
    sale_start = models.DateTimeField()
    sale_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(
        default=False, help_text="Génère un billet PDF avec un visuel premium (billets VIP / prestige)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} — {self.event.title}"

    @property
    def sold_count(self):
        return self.tickets.exclude(status=Ticket.Status.CANCELLED).count()

    @property
    def remaining_quota(self):
        return self.quota - self.sold_count

    def is_on_sale(self):
        now = timezone.now()
        return self.is_active and self.sale_start <= now <= self.sale_end and self.remaining_quota > 0


class Ticket(models.Model):
    class Status(models.TextChoices):
        VALID = "valid", "Valide"
        USED = "used", "Utilisé"
        CANCELLED = "cancelled", "Annulé"

    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="tickets")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets")
    payment = models.ForeignKey("payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)
    buyer_first_name = models.CharField(max_length=150, blank=True)
    buyer_last_name = models.CharField(max_length=150, blank=True)
    buyer_email = models.EmailField(blank=True)
    buyer_phone = models.CharField(max_length=30, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-purchased_at"]
        indexes = [models.Index(fields=["code"])]

    def __str__(self):
        return f"Billet {self.code} ({self.get_status_display()})"
