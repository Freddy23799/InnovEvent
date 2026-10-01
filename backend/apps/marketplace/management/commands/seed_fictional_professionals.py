from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.marketplace.models import (
    MarketplaceSubscription,
    MarketplaceType,
    ProfessionalProfile,
    ProfessionalService,
)

PROFILES = [
    {
        "username": "presta_bella_fleurs",
        "first_name": "Bella", "last_name": "Nkeng",
        "photo": "/tmp/seed_photos/p1_bella.jpg",
        "marketplace_type": MarketplaceType.INTERIOR_DESIGN,
        "category": "florist",
        "business_name": "Bella Fleurs & Décoration",
        "description": "Compositions florales et décoration d'espaces pour mariages, baptêmes et événements corporate. Un style épuré et raffiné, pensé pour sublimer chaque lieu.",
        "team_presentation": "Une équipe de 4 fleuristes et décorateurs passionnés, basée à Yaoundé.",
        "specialties": "Mariages, Baptêmes, Décoration florale",
        "city": "Yaoundé", "neighborhood": "Bastos",
        "service_area": "Yaoundé et environs",
        "contact_phone": "+237 6 90 11 22 33", "contact_email": "contact@bellafleurs.example",
        "is_verified": True,
        "services": [
            {"name": "Décoration florale de salle", "pricing_type": "fixed", "price_from": 120000, "duration_label": "1 journée"},
            {"name": "Bouquet & boutonnières mariés", "pricing_type": "fixed", "price_from": 35000, "duration_label": None},
        ],
    },
    {
        "username": "presta_dj_kalvin",
        "first_name": "Kalvin", "last_name": "Mbarga",
        "photo": "/tmp/seed_photos/p2_kalvin.jpg",
        "marketplace_type": MarketplaceType.ACTORS,
        "category": "dj",
        "business_name": "DJ Kalvin Mix",
        "description": "DJ professionnel événementiel depuis 8 ans : mariages, anniversaires, soirées corporate. Ambiance garantie, matériel son & lumière inclus.",
        "team_presentation": "",
        "specialties": "Mariages, Anniversaires, Soirées corporate",
        "city": "Douala", "neighborhood": "Bonapriso",
        "service_area": "Douala, Yaoundé sur devis",
        "contact_phone": "+237 6 90 22 33 44", "contact_email": "kalvinmix@innovevent.example",
        "is_verified": True,
        "services": [
            {"name": "Animation DJ soirée complète", "pricing_type": "fixed", "price_from": 180000, "duration_label": "6 heures"},
            {"name": "Sonorisation + éclairage additionnel", "pricing_type": "quote", "price_from": None, "duration_label": None},
        ],
    },
    {
        "username": "presta_soundwave",
        "first_name": "Yannick", "last_name": "Ateba",
        "photo": "/tmp/seed_photos/p3_soundwave.jpg",
        "marketplace_type": MarketplaceType.ACTORS,
        "category": "sound",
        "business_name": "SoundWave Sonorisation",
        "description": "Location et prestation de sonorisation professionnelle pour conférences, concerts et événements d'entreprise. Techniciens son certifiés.",
        "team_presentation": "3 techniciens son, matériel Yamaha & JBL professionnel.",
        "specialties": "Conférences, Concerts, Événements corporate",
        "city": "Douala", "neighborhood": "Akwa",
        "service_area": "Littoral & Centre",
        "contact_phone": "+237 6 90 33 44 55", "contact_email": "contact@soundwave.example",
        "is_verified": False,
        "services": [
            {"name": "Sonorisation salle jusqu'à 300 pers.", "pricing_type": "fixed", "price_from": 150000, "duration_label": "1 journée"},
        ],
    },
    {
        "username": "presta_saveurs_afrique",
        "first_name": "Joseph", "last_name": "Fotso",
        "photo": "/tmp/seed_photos/p4_saveurs.jpg",
        "marketplace_type": MarketplaceType.ACTORS,
        "category": "caterer",
        "business_name": "Saveurs d'Afrique Traiteur",
        "description": "Traiteur événementiel spécialisé en cuisine camerounaise et internationale. Buffets, cocktails dînatoires et service à table pour tous types d'événements.",
        "team_presentation": "Une brigade de 10 personnes dirigée par un chef formé à l'international.",
        "specialties": "Mariages, Galas, Cocktails d'entreprise",
        "city": "Yaoundé", "neighborhood": "Mvan",
        "service_area": "Yaoundé et environs",
        "contact_phone": "+237 6 90 44 55 66", "contact_email": "contact@saveursafrique.example",
        "is_verified": True,
        "services": [
            {"name": "Buffet complet (par invité)", "pricing_type": "fixed", "price_from": 8500, "duration_label": None},
            {"name": "Cocktail dînatoire premium", "pricing_type": "quote", "price_from": None, "duration_label": None},
        ],
    },
    {
        "username": "presta_elegance_design",
        "first_name": "Patrick", "last_name": "Essomba",
        "photo": "/tmp/seed_photos/p5_elegance.jpg",
        "marketplace_type": MarketplaceType.INTERIOR_DESIGN,
        "category": "interior_architect",
        "business_name": "Élégance Design Intérieur",
        "description": "Architecte d'intérieur spécialisé dans l'aménagement d'espaces événementiels et résidentiels haut de gamme. Conception 3D et suivi de chantier inclus.",
        "team_presentation": "Cabinet de 5 architectes et décorateurs d'intérieur.",
        "specialties": "Aménagement de salles, Design résidentiel, Scénographie",
        "city": "Yaoundé", "neighborhood": "Bastos",
        "service_area": "Yaoundé, Douala sur devis",
        "contact_phone": "+237 6 90 55 66 77", "contact_email": "contact@elegancedesign.example",
        "is_verified": True,
        "services": [
            {"name": "Conception 3D d'espace événementiel", "pricing_type": "quote", "price_from": None, "duration_label": None},
            {"name": "Aménagement complet de salle", "pricing_type": "fixed", "price_from": 450000, "duration_label": "Sur devis"},
        ],
    },
    {
        "username": "presta_prestige_events",
        "first_name": "Michel", "last_name": "Owona",
        "photo": "/tmp/seed_photos/p6_prestige.jpg",
        "marketplace_type": MarketplaceType.ACTORS,
        "category": "agency",
        "business_name": "Prestige Events Agency",
        "description": "Agence événementielle full-service : conception, coordination et exécution d'événements corporate et privés, de A à Z.",
        "team_presentation": "Une équipe de 6 chargés de projet événementiel.",
        "specialties": "Événements corporate, Lancements de produits, Séminaires",
        "city": "Douala", "neighborhood": "Bonanjo",
        "service_area": "National",
        "contact_phone": "+237 6 90 66 77 88", "contact_email": "contact@prestigeevents.example",
        "is_verified": True,
        "services": [
            {"name": "Coordination complète d'événement", "pricing_type": "quote", "price_from": None, "duration_label": None},
        ],
    },
    {
        "username": "presta_mariage_parfait",
        "first_name": "Carine", "last_name": "Belinga",
        "photo": "/tmp/seed_photos/p7_mariage.jpg",
        "marketplace_type": MarketplaceType.ACTORS,
        "category": "wedding_planner",
        "business_name": "Mariage Parfait Events",
        "description": "Wedding planner dédiée à la conception et l'organisation de mariages sur-mesure, du premier rendez-vous jusqu'au jour J.",
        "team_presentation": "Équipe de 3 wedding planners, disponibles toute l'année.",
        "specialties": "Mariages traditionnels, Mariages modernes, Cérémonies civiles",
        "city": "Yaoundé", "neighborhood": "Omnisport",
        "service_area": "Yaoundé, Douala",
        "contact_phone": "+237 6 90 77 88 99", "contact_email": "contact@mariageparfait.example",
        "is_verified": True,
        "services": [
            {"name": "Organisation complète de mariage", "pricing_type": "fixed", "price_from": 650000, "duration_label": "Forfait complet"},
            {"name": "Coordination jour J uniquement", "pricing_type": "fixed", "price_from": 150000, "duration_label": "1 journée"},
        ],
    },
]


