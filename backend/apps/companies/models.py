from django.conf import settings
from django.db import models

from apps.documents.validators import validate_document_file


class CompanyProfile(models.Model):
    """Compte « Entreprise » (section 5 du cahier des charges) — distinct du
    profil « Professionnel » (`apps.marketplace.ProfessionalProfile`) : une
    entité juridique (raison sociale, RCCM/NIU, représentant) plutôt qu'un
    prestataire individuel. Rattaché à un compte `role="partner"` comme
    `ProfessionalProfile`/`Carrier` — aucun nouveau rôle applicatif."""

    class VerificationStatus(models.TextChoices):
        NOT_VERIFIED = "not_verified", "Non vérifié"
        PROFILE_VERIFIED = "profile_verified", "Profil vérifié"
        IDENTITY_VERIFIED = "identity_verified", "Identité vérifiée"
        COMPANY_VERIFIED = "company_verified", "Entreprise vérifiée"
        PORTFOLIO_VERIFIED = "portfolio_verified", "Portfolio vérifié"
        PROFESSIONAL_PARTNER = "professional_partner", "Partenaire professionnel"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_profile")
    raison_sociale = models.CharField(max_length=200)
    activite = models.CharField(max_length=200, blank=True, help_text="Secteur d'activité")
    rccm = models.CharField(max_length=100, blank=True, help_text="Numéro RCCM")
    niu = models.CharField(max_length=100, blank=True, help_text="Numéro d'identifiant unique (NIU)")
    adresse = models.CharField(max_length=300, blank=True)
    representant = models.CharField(max_length=150, blank=True, help_text="Représentant légal")
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
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
        return self.raison_sociale

    @property
    def is_verified(self):
        return self.verification_status != self.VerificationStatus.NOT_VERIFIED


class CompanyDocument(models.Model):
    """Documents justificatifs (section 5) — plusieurs par entreprise
    (RCCM, NIU, statuts...), contrairement à `Carrier.documents` (un seul
    fichier) : besoin explicite de pluralité ici."""

    profile = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="companies/documents/", validators=[validate_document_file])
    label = models.CharField(max_length=150, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.label or self.file.name
