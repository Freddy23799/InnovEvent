from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Event
from apps.tickets.models import TicketType


class Command(BaseCommand):
    """Crée un compte organisateur de démonstration avec un événement public et
    sa billetterie, afin que le nouveau marché des événements ait du contenu à
    afficher dès le premier essai. Idempotent."""

    help = "Seed d'un compte organisateur + événement public + billets de démonstration."

    def handle(self, *args, **options):
        organizer, created = User.objects.get_or_create(
            username="organisateur_demo",
            defaults=dict(
                email="organisateur@innovevent.example",
                role=User.Role.ORGANIZER,
                first_name="Boris",
                last_name="Essomba",
                is_verified=True,
            ),
        )
        if created:
            organizer.set_password("Organisateur!2026")
            organizer.save()
        elif organizer.role != User.Role.ORGANIZER:
            organizer.role = User.Role.ORGANIZER
            organizer.save(update_fields=["role"])

        start = timezone.now() + timedelta(days=45)
        event, _ = Event.objects.get_or_create(
            title="Nuit Afro Live — Boris B.",
            organizer=organizer,
            defaults=dict(
                description="Concert live avec DJ set, ouvert au public. Billets en vente en ligne.",
                status=Event.Status.PUBLISHED,
                start_date=start,
                end_date=start + timedelta(hours=5),
                budget_total=2000000,
                is_public=True,
            ),
        )
        if not event.is_public or event.status != Event.Status.PUBLISHED:
            event.is_public = True
            event.status = Event.Status.PUBLISHED
            event.save(update_fields=["is_public", "status"])

        sale_start = timezone.now()
        sale_end = start - timedelta(hours=2)
        TicketType.objects.get_or_create(
            event=event, name="Standard",
            defaults=dict(price=5000, currency="XAF", quota=200, sale_start=sale_start, sale_end=sale_end, is_active=True),
        )
        TicketType.objects.get_or_create(
            event=event, name="VIP",
            defaults=dict(price=15000, currency="XAF", quota=50, sale_start=sale_start, sale_end=sale_end, is_active=True),
        )

        self.stdout.write(self.style.SUCCESS("Organisateur de démonstration prêt :"))
        self.stdout.write("  - organisateur_demo / Organisateur!2026 (Organisateur)")
        self.stdout.write(f"  - Événement public : « {event.title} » avec billets Standard/VIP")
