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

    REQUIRED_FOR_VISIBILITY = {
        "full_name": "nom complet", "city": "ville", "formation": "formation",
        "competences": "compétences", "experience": "expérience", "photo": "photo",
    }

    @property
    def missing_fields(self):
        """Champs à compléter avant de pouvoir payer la visibilité du profil."""
        missing = [label for field, label in self.REQUIRED_FOR_VISIBILITY.items() if not getattr(self, field)]
        if not self.portfolio_items.exists():
            missing.append("au moins une réalisation")
        return missing

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
