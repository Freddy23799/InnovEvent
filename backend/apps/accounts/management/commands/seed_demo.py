from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.employees.models import Employee
from apps.equipment.models import Equipment
from apps.events.models import Event
from apps.providers.models import Provider
from apps.tickets.models import TicketType
from apps.training.models import Training
from apps.venues.models import Venue

User = get_user_model()


class Command(BaseCommand):
    """Génère des données de démonstration réalistes, sans données personnelles
    réelles (section 25 du CDC), ainsi que les comptes initiaux (section 26)."""

    help = "Crée des comptes et des données de démonstration InnovEvent-GS."

    def handle(self, *args, **options):
        admin = self._create_user("admin", "admin@innovevent.example", "Admin!InnovEvent2026", User.Role.ADMIN, "Aïcha", "Ngono")
        client = self._create_user("client_demo", "client@innovevent.example", "Client!InnovEvent2026", User.Role.CLIENT, "Paul", "Mballa")
        participant = self._create_user("participant_demo", "participant@innovevent.example", "Participant!2026", User.Role.PARTICIPANT, "Sarah", "Eyenga")
        employee_user = self._create_user("employe_demo", "employe@innovevent.example", "Employe!InnovEvent2026", User.Role.EMPLOYEE, "Junior", "Fotso")

        venue, _ = Venue.objects.get_or_create(
            name="Palais des Congrès de Yaoundé",
            defaults=dict(city="Yaoundé", capacity=800, price_per_day=450000, description="Grande salle modulable au centre-ville."),
        )
        Venue.objects.get_or_create(
            name="Villa Belvédère",
            defaults=dict(city="Douala", capacity=250, price_per_day=220000, description="Salle de réception élégante avec jardin privatif, idéale pour mariages et galas."),
        )
        Venue.objects.get_or_create(
            name="Salle Horizon Bleu",
            defaults=dict(
                city="Douala", capacity=350, price_per_day=280000,
                description="Grand espace élégant pour mariage, gala ou réception premium avec zone scène et piste de danse.",
            ),
        )
        Venue.objects.get_or_create(
            name="Salle Jardin Prestige",
            defaults=dict(
                city="Yaoundé", capacity=180, price_per_day=160000,
                description="Salle chaleureuse pour anniversaires, dîners privés et événements professionnels de taille moyenne.",
            ),
        )
        Venue.objects.get_or_create(
            name="Salle Signature Event",
            defaults=dict(
                city="Bafoussam", capacity=500, price_per_day=350000,
                description="Configuration grande capacité avec fond de scène, accès logistique et zone VIP pour réceptions.",
            ),
        )
        provider, _ = Provider.objects.get_or_create(
            name="DJ Kalash Prod", category=Provider.Category.DJ,
            defaults=dict(contact_email="djkalash@example.com", contact_phone="+237600000000", price_range="80 000 - 200 000 XAF"),
        )
        Provider.objects.get_or_create(
            name="Traiteur Saveurs d'Afrique", category=Provider.Category.CATERER,
            defaults=dict(contact_email="traiteur@example.com", price_range="2 500 - 6 000 XAF / personne"),
        )
        Provider.objects.get_or_create(
            name="Élégance Déco Events", category=Provider.Category.DECORATION,
            defaults=dict(contact_email="elegance.deco@example.com", contact_phone="+237601000000", price_range="150 000 - 500 000 XAF"),
        )
        Equipment.objects.get_or_create(
            name="Système de sonorisation 2000W", category=Equipment.Category.SOUND,
            defaults=dict(quantity_total=5, price_per_unit=75000),
        )
        Equipment.objects.get_or_create(
            name="Écrans et régie audiovisuelle", category=Equipment.Category.VIDEO,
            defaults=dict(quantity_total=3, price_per_unit=120000, description="Écrans LED, vidéoprojecteurs et régie de visioconférence pour conférences et séminaires."),
        )

        event, _ = Event.objects.get_or_create(
            title="Gala annuel InnovEvent",
            organizer=client,
            defaults=dict(
                description="Soirée de gala avec remise de prix et animation musicale.",
                venue=venue,
                status=Event.Status.PUBLISHED,
                start_date=timezone.now() + timedelta(days=21),
                end_date=timezone.now() + timedelta(days=21, hours=5),
                budget_total=3000000,
                is_public=True,
            ),
        )

        TicketType.objects.get_or_create(
            event=event, name="Standard",
            defaults=dict(price=15000, currency="XAF", quota=200,
                          sale_start=timezone.now(), sale_end=timezone.now() + timedelta(days=20)),
        )
        TicketType.objects.get_or_create(
            event=event, name="VIP",
            defaults=dict(price=45000, currency="XAF", quota=50,
                          sale_start=timezone.now(), sale_end=timezone.now() + timedelta(days=20)),
        )

        Employee.objects.get_or_create(
            user=employee_user,
            defaults=dict(first_name="Junior", last_name="Fotso", position="Agent de contrôle d'accès", hire_date=timezone.now().date()),
        )

        Training.objects.get_or_create(
            name="Régie événementielle niveau 1", specialty="Régie technique", level="Débutant",
            session_label="Session janvier 2026",
            defaults=dict(fee_amount=150000, start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=30)),
        )

        self.stdout.write(self.style.SUCCESS("Données de démonstration créées avec succès."))
        self.stdout.write("Comptes initiaux (à changer immédiatement en production) :")
        for username, password, role in [
            ("admin", "Admin!InnovEvent2026", "Administrateur"),
            ("client_demo", "Client!InnovEvent2026", "Client"),
            ("participant_demo", "Participant!2026", "Participant"),
            ("employe_demo", "Employe!InnovEvent2026", "Employé"),
        ]:
            self.stdout.write(f"  - {username} / {password} ({role})")

    def _create_user(self, username, email, password, role, first_name, last_name):
        user, created = User.objects.get_or_create(
            username=username,
            defaults=dict(email=email, role=role, first_name=first_name, last_name=last_name, is_verified=True),
        )
        if created:
            user.set_password(password)
            if role == User.Role.ADMIN:
                user.is_staff = True
                user.is_superuser = True
            user.save()
        return user
