import math

from django.conf import settings
from django.db import models


class Booking(models.Model):
    """Réservation d'une salle, d'un prestataire ou de matériel pour un événement,
    avec vérification automatique des conflits (section 8 du CDC)."""

    class ResourceType(models.TextChoices):
        VENUE = "venue", "Salle"
        PROVIDER = "provider", "Prestataire"
        EQUIPMENT = "equipment", "Matériel"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmée"
        CANCELLED = "cancelled", "Annulée"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="bookings")
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    venue = models.ForeignKey("venues.Venue", on_delete=models.CASCADE, null=True, blank=True, related_name="bookings")
    provider = models.ForeignKey("providers.Provider", on_delete=models.CASCADE, null=True, blank=True, related_name="bookings")
    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.CASCADE, null=True, blank=True, related_name="bookings")
    quantity = models.PositiveIntegerField(default=1, help_text="Utilisé uniquement pour le matériel")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    payment = models.ForeignKey(
        "payments.Payment", on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="bookings_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_datetime"]
        indexes = [models.Index(fields=["start_datetime", "end_datetime"])]

    def __str__(self):
        return f"Réservation #{self.pk} — {self.event.title}"

    @property
    def resource(self):
        return getattr(self, self.resource_type)

    @property
    def duration_days(self):
        seconds = (self.end_datetime - self.start_datetime).total_seconds()
        return max(1, math.ceil(seconds / 86400))

    @property
    def estimated_cost(self):
        """Coût estimé, calculable uniquement pour les ressources à tarification
        numérique (salle, matériel) ; None pour les prestataires (tarif sur devis).
        Applique automatiquement l'offre promotionnelle en cours sur la ressource,
        le cas échéant."""
        if self.resource_type == self.ResourceType.VENUE and self.venue_id:
            return self.venue.discounted_price_per_day() * self.duration_days
        if self.resource_type == self.ResourceType.EQUIPMENT and self.equipment_id:
            return self.equipment.discounted_price_per_unit() * self.quantity * self.duration_days
        return None
