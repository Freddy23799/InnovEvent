from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class VenueReview(models.Model):
    """Avis client sur une salle, avec note en étoiles (par demi-étoile) et
    commentaire, affichés sur la fiche de consultation de la salle."""

    venue = models.ForeignKey("venues.Venue", on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="venue_reviews")
    rating = models.DecimalField(
        max_digits=2, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.5")), MaxValueValidator(Decimal("5.0"))],
        help_text="Note de 0.5 à 5, par pas de 0.5 étoile",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["venue", "author"], name="unique_review_per_client_per_venue"),
        ]

    def __str__(self):
        return f"{self.author} — {self.venue} ({self.rating}★)"


class ProviderReview(models.Model):
    """Avis client sur un prestataire (DJ, traiteur, décoration…)."""

    provider = models.ForeignKey("providers.Provider", on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_reviews")
    rating = models.DecimalField(
        max_digits=2, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.5")), MaxValueValidator(Decimal("5.0"))],
        help_text="Note de 0.5 à 5, par pas de 0.5 étoile",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "author"], name="unique_review_per_client_per_provider"),
        ]

    def __str__(self):
        return f"{self.author} — {self.provider} ({self.rating}★)"


class EquipmentReview(models.Model):
    """Avis client sur un matériel du catalogue."""

    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="equipment_reviews")
    rating = models.DecimalField(
        max_digits=2, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.5")), MaxValueValidator(Decimal("5.0"))],
        help_text="Note de 0.5 à 5, par pas de 0.5 étoile",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["equipment", "author"], name="unique_review_per_client_per_equipment"),
        ]

    def __str__(self):
        return f"{self.author} — {self.equipment} ({self.rating}★)"


class ProfessionalReview(models.Model):
    """Avis client sur un profil professionnel (marketplace décoration/design
    intérieur ou marketplace des acteurs) — seul un client abonné au
    marketplace de ce profil peut en laisser un (contrôlé côté serializer)."""

    profile = models.ForeignKey("marketplace.ProfessionalProfile", on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="professional_reviews")
    rating = models.DecimalField(
        max_digits=2, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.5")), MaxValueValidator(Decimal("5.0"))],
        help_text="Note de 0.5 à 5, par pas de 0.5 étoile",
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "author"], name="unique_review_per_client_per_profile"),
        ]

    def __str__(self):
        return f"{self.author} — {self.profile} ({self.rating}★)"