class Command(BaseCommand):
    """Crée des profils professionnels fictifs (avec photo réelle, services et
    abonnement actif) pour peupler les marketplaces premium à des fins de
    démonstration. Idempotent."""

    help = "Seed de profils professionnels fictifs pour les marketplaces premium."

    def handle(self, *args, **options):
        created_count = 0
        for entry in PROFILES:
            user, user_created = User.objects.get_or_create(
                username=entry["username"],
                defaults=dict(
                    email=entry["contact_email"],
                    role=User.Role.PARTNER,
                    first_name=entry["first_name"],
                    last_name=entry["last_name"],
                    phone=entry["contact_phone"],
                    is_verified=True,
                ),
            )
            if user_created:
                user.set_password("Prestataire!2026")
                user.save()

            sub, _ = MarketplaceSubscription.objects.get_or_create(
                user=user, marketplace_type=entry["marketplace_type"],
                defaults={"expires_at": timezone.now() + timedelta(days=365)},
            )
            if sub.expires_at < timezone.now():
                sub.expires_at = timezone.now() + timedelta(days=365)
                sub.save(update_fields=["expires_at"])

            profile, profile_created = ProfessionalProfile.objects.get_or_create(
                user=user,
                defaults=dict(
                    marketplace_type=entry["marketplace_type"],
                    category=entry["category"],
                    business_name=entry["business_name"],
                    description=entry["description"],
                    team_presentation=entry["team_presentation"],
                    specialties=entry["specialties"],
                    city=entry["city"], neighborhood=entry["neighborhood"],
                    service_area=entry["service_area"],
                    contact_phone=entry["contact_phone"], contact_email=entry["contact_email"],
                    is_verified=entry["is_verified"], is_active=True,
                ),
            )
            if profile_created:
                try:
                    with open(entry["photo"], "rb") as fh:
                        filename = entry["photo"].split("/")[-1]
                        profile.logo.save(filename, File(fh), save=True)
                except OSError:
                    self.stdout.write(self.style.WARNING(f"Photo introuvable pour {entry['business_name']}"))
                created_count += 1

            for service_entry in entry["services"]:
                ProfessionalService.objects.get_or_create(
                    profile=profile, name=service_entry["name"],
                    defaults=dict(
                        pricing_type=service_entry["pricing_type"],
                        price_from=service_entry["price_from"],
                        duration_label=service_entry["duration_label"] or "",
                        is_active=True,
                    ),
                )

        self.stdout.write(self.style.SUCCESS(f"{created_count} profil(s) professionnel(s) fictif(s) créé(s)."))
        self.stdout.write("Mot de passe commun : Prestataire!2026")
