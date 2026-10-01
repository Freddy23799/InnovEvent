from django.conf import settings
from django.db import models

from apps.documents.validators import validate_image_file


class TalentProfile(models.Model):
    """Compte « Talent » (section 5 du cahier des charges) — un particulier à
    la recherche d'une opportunité (mission, freelance, stage...), distinct
    du « Professionnel » (prestataire qui VEND un service). Rattaché à un
    compte `role="partner"` comme les autres profils de partenaires, aucun
    nouveau rôle applicatif."""

    class VerificationStatus(models.TextChoices):
        NOT_VERIFIED = "not_verified", "Non vérifié"
        PROFILE_VERIFIED = "profile_verified", "Profil vérifié"
        IDENTITY_VERIFIED = "identity_verified", "Identité vérifiée"
        COMPANY_VERIFIED = "company_verified", "Entreprise vérifiée"
        PORTFOLIO_VERIFIED = "portfolio_verified", "Portfolio vérifié"
        PROFESSIONAL_PARTNER = "professional_partner", "Partenaire professionnel"

    class Availability(models.TextChoices):
        IMMEDIATE = "immediate", "Immédiate"
        WITHIN_MONTH = "within_month", "Sous 1 mois"
        TO_DEFINE = "to_define", "À définir"

    class OpportunityType(models.TextChoices):
        ONE_OFF = "one_off", "Mission ponctuelle"
        FIXED_TERM = "fixed_term", "CDD"
        PERMANENT = "permanent", "CDI"
        INTERNSHIP = "internship", "Stage"
        FREELANCE = "freelance", "Freelance"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="talent_profile")
    full_name = models.CharField(max_length=150)
    formation = models.TextField(blank=True, help_text="Formation / parcours académique")
    competences = models.CharField(max_length=300, blank=True, help_text="Séparées par des virgules")
    experience = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    disponibilite = models.CharField(max_length=20, choices=Availability.choices, default=Availability.TO_DEFINE)
    opportunity_type = models.CharField(max_length=20, choices=OpportunityType.choices, default=OpportunityType.ONE_OFF)
    photo = models.ImageField(upload_to="talents/photos/", blank=True, null=True, validators=[validate_image_file])
    verification_status = models.CharField(
        max_length=25, choices=VerificationStatus.choices, default=VerificationStatus.NOT_VERIFIED,
        help_text="Statut de vérification, accordé par l'administration.",
    )
    is_active = models.BooleanField(default=True, help_text="Décocher pour masquer le profil sans le supprimer.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name

    @property
    def is_verified(self):
        return self.verification_status != self.VerificationStatus.NOT_VERIFIED


class TalentPortfolioItem(models.Model):
    profile = models.ForeignKey(TalentProfile, on_delete=models.CASCADE, related_name="portfolio_items")
    image = models.ImageField(upload_to="talents/portfolio/", validators=[validate_image_file])
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.caption or f"Portfolio #{self.pk}"


class TalentMission(models.Model):
    """Mission fictive ou réelle publiée par un prestataire pour les talents."""
    class MissionType(models.TextChoices):
        ONE_OFF = "one_off", "Mission ponctuelle"
        FIXED_TERM = "fixed_term", "CDD"
        PERMANENT = "permanent", "CDI"
        INTERNSHIP = "internship", "Stage"
        FREELANCE = "freelance", "Freelance"

    title = models.CharField(max_length=180)
    provider_name = models.CharField(max_length=160)
    provider_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="talent_missions")
    city = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    mission_type = models.CharField(max_length=20, choices=MissionType.choices, default=MissionType.ONE_OFF)
    starts_at = models.DateField(null=True, blank=True)
    compensation = models.CharField(max_length=100, blank=True)
    skills = models.CharField(max_length=300, blank=True, help_text="Compétences séparées par des virgules")
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.provider_name}"
