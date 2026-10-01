from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.marketplace.models import (
    MarketplaceListing,
    MarketplaceSubscription,
    ProfessionalProfile,
    ProfessionalService,
)


class Command(BaseCommand):
    """Crée un compte partenaire de démonstration, déjà abonné au marketplace
    « Acteurs » et avec un profil professionnel publié (services inclus), afin
    de pouvoir tester immédiatement le parcours côté client (consultation,
    prise de contact). Idempotent."""

    help = "Seed d'un compte partenaire + abonnement + profil professionnel de démonstration."

    def handle(self, *args, **options):
        partner, created = User.objects.get_or_create(
            username="partenaire_demo",
            defaults=dict(
                email="partenaire@innovevent.example",
                role=User.Role.PARTNER,
                first_name="Aline",
                last_name="Nguemo",
                is_verified=True,
            ),
        )
        if created:
            partner.set_password("Partenaire!2026")
            partner.save()
        elif partner.role != User.Role.PARTNER:
            partner.role = User.Role.PARTNER
            partner.save(update_fields=["role"])

        sub, _ = MarketplaceSubscription.objects.get_or_create(
            user=partner, marketplace_type=MarketplaceListing.MarketplaceType.ACTORS,
            defaults={"expires_at": timezone.now() + timedelta(days=30)},
        )
        if sub.expires_at < timezone.now():
            sub.expires_at = timezone.now() + timedelta(days=30)
            sub.save(update_fields=["expires_at"])

        # Nettoyage d'une éventuelle annonce héritée d'avant l'introduction du
        # profil professionnel (les marketplaces "acteurs"/"design intérieur"
        # utilisent désormais exclusivement ProfessionalProfile).
        MarketplaceListing.objects.filter(
            created_by=partner, marketplace_type=MarketplaceListing.MarketplaceType.ACTORS,
        ).delete()

        profile, _ = ProfessionalProfile.objects.get_or_create(
            user=partner,
            defaults=dict(
                marketplace_type=MarketplaceListing.MarketplaceType.ACTORS,
                category="decoration",
                business_name="Aline Déco Events",
                description="Décoration florale et scénographie sur-mesure pour mariages, galas et anniversaires.",
                team_presentation="Une équipe de 6 décorateurs et scénographes basée à Yaoundé.",
                specialties="Mariages, Galas, Anniversaires",
                city="Yaoundé", neighborhood="Bastos", service_area="Yaoundé, Douala et environs",
                contact_phone="+237 6 90 00 00 00", contact_email="partenaire@innovevent.example",
                is_verified=True, is_active=True,
            ),
        )

        ProfessionalService.objects.get_or_create(
            profile=profile, name="Décoration événementielle Aline N.",
            defaults=dict(
                description="Décoration florale et scénographie sur-mesure pour mariages, galas et anniversaires.",
                pricing_type=ProfessionalService.PricingType.FIXED, price_from=150000, currency="XAF",
                duration_label="1 journée", is_active=True,
            ),
        )

        self.stdout.write(self.style.SUCCESS("Partenaire de démonstration prêt :"))
        self.stdout.write("  - partenaire_demo / Partenaire!2026 (Partenaire)")
        self.stdout.write("  - Abonné au marketplace « Acteurs », profil professionnel déjà publié.")
