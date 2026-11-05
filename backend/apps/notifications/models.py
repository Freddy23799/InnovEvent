from django.conf import settings
from django.db import models


class EmailLog(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Envoyé"
        FAILED = "failed", "Échec"

    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=Status.choices)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.template_name} -> {self.recipient_email} ({self.status})"


class SmsLog(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Envoyé"
        FAILED = "failed", "Échec"

    recipient_phone = models.CharField(max_length=30)
    message = models.CharField(max_length=320)
    status = models.CharField(max_length=10, choices=Status.choices)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"SMS -> {self.recipient_phone} ({self.status})"


class Notification(models.Model):
    """Notification in-app (« push ») affichée dans la cloche du tableau de bord."""

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=200, blank=True, help_text="Route frontend associée, ex: /bookings")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"


class PushSubscription(models.Model):
    """Abonnement Web Push d'un navigateur ou d'une PWA (un par appareil) :
    permet de notifier l'utilisateur même application fermée."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Push {self.user} ({self.endpoint[:40]}…)"
