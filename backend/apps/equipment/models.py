from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone


class Equipment(models.Model):
    class Category(models.TextChoices):
        SOUND = "sound", "Sonorisation"
        LIGHTING = "lighting", "Éclairage"
        FURNITURE = "furniture", "Mobilier"
        VIDEO = "video", "Vidéo"
        OTHER = "other", "Autre"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    quantity_total = models.PositiveIntegerField(default=1)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="equipment/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(90)])
    discount_label = models.CharField(max_length=100, blank=True, help_text="Ex: Offre de rentrée")
    discount_valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name

    def is_currently_available(self):
        now = timezone.now()
        return self.available_quantity(now, now) > 0

    def available_quantity(self, start, end, exclude_booking_id=None):
        """Quantité disponible sur une plage horaire donnée, en tenant compte des
        réservations déjà confirmées/en attente qui se chevauchent (section 8)."""
        from apps.bookings.models import Booking

        overlapping = Booking.objects.filter(
            equipment=self,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_datetime__lt=end,
            end_datetime__gt=start,
        )
        if exclude_booking_id:
            overlapping = overlapping.exclude(pk=exclude_booking_id)
        reserved = overlapping.aggregate(total=models.Sum("quantity"))["total"] or 0
        return self.quantity_total - reserved

    def has_active_discount(self):
        if self.discount_percent <= 0:
            return False
        if self.discount_valid_until and self.discount_valid_until < timezone.now().date():
            return False
        return True

    def discounted_price_per_unit(self):
        if not self.has_active_discount():
            return self.price_per_unit
        factor = Decimal(100 - self.discount_percent) / Decimal(100)
        return (self.price_per_unit * factor).quantize(Decimal("0.01"))

    def average_rating(self):
        from django.db.models import Avg

        return self.reviews.aggregate(avg=Avg("rating"))["avg"]

    def review_count(self):
        return self.reviews.count()


class StockMovement(models.Model):
    """Mouvement de stock (entrée/sortie) sur un matériel : réapprovisionnement,
    utilisation, perte, casse, retour… Chaque mouvement met automatiquement à
    jour la quantité totale en stock, en conservant un historique complet et
    compréhensible de bout en bout (section « gestion de stock »)."""

    class MovementType(models.TextChoices):
        IN = "in", "Entrée (réapprovisionnement)"
        OUT = "out", "Sortie"

    class Reason(models.TextChoices):
        RESTOCK = "restock", "Réapprovisionnement / achat"
        EVENT_USE = "event_use", "Utilisation pour un événement"
        DAMAGE = "damage", "Endommagé"
        LOSS = "loss", "Perdu / volé"
        RETURN = "return", "Retour en stock"
        DISPOSAL = "disposal", "Mise au rebut"
        OTHER = "other", "Autre"

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="stock_movements")
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.OTHER)
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_movement_type_display()} — {self.equipment.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            delta = self.quantity if self.movement_type == self.MovementType.IN else -self.quantity
            Equipment.objects.filter(pk=self.equipment_id).update(quantity_total=models.F("quantity_total") + delta)
            # Le FK en cache garde l'ancienne quantité après un .update() en base :
            # on le rafraîchit pour que la sérialisation immédiate (ex: resulting_quantity) soit correcte.
            self.equipment.refresh_from_db(fields=["quantity_total"])


class Expense(models.Model):
    """Dépense liée à la gestion du matériel (achat, réparation, logistique…),
    pour un suivi financier complet du stock, distinct du budget par événement."""

    class Category(models.TextChoices):
        PURCHASE = "purchase", "Achat de matériel"
        MAINTENANCE = "maintenance", "Maintenance / réparation"
        LOGISTICS = "logistics", "Logistique / transport"
        UTILITIES = "utilities", "Charges (eau, électricité, internet)"
        OTHER = "other", "Autre"

    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    label = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses",
        help_text="Matériel concerné, le cas échéant",
    )
    stock_movement = models.ForeignKey(
        StockMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses",
    )
    notes = models.TextField(blank=True)
    incurred_at = models.DateField(default=timezone.now)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-incurred_at", "-created_at"]

    def __str__(self):
        return f"{self.label} — {self.amount}"
