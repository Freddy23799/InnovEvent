import os

from django.core.files import File
from django.core.management.base import BaseCommand

from apps.equipment.models import Equipment
from apps.events.models import Event
from apps.providers.models import Provider
from apps.venues.models import Venue


class Command(BaseCommand):
    """Associe les photos de démonstration (déposées dans un dossier temporaire)
    aux salles, prestataires et matériel créés par `seed_demo`. Usage ponctuel,
    à exécuter après avoir copié les images dans le conteneur (voir docker cp)."""

    help = "Associe les photos de démonstration aux ressources existantes."

    def add_arguments(self, parser):
        parser.add_argument("photos_dir", type=str)

    def handle(self, *args, **options):
        photos_dir = options["photos_dir"]

        mapping = [
            (Venue, "name", "Palais des Congrès de Yaoundé", "venue_1.jpg"),
            (Venue, "name", "Villa Belvédère", "venue_2.jpg"),
            (Provider, "name", "DJ Kalash Prod", "provider_dj.jpg"),
            (Provider, "name", "Traiteur Saveurs d'Afrique", "provider_caterer.jpg"),
            (Provider, "name", "Élégance Déco Events", "provider_decoration.jpg"),
            (Equipment, "name", "Système de sonorisation 2000W", "equipment_1.jpg"),
            (Equipment, "name", "Écrans et régie audiovisuelle", "equipment_2.jpg"),
            (Event, "title", "Gala annuel InnovEvent", "event_gala.jpg"),
        ]

        for model, lookup_field, name, filename in mapping:
            path = os.path.join(photos_dir, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(f"Fichier introuvable : {path}"))
                continue
            obj = model.objects.filter(**{lookup_field: name}).first()
            if not obj:
                self.stdout.write(self.style.WARNING(f"Ressource introuvable : {model.__name__} « {name} »"))
                continue
            with open(path, "rb") as f:
                obj.photo.save(filename, File(f), save=True)
            self.stdout.write(self.style.SUCCESS(f"Photo associée : {model.__name__} « {name} »"))
