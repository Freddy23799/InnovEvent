import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.marketplace.reminders import run_all_reminders


class Command(BaseCommand):
    help = "Envoie les relances de l'assistant (panier abandonné, facture, devis, abonnement)."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Tourne en continu (service planifié).")
        parser.add_argument("--interval", type=int, default=600, help="Secondes entre deux passages (avec --loop).")
        parser.add_argument("--initial-delay", type=int, default=60, help="Attente avant le premier passage (avec --loop), le temps que les migrations s'appliquent.")

    def handle(self, *args, loop=False, interval=600, initial_delay=60, **options):
        if loop:
            time.sleep(initial_delay)
        while True:
            close_old_connections()
            try:
                counts = run_all_reminders()
                if any(counts.values()) or not loop:
                    self.stdout.write(f"Relances envoyées : {counts}")
            except Exception as exc:  # un passage raté ne doit pas arrêter le service
                self.stderr.write(f"Relances : erreur {exc!r}")
                if not loop:
                    raise
            if not loop:
                return
            time.sleep(interval)
