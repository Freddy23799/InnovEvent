from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.documents.validators import validate_image_file


class User(AbstractUser):
    """Utilisateur unique pour les 4 rôles du CDC (section 4).

    Un seul modèle avec un champ `role` plutôt que 4 modèles séparés : simplifie
    l'authentification JWT (un seul point d'entrée) et les relations FK (Event.organizer,
    Ticket.owner, etc. pointent toutes vers `accounts.User`).
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        CLIENT = "client", "Client"
        ORGANIZER = "organizer", "Organisateur"
        PARTICIPANT = "participant", "Participant / Élève"
        EMPLOYEE = "employee", "Employé"
        PARTNER = "partner", "Prestataire"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PARTICIPANT)
    phone = models.CharField(max_length=30, blank=True)
    city = models.CharField(max_length=100, blank=True, help_text="Ville — renseignée à l'inscription.")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, validators=[validate_image_file])
    is_verified = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    premium_until = models.DateTimeField(
        null=True, blank=True, help_text="Abonnement Premium Marketplace actif jusqu'à cette date."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def is_online(self):
        if not self.last_seen:
            return False
        from django.utils import timezone

        return (timezone.now() - self.last_seen).total_seconds() < 300

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_client_role(self):
        return self.role == self.Role.CLIENT

    @property
    def is_organizer_role(self):
        return self.role == self.Role.ORGANIZER

    @property
    def is_participant_role(self):
        return self.role == self.Role.PARTICIPANT

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_partner_role(self):
        return self.role == self.Role.PARTNER

    @property
    def is_premium(self):
        if not self.premium_until:
            return False
        from django.utils import timezone

        return self.premium_until > timezone.now()
