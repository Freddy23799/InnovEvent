from decimal import Decimal

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone


class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    price_per_day = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amenities = models.JSONField(default=list, blank=True, help_text="Liste des équipements inclus")
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="venues/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(90)])
    discount_label = models.CharField(max_length=100, blank=True, help_text="Ex: Offre de rentrée")
    discount_valid_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def is_currently_available(self):
        from apps.bookings.models import Booking

        now = timezone.now()
        return not self.bookings.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            start_datetime__lte=now,
            end_datetime__gte=now,
        ).exists()

    def average_rating(self):
        from django.db.models import Avg

        return self.reviews.aggregate(avg=Avg("rating"))["avg"]

    def review_count(self):
        return self.reviews.count()

    def has_active_discount(self):
        if self.discount_percent <= 0:
            return False
        if self.discount_valid_until and self.discount_valid_until < timezone.now().date():
            return False
        return True

    def discounted_price_per_day(self):
        if not self.has_active_discount():
            return self.price_per_day
        factor = Decimal(100 - self.discount_percent) / Decimal(100)
        return (self.price_per_day * factor).quantize(Decimal("0.01"))
