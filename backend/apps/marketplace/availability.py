"""Résolution des disponibilités d'un profil professionnel : un seul point
d'entrée qui combine les dates bloquées manuellement, les prestations déjà
confirmées et le délai minimum de réservation — pour ne jamais coder cette
vérification à la main à chaque nouvel endroit qui en a besoin."""

import calendar
from datetime import date as date_cls

from django.utils import timezone

from .models import ProfessionalBlockedDate, ProfessionalBookingRequest


class DayStatus:
    PAST = "past"
    TOO_SOON = "too_soon"
    BLOCKED = "blocked"
    FULL = "full"
    AVAILABLE = "available"


def get_availability_settings(profile):
    settings = getattr(profile, "availability_settings", None)
    if settings is None:
        from .models import ProfessionalAvailabilitySettings

        settings = ProfessionalAvailabilitySettings.objects.create(profile=profile)
    return settings


def resolve_day_status(profile, day, settings=None, blocked_dates=None, confirmed_counts=None):
    settings = settings or get_availability_settings(profile)
    today = timezone.localdate()

    if day < today:
        return DayStatus.PAST
    if (day - today).days < settings.min_notice_days:
        return DayStatus.TOO_SOON

    if blocked_dates is None:
        blocked_dates = set(ProfessionalBlockedDate.objects.filter(profile=profile, date=day).values_list("date", flat=True))
    if day in blocked_dates:
        return DayStatus.BLOCKED

    if confirmed_counts is None:
        count = ProfessionalBookingRequest.objects.filter(
            profile=profile, event_date=day, status=ProfessionalBookingRequest.Status.CONFIRMED,
        ).count()
    else:
        count = confirmed_counts.get(day, 0)
    if count >= settings.max_bookings_per_day:
        return DayStatus.FULL

    return DayStatus.AVAILABLE


def resolve_month_availability(profile, year, month):
    """Retourne {jour: statut} pour chaque jour du mois donné — une seule
    requête groupée par catégorie plutôt qu'une requête par jour."""

    settings = get_availability_settings(profile)
    days_in_month = calendar.monthrange(year, month)[1]
    first_day = date_cls(year, month, 1)
    last_day = date_cls(year, month, days_in_month)

    blocked_dates = set(
        ProfessionalBlockedDate.objects.filter(profile=profile, date__range=(first_day, last_day)).values_list("date", flat=True)
    )
    confirmed_qs = ProfessionalBookingRequest.objects.filter(
        profile=profile, event_date__range=(first_day, last_day), status=ProfessionalBookingRequest.Status.CONFIRMED,
    ).values_list("event_date", flat=True)
    confirmed_counts = {}
    for d in confirmed_qs:
        confirmed_counts[d] = confirmed_counts.get(d, 0) + 1

    result = {}
    for day_num in range(1, days_in_month + 1):
        day = date_cls(year, month, day_num)
        result[day.isoformat()] = resolve_day_status(profile, day, settings, blocked_dates, confirmed_counts)
    return result
