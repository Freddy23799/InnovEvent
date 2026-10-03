"""Garantit la présence d'un administrateur complet après les migrations."""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = (
        "Crée l'administrateur initial si aucun super-administrateur actif n'existe. "
        "Les identifiants sont lus uniquement depuis les variables INITIAL_ADMIN_*."
    )

    def handle(self, *args, **options):
        user_model = get_user_model()

        # Un compte doit être à la fois actif, staff et superuser : il peut ainsi
        # administrer toutes les ressources via l'API et l'administration Django.
        if user_model.objects.filter(
            is_active=True,
            is_staff=True,
            is_superuser=True,
        ).exists():
            self.stdout.write("Un super-administrateur actif existe déjà ; aucune création nécessaire.")
            return

        username = os.environ.get("INITIAL_ADMIN_USERNAME", "admin").strip()
        email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@innovevent.local").strip()
        password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
        first_name = os.environ.get("INITIAL_ADMIN_FIRST_NAME", "Administrateur").strip()
        last_name = os.environ.get("INITIAL_ADMIN_LAST_NAME", "InnovEvent").strip()

        if not username:
            raise CommandError("INITIAL_ADMIN_USERNAME ne peut pas être vide.")
        if not email:
            raise CommandError("INITIAL_ADMIN_EMAIL ne peut pas être vide.")
        if not password:
            raise CommandError(
                "Aucun super-administrateur actif n'existe et INITIAL_ADMIN_PASSWORD n'est pas défini. "
                "Définissez-le avant de démarrer le backend."
            )

        candidate = user_model(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        try:
            validate_password(password, user=candidate)
        except Exception as exc:
            raise CommandError(f"INITIAL_ADMIN_PASSWORD ne respecte pas la politique de mot de passe : {exc}") from exc

        try:
            with transaction.atomic():
                # get_or_create rend la commande idempotente et empêche qu'un
                # redémarrage normal ne remplace les identifiants configurés.
                user, created = user_model.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "role": user_model.Role.ADMIN,
                        "is_active": True,
                        "is_staff": True,
                        "is_superuser": True,
                        "is_verified": True,
                    },
                )
                if not created:
                    raise CommandError(
                        f"Le nom d'utilisateur INITIAL_ADMIN_USERNAME={username!r} existe déjà, "
                        "mais aucun super-administrateur actif n'a été trouvé. "
                        "Choisissez un autre INITIAL_ADMIN_USERNAME ou corrigez le compte existant."
                    )

                user.set_password(password)
                user.save(update_fields=["password", "updated_at"])
        except IntegrityError as exc:
            raise CommandError(
                "Impossible de créer l'administrateur initial (conflit concurrent ou contrainte de base de données)."
            ) from exc

        self.stdout.write(self.style.SUCCESS(f"Administrateur initial créé : {username}"))
