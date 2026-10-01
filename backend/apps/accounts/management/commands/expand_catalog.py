import os

from django.core.files import File
from django.core.management.base import BaseCommand

from apps.equipment.models import Equipment
from apps.providers.models import Provider
from apps.venues.models import Venue


class Command(BaseCommand):
    """Double le catalogue de démonstration (salles, prestataires, matériel) en
    créant de nouvelles fiches, chacune avec sa propre photo de couverture —
    plutôt que d'ajouter plusieurs photos à une même fiche. Idempotent."""

    help = "Ajoute de nouvelles salles/prestataires/matériel avec photo, depuis un dossier de photos déjà nettoyées."

    def add_arguments(self, parser):
        parser.add_argument("photos_dir", type=str)

    def handle(self, *args, **options):
        photos_dir = options["photos_dir"]

        venues = [
            ("Château des Lumières", "Douala", 220, 280000,
             "Verrière lumineuse au décor raffiné, idéale pour réceptions et mariages haut de gamme.",
             "nu.jpg"),
            ("Grand Théâtre Impérial", "Yaoundé", 600, 500000,
             "Grande salle de spectacle à l'italienne, parfaite pour concerts, galas et grandes conférences.",
             "it.jpg"),
            ("Studio Concert Live", "Douala", 300, 320000,
             "Salle de concert équipée d'une régie son professionnelle intégrée.",
             "depo.jpg"),
            ("Salle Étoile Pourpre", "Bafoussam", 250, 260000,
             "Ambiance feutrée et éclairage d'ambiance violet, idéale pour soirées et réceptions élégantes.",
             "3-scaled.jpg"),
            ("Salle Rose Élégance", "Yaoundé", 180, 230000,
             "Salle de réception habillée aux tons roses et blancs, décoration florale incluse.",
             "R.jpg"),
        ]

        providers = [
            (Provider.Category.DJ, "DJ Vibe Master", "80 000 - 200 000 XAF",
             "Animation musicale professionnelle pour mariages, concerts et soirées d'entreprise.",
             "0f498543f671771fd6eeb879d2c9109b.jpg"),
            (Provider.Category.DECORATION, "Déco Rose Événements", "100 000 - 400 000 XAF",
             "Décoration florale et scénographie sur mesure, thèmes romantiques et élégants.",
             "OIP_1.jpg"),
            (Provider.Category.CATERER, "Chef en Plein Air Traiteur", "3 000 - 7 000 XAF / personne",
             "Cuisine de rue haut de gamme et grillades préparées sur place devant vos invités.",
             "3be224aff2d37c31ac689f772bfa3ed7.jpg"),
        ]

        equipment = [
            (Equipment.Category.LIGHTING, "Projecteur de scène LED", 15, 12000,
             "Projecteur LED professionnel pour éclairage de scène et ambiance colorée.",
             "20007160_800.jpg"),
            (Equipment.Category.VIDEO, "Vidéoprojecteur HD", 6, 25000,
             "Vidéoprojecteur haute définition pour présentations et projections grand écran.",
             "71uwypoebzl-ac-sl1500-1711659511-1711660222.jpg"),
        ]

        for name, city, capacity, price, description, filename in venues:
            self._create(Venue, {"name": name}, dict(
                city=city, capacity=capacity, price_per_day=price, description=description, is_active=True,
            ), photos_dir, filename)

        for category, name, price_range, description, filename in providers:
            self._create(Provider, {"name": name}, dict(
                category=category, price_range=price_range, description=description, is_active=True,
            ), photos_dir, filename)

        for category, name, quantity_total, price_per_unit, description, filename in equipment:
            self._create(Equipment, {"name": name}, dict(
                category=category, quantity_total=quantity_total, price_per_unit=price_per_unit,
                description=description, is_active=True,
            ), photos_dir, filename)

    def _create(self, model, lookup, defaults, photos_dir, filename):
        obj, created = model.objects.get_or_create(defaults=defaults, **lookup)
        if not created:
            self.stdout.write(self.style.WARNING(f"Déjà existant : {model.__name__} « {lookup} »"))
            return
        path = os.path.join(photos_dir, filename)
        if os.path.exists(path):
            with open(path, "rb") as f:
                obj.photo.save(filename, File(f), save=True)
        self.stdout.write(self.style.SUCCESS(f"Créé : {model.__name__} « {obj.name} »"))
