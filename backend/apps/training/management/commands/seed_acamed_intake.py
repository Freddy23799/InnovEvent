from datetime import date

from django.core.management.base import BaseCommand

from apps.training.models import Training, TrainingFormula

SCHEDULE_OPTIONS = [
    {"label": "Cours du jour", "hours": "10H - 13H"},
    {"label": "Cours du soir", "hours": "15H - 18H"},
]

PERKS = [
    "Wifi disponible",
    "Cadre propre",
    "Des enseignants expérimentés et professionnels",
    "Cours pratique sur le terrain",
    "Suivi des apprenants après la formation",
    "Matériel loué avec 50% de réduction pour vos prestations après la formation",
    "Polo offert pour tous les apprenants",
]

SESSION_LABEL = "Rentrée académique 2026"
START_DATE = date(2026, 10, 12)

# (nom de la filière, propose la formule accélérée 1 mois ?)
FILIERES = [
    ("Décoration Événementielle", True),
    ("Design et Décoration d'Intérieur", False),
    ("Marketing Digital", True),
    ("Wedding Planner", True),
]


class Command(BaseCommand):
    """Crée la rentrée académique 2026 telle qu'annoncée sur le support de
    communication de l'école : une filière par métier, chacune avec ses
    formules de durée/tarif et ses horaires (section formation du CDC).
    Idempotent : peut être relancée sans dupliquer les données."""

    help = "Seed des filières et formules de la rentrée académique 2026 (inspirées de l'affiche de communication)."

    def handle(self, *args, **options):
        for name, has_accelerated in FILIERES:
            training, created = Training.objects.get_or_create(
                name=name,
                session_label=SESSION_LABEL,
                defaults=dict(
                    specialty=name,
                    level="Débutant à intermédiaire",
                    description=f"Formation professionnalisante en {name.lower()}, avec suivi pratique sur le terrain.",
                    start_date=START_DATE,
                    schedule_options=SCHEDULE_OPTIONS,
                    perks=PERKS,
                    is_active=True,
                ),
            )
            if not created:
                training.schedule_options = SCHEDULE_OPTIONS
                training.perks = PERKS
                training.is_active = True
                training.save(update_fields=["schedule_options", "perks", "is_active"])

            if has_accelerated:
                TrainingFormula.objects.update_or_create(
                    training=training, duration_months=1,
                    defaults=dict(label="Formation accélérée", registration_fee=10000, tuition_fee=100000, is_active=True),
                )
            TrainingFormula.objects.update_or_create(
                training=training, duration_months=3,
                defaults=dict(label="Formation complète", registration_fee=10000, tuition_fee=200000, is_active=True),
            )

            self.stdout.write(self.style.SUCCESS(f"  - {name} ({'1 et 3 mois' if has_accelerated else '3 mois'})"))

        self.stdout.write(self.style.SUCCESS("Rentrée académique 2026 initialisée avec succès."))
