import uuid

from django.conf import settings
from django.db import models


def generate_transaction_ref():
    return str(uuid.uuid4())


class Payment(models.Model):
    """Transaction de paiement, indépendante de son usage (billetterie aujourd'hui,
    formations/RH demain) — section 10 du CDC."""

    class Provider(models.TextChoices):
        MTN_MOMO = "mtn_momo", "MTN Mobile Money"
        ORANGE_MONEY = "orange_money", "Orange Money"
        CARD = "card", "Carte bancaire (Visa / Mastercard)"
        PAYPAL = "paypal", "PayPal"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        FREEMOPAY = "freemopay", "FreemoPay"
        KOB = "kob", "KOB"
        DEMO = "demo", "Mode démonstration"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        COMPLETED = "completed", "Complété"
        FAILED = "failed", "Échoué"
        REFUNDED = "refunded", "Remboursé"

    class Currency(models.TextChoices):
        XAF = "XAF", "Franc CFA"
        EUR = "EUR", "Euro"
        USD = "USD", "Dollar US"
        GBP = "GBP", "Livre sterling"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.XAF)
    provider = models.CharField(max_length=20, choices=Provider.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_ref = models.CharField(max_length=64, unique=True, default=generate_transaction_ref, editable=False)
    provider_reference = models.CharField(max_length=200, blank=True, help_text="Référence renvoyée par la passerelle")
    purpose = models.CharField(max_length=50, default="ticket_purchase", help_text="ticket_purchase, training_fee, ...")
    raw_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["transaction_ref"])]

    def __str__(self):
        return f"{self.transaction_ref} — {self.amount} {self.currency} ({self.get_status_display()})"
