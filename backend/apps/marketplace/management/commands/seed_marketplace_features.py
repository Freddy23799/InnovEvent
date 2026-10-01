from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.marketplace.models import (
    CommissionSettings,
    MarketplaceFeature,
    MarketplaceSubscription,
    MarketplaceType,
    SubscriptionPlan,
    SubscriptionTier,
)

# Formules de durée par défaut — l'administration peut ensuite librement
# modifier prix/durées/libellés depuis « Paliers d'abonnement » (get_or_create :
# relancer ce seed ne réinitialise jamais un tarif déjà personnalisé).
SUBSCRIPTION_PLANS = [
    {"code": "1_month", "label": "1 mois", "months": 1, "duration_days": 30, "price": Decimal("15000"), "discount_percent": 0, "order": 0},
    {"code": "3_months", "label": "3 mois", "months": 3, "duration_days": 90, "price": Decimal("42000"), "discount_percent": 7, "order": 1},
    {"code": "6_months", "label": "6 mois", "months": 6, "duration_days": 182, "price": Decimal("80000"), "discount_percent": 11, "order": 2},
    {"code": "12_months", "label": "12 mois", "months": 12, "duration_days": 365, "price": Decimal("150000"), "discount_percent": 17, "order": 3},
]

TIERS = [
    {"code": "free", "label": "Free", "level": 0, "order": 0, "is_default": False,
     "description": "Accès limité : consultation générale, aucune fonctionnalité premium."},
    {"code": "basic", "label": "Basic", "level": 1, "order": 1, "is_default": False,
     "description": "Accès à certaines fonctionnalités du marketplace."},
    {"code": "premium", "label": "Premium", "level": 2, "order": 2, "is_default": True,
     "description": "Accès complet aux fonctionnalités du marketplace."},
    {"code": "pro", "label": "Pro", "level": 3, "order": 3, "is_default": False,
     "description": "Accès complet, plus fonctionnalités avancées (à venir)."},
]

