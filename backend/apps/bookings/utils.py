from django.utils import timezone


def upcoming_unavailability(resource, limit=5):
    """Retourne les prochains créneaux où une ressource (salle, prestataire,
    matériel) est déjà réservée, afin d'informer le client sur les périodes
    d'indisponibilité à venir (au-delà du simple statut « maintenant »)."""
    from .models import Booking

    now = timezone.now()
    bookings = (
        resource.bookings.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
            end_datetime__gte=now,
        )
        .order_by("start_datetime")[:limit]
    )
    return [{"start": b.start_datetime, "end": b.end_datetime} for b in bookings]
