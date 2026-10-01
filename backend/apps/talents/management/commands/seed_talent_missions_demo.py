from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.marketplace.models import MarketplaceType, SubscriptionPlan
from apps.talents.models import TalentMission, TalentProfile


class Command(BaseCommand):
    help = "Prépare un compte talent fictif et des missions de prestataires pour la démonstration."

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
            "label": "30 jours — Missions talent", "months": 1, "duration_days": 30,
            "price": 1000, "discount_percent": 0, "order": 0,
            "marketplace_type": MarketplaceType.TALENT_MISSIONS,
        })
        offers = [
            ("Assistant·e de coordination — mariage", "Éclat Events", "Douala", "Appui au planning, coordination des prestataires et accueil des invités pour un mariage de 180 personnes.", "one_off", "2026-10-18", "45 000 FCFA", "Coordination,Accueil,Organisation"),
            ("Photographe événementiel", "Studio Lumière", "Yaoundé", "Couverture photo d’un lancement de produit. Portfolio de photographie événementielle souhaité.", "freelance", "2026-10-24", "À discuter", "Photographie,Retouche,Événementiel"),
            ("Assistant·e décoration de salle", "Déco & Fêtes", "Douala", "Préparation de la salle, installation des éléments décoratifs et rangement après réception.", "internship", "2026-11-02", "Indemnité de stage", "Décoration,Travail en équipe"),
            ("Régisseur·se son et lumière", "Pulse Technique", "Bafoussam", "Renfort technique pour une série de conférences : installation, conduite et démontage du matériel.", "fixed_term", "2026-11-10", "80 000 FCFA / mois", "Sonorisation,Éclairage,Régie"),
            ("Hôte·sse d’accueil bilingue", "Signature Réceptions", "Kribi", "Accueil et orientation des participants pendant un séminaire de deux jours.", "one_off", "2026-11-16", "30 000 FCFA", "Accueil,Anglais,Protocole"),
        ]
        provider_accounts = {}
        for title, provider, city, description, kind, starts, pay, skills in offers:
            provider_slug = provider.lower().replace(" ", "_").replace("&", "and")
            provider_user, provider_created = User.objects.get_or_create(
                username=f"prestataire_{provider_slug}",
                defaults={"email": f"{provider_slug}@innovevent.example", "role": User.Role.PARTNER,
                          "first_name": provider.split()[0], "last_name": "Prestataire", "is_verified": True},
            )
            if provider_created:
                provider_user.set_password("Prestataire!2026")
                provider_user.save()
            elif provider_user.role != User.Role.PARTNER:
                provider_user.role = User.Role.PARTNER
                provider_user.save(update_fields=["role"])
            provider_accounts[provider] = provider_user
            TalentMission.objects.update_or_create(title=title, provider_name=provider, defaults={
                "provider_user": provider_user, "city": city, "description": description, "mission_type": kind,
                "starts_at": date.fromisoformat(starts), "compensation": pay,
                "skills": skills, "is_active": True, "is_demo": True,
            })
        self.stdout.write(self.style.SUCCESS("Compte talent et missions de démonstration prêts."))
        self.stdout.write("Identifiant : talent_demo")
        self.stdout.write("Mot de passe : Talent!2026")
        self.stdout.write("Abonnement : 1 000 XAF / 30 jours, à acheter depuis l'espace talent.")
        self.stdout.write("Prestataires fictifs : prestataire_* / Prestataire!2026")
