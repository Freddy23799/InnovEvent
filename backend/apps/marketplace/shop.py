"""Disponibilités de la boutique (achat et location).

Le stock « possédé » d'un produit est celui de l'article d'inventaire lié
(`Equipment.quantity_total`, tenu par la gestion de stock de l'administration),
ou à défaut `MarketplaceListing.stock` ; `None` = stock non suivi (illimité).

Une location immobilise des pièces sur une période (dates incluses) : la
disponibilité d'une période est le stock possédé moins le pic de pièces déjà
louées sur l'un de ses jours, moins les réservations de l'ancien catalogue
d'équipements (apps.bookings) qui la chevauchent.
"""

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from .models import SaleOrder, SaleOrderItem

ACTIVE_RENTAL_STATUSES = [SaleOrder.RentalStatus.RESERVED, SaleOrder.RentalStatus.OUT]


def owned_quantity(listing):
    if listing.equipment_id:
        return listing.equipment.quantity_total
    return listing.stock


def _rental_items(listing, start, end):
    return SaleOrderItem.objects.filter(
        listing=listing,
        order__order_type=SaleOrder.OrderType.RENTAL,
        order__rental_status__in=ACTIVE_RENTAL_STATUSES,
        order__rental_start__lte=end,
        order__rental_end__gte=start,
    ).exclude(order__status=SaleOrder.Status.CANCELLED).values_list("quantity", "order__rental_start", "order__rental_end")


def peak_rented_quantity(listing, start, end):
    """Plus grand nombre de pièces louées un même jour entre `start` et `end`."""
    rows = list(_rental_items(listing, start, end))
    if not rows:
        return 0
    # Le pic ne peut tomber qu'au premier jour d'une location (ou au début de la période).
    candidates = {max(start, row_start) for _qty, row_start, _row_end in rows}
    return max(
        sum(qty for qty, row_start, row_end in rows if row_start <= day <= row_end)
        for day in candidates
    )


def _equipment_booked(listing, start, end):
    if not listing.equipment_id:
        return 0
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
    equipment = listing.equipment
    return equipment.quantity_total - equipment.available_quantity(start_dt, end_dt)


def available_for_rent(listing, start, end):
    owned = owned_quantity(listing)
    if owned is None:
        return None
    return max(owned - peak_rented_quantity(listing, start, end) - _equipment_booked(listing, start, end), 0)


def available_for_sale(listing):
    """Pièces vendables : le stock possédé moins ce qui est loué ou réservé
    à la location à partir d'aujourd'hui."""
    owned = owned_quantity(listing)
    if owned is None:
        return None
    today = timezone.localdate()
    horizon = max(
        [today] + [row_end for _qty, _start, row_end in _rental_items(listing, today, date.max)]
    )
    return max(owned - peak_rented_quantity(listing, today, horizon), 0)
