import os

from django.core.files import File
from django.core.management.base import BaseCommand

from apps.events.models import Event
from apps.training.models import Training
from apps.venues.models import Venue


class Command(BaseCommand):
    """Associe des photos aux salles/événements/formations qui n'en ont pas
    encore, depuis un dossier de photos déjà nettoyées (filigrane retiré)."""

    help = "Associe les photos manquantes (salles, événements, formations)."

    def add_arguments(self, parser):
        parser.add_argument("photos_dir", type=str)

    def handle(self, *args, **options):
        photos_dir = options["photos_dir"]

        mapping = [
            (Venue, "name", "Salle Horizon Bleu", "salle.jpg"),
            (Venue, "name", "Salle Jardin Prestige", "salle-de-mariage.jpg"),
            (Venue, "name", "Salle Signature Event", "4-scaled.jpg"),
            (Event, "title", "Nuit Afro Live — Boris B.", "Limportance-du-DJ-dans-un-evenement-sportif.jpg"),
            (Training, "name", "Décoration Événementielle", "Decoration-salle-mariage-tropical.jpg"),
            (Training, "name", "Design et Décoration d'Intérieur", "Decoration-salle-mariage-boheme.jpg"),
            (Training, "name", "Wedding Planner", "decoration-mariage-champetre-blanc-ivoire-salle.jpg"),
            (Training, "name", "Marketing Digital", "SV30_extron.jpg"),
            (Training, "name", "Régie événementielle niveau 1", "Staff-Eins-Personal_Event-800x700.jpg"),
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
