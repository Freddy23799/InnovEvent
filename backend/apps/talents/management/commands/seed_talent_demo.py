from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.marketplace.models import MarketplaceType, SubscriptionPlan
from apps.talents.models import TalentProfile


class Command(BaseCommand):
    help = "Prépare un compte talent fictif et la formule « Visibilité talent » pour la démonstration."

    def handle(self, *args, **options):
        talent, created = User.objects.get_or_create(
            username="talent_demo",
            defaults={"email": "talent@innovevent.example", "role": User.Role.PARTNER,
                      "first_name": "Nadia", "last_name": "Mballa", "is_verified": True},
        )
        if created:
            talent.set_password("Talent!2026")
            talent.save()
        elif talent.role != User.Role.PARTNER:
            talent.role = User.Role.PARTNER
            talent.save(update_fields=["role"])
        TalentProfile.objects.get_or_create(user=talent, defaults={
            "full_name": "Nadia Mballa", "formation": "Licence en communication événementielle",
            "competences": "Coordination, accueil, protocole, réseaux sociaux",
            "experience": "Assistante de production sur plusieurs événements associatifs à Douala.",
            "city": "Douala", "disponibilite": TalentProfile.Availability.IMMEDIATE,
            "opportunity_type": TalentProfile.OpportunityType.ONE_OFF,
        })
        SubscriptionPlan.objects.update_or_create(code="talent_1_month", defaults={
            "label": "30 jours — Visibilité talent", "months": 1, "duration_days": 30,
            "price": 1000, "discount_percent": 0, "order": 0,
            "marketplace_type": MarketplaceType.TALENT_MISSIONS,
        })
        self.stdout.write(self.style.SUCCESS("Compte talent de démonstration prêt."))
        self.stdout.write("Identifiant : talent_demo")
        self.stdout.write("Mot de passe : Talent!2026")
        self.stdout.write("Visibilité : 1 000 XAF / 30 jours, à acheter depuis « Mon profil talent ».")