# Une même liste de fonctionnalités type pour les marketplaces "profil
# professionnel" (acteurs, décoration/design intérieur, salles de réception) :
# rien n'est visible — ni la liste, ni la fiche détaillée — pour un compte non
# abonné à CE marketplace précis (l'administration voit toujours tout, via
# resolve_features). "Avis" existe déjà (notation en étoiles) ; "Comparaison"
# et "Calendrier des disponibilités" sont désactivées par défaut car non
# encore développées — l'administration pourra les activer dès qu'elles le
# seront, sans nouvelle fonctionnalité à coder ici.
PROFESSIONAL_FEATURES = [
    {"key": "browse", "label": "Consulter les prestataires", "order": 0,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Liste des prestataires du marketplace — réservée aux comptes abonnés."},
    {"key": "view_profile", "label": "Voir les profils détaillés", "order": 1,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Fiche complète : description, équipe, spécialités, zone d'intervention."},
    {"key": "view_services", "label": "Voir les services & tarifs", "order": 2,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Liste des services proposés, avec tarifs et conditions."},
    {"key": "contact", "label": "Contacter le prestataire", "order": 3,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Messagerie libre directe avec le prestataire, via la plateforme (aucune coordonnée personnelle échangée)."},
    {"key": "book", "label": "Réserver", "order": 4,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Envoi d'une demande de réservation via la plateforme."},
    {"key": "reviews", "label": "Avis", "order": 5,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Notation en étoiles et avis clients."},
    {"key": "favorites", "label": "Favoris", "order": 5,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Enregistrer ce prestataire dans sa liste de favoris."},
    {"key": "comparison", "label": "Comparaison", "order": 6,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.HIDDEN,
     "description": "Comparer plusieurs prestataires côte à côte (fonctionnalité à venir)."},
    {"key": "availability_calendar", "label": "Calendrier des disponibilités", "order": 7,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.UPSELL,
     "description": "Disponibilités du prestataire en temps réel.",
     "upsell_message": "Abonnez-vous pour consulter les disponibilités en temps réel de ce prestataire."},
    {"key": "recommendations", "label": "Recommandations personnalisées", "order": 8,
     "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
     "description": "Suggestions de prestataires basées sur les favoris et demandes de devis du client."},
]

# Accès par catégorie de métiers de la Marketplace des acteurs (barre latérale
# + index de catégories) — un « feature » par groupe, pour que l'admin décide
# quel palier d'abonnement donne accès à quelle catégorie, sans rien coder.
# Par défaut tout est ouvert à n'importe quel abonné actif ; deux catégories
# sont réservées au palier Pro à titre d'exemple (configurable à tout moment
# depuis « Fonctionnalités & permissions »). Les clés doivent rester en phase
# avec les 10 groupes de frontend/src/data/actorCategories.js.
ACTOR_GROUP_FEATURES = [
    {"key": "group_organisation", "label": "Catégorie : Organisation & coordination", "order": 10, "min_tier_code": None},
    {"key": "group_logistique", "label": "Catégorie : Lieu & logistique de base", "order": 11, "min_tier_code": None},
    {"key": "group_decoration", "label": "Catégorie : Décoration & scénographie", "order": 12, "min_tier_code": None},
    {"key": "group_restauration", "label": "Catégorie : Restauration & boissons", "order": 13, "min_tier_code": None},
    {"key": "group_image", "label": "Catégorie : Image & souvenirs", "order": 14, "min_tier_code": None},
    {"key": "group_musique", "label": "Catégorie : Son, musique & lumière", "order": 15, "min_tier_code": None},
    {"key": "group_animation", "label": "Catégorie : Animation & spectacle", "order": 16, "min_tier_code": "pro"},
    {"key": "group_beaute", "label": "Catégorie : Beauté, mode & tenue", "order": 17, "min_tier_code": None},
    {"key": "group_transport", "label": "Catégorie : Transport & hébergement", "order": 18, "min_tier_code": "pro"},
    {"key": "group_support", "label": "Catégorie : Support & impression", "order": 19, "min_tier_code": None},
]

SALE_FEATURES = [
    {"key": "browse", "label": "Consulter les annonces", "order": 0,
     "visibility": MarketplaceFeature.Visibility.EVERYONE, "state": MarketplaceFeature.State.SHOWN,
     "description": "Liste des annonces en accès libre."},
    {"key": "order", "label": "Commander", "order": 1,
     "visibility": MarketplaceFeature.Visibility.AUTHENTICATED, "state": MarketplaceFeature.State.SHOWN,
     "description": "Achat direct d'une annonce (paiement immédiat)."},
]


class Command(BaseCommand):
    """Seed des paliers d'abonnement et des fonctionnalités par défaut du
    moteur de permissions des marketplaces premium. Idempotent — relançable
    sans dupliquer ni écraser les personnalisations déjà faites par l'admin."""

    help = "Seed des paliers d'abonnement et fonctionnalités de marketplace par défaut."

    def handle(self, *args, **options):
        tiers_by_code = {}
        for entry in TIERS:
            tier, _ = SubscriptionTier.objects.get_or_create(code=entry["code"], defaults=entry)
            tiers_by_code[entry["code"]] = tier

        default_tier = tiers_by_code["premium"]

        plans_created = 0
        for entry in SUBSCRIPTION_PLANS:
            _, was_created = SubscriptionPlan.objects.get_or_create(code=entry["code"], defaults=entry)
            plans_created += int(was_created)

        feature_sets = {
            MarketplaceType.ACTORS: PROFESSIONAL_FEATURES,
            MarketplaceType.INTERIOR_DESIGN: PROFESSIONAL_FEATURES,
            MarketplaceType.VENUES: PROFESSIONAL_FEATURES,
            MarketplaceType.SALE: SALE_FEATURES,
        }
        created = 0
        for marketplace_type, features in feature_sets.items():
            for entry in features:
                _, was_created = MarketplaceFeature.objects.get_or_create(
                    marketplace_type=marketplace_type, key=entry["key"],
                    defaults={
                        "label": entry["label"], "description": entry["description"],
                        "visibility": entry["visibility"], "state": entry["state"],
                        "upsell_message": entry.get("upsell_message", ""), "order": entry["order"],
                    },
                )
                created += int(was_created)

        for entry in ACTOR_GROUP_FEATURES:
            min_tier = tiers_by_code.get(entry["min_tier_code"]) if entry["min_tier_code"] else None
            _, was_created = MarketplaceFeature.objects.get_or_create(
                marketplace_type=MarketplaceType.ACTORS, key=entry["key"],
                defaults={
                    "label": entry["label"], "description": "",
                    "visibility": MarketplaceFeature.Visibility.SUBSCRIBER, "state": MarketplaceFeature.State.SHOWN,
                    "min_tier": min_tier, "order": entry["order"],
                },
            )
            created += int(was_created)

        # Abonnements existants sans palier : on leur attribue le palier par
        # défaut (Premium) pour préserver leur accès actuel tel quel.
        updated_subs = MarketplaceSubscription.objects.filter(tier__isnull=True).update(tier=default_tier)

        commissions_created = 0
        for marketplace_type in MarketplaceType.values:
            _, was_created = CommissionSettings.objects.get_or_create(
                marketplace_type=marketplace_type, defaults={"commission_percent": Decimal("5.00")},
            )
            commissions_created += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"{len(tiers_by_code)} palier(s) prêts, {plans_created} formule(s) tarifaire(s) créée(s), "
            f"{created} fonctionnalité(s) créée(s), "
            f"{updated_subs} abonnement(s) existant(s) rattaché(s) au palier « {default_tier.label} », "
            f"{commissions_created} taux de commission créé(s)."
        ))
