from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from apps.marketplace.models import MarketplaceListing, MarketplaceType, SaleCategory

# Produits « Art de la table » photographiés en boutique (dossier
# frontend/image/la). Prix indicatifs : à ajuster depuis l'administration
# (Marketplaces Premium → Annonces).
PRODUCTS = [
    {
        "file": "WhatsApp Image 2026-11-05 at 11.17.23.jpeg",
        "title": "Verres à pied colorés en relief",
        "subcategory": "glasses",
        "price": Decimal("2500"),
        "description": (
            "Verres à pied en verre pressé à motif diamant, disponibles en bleu, ambre et vert olive.\n"
            "Idéals pour apporter de la couleur à une table de mariage, de gala ou d'anniversaire.\n"
            "Prix à la pièce — mélangez les couleurs selon votre décoration."
        ),
    },
    {
        "file": "WhatsApp Image 2026-11-05 at 11.17.10.jpeg",
        "title": "Ensemble de table noir & liseré or",
        "subcategory": "plates",
        "price": Decimal("12500"),
        "description": (
            "Couvert complet pour une table élégante : sous-assiette noire texturée, assiette plate et "
            "assiette à dessert blanches à large liseré doré.\n"
            "Les verres striés présentés sur la photo sont vendus séparément.\n"
            "Prix par couvert."
        ),
    },
    {
        "file": "WhatsApp Image 2026-11-05 at 11.17.35.jpeg",
        "title": "Sous-assiette dorée festonnée & assiette noire",
        "subcategory": "charger_plates",
        "price": Decimal("6500"),
        "description": (
            "Sous-assiette dorée aux bords festonnés associée à une assiette noire brillante.\n"
            "Un contraste chic pour les dîners de gala et les réceptions de soirée.\n"
            "Prix par ensemble (sous-assiette + assiette)."
        ),
    },
    {
        "file": "WhatsApp Image 2026-11-05 at 11.17.47.jpeg",
        "title": "Set de table tressé doré & assiettes blanches",
        "subcategory": "charger_plates",
        "price": Decimal("8500"),
        "description": (
            "Set de table rond tressé doré à bords ondulés, avec assiette plate et assiette creuse "
            "en porcelaine blanche.\n"
            "Parfait pour une décoration chaleureuse et lumineuse.\n"
            "Prix par couvert."
        ),
    },
    {
        "file": "WhatsApp Image 2026-11-05 at 11.18.01.jpeg",
        "title": "Sous-assiette blanche festonnée liseré or",
        "subcategory": "charger_plates",
        "price": Decimal("7500"),
        "description": (
            "Sous-assiette blanche aux bords festonnés soulignés d'un fin liseré doré, avec assiette "
            "plate et assiette à dessert blanches.\n"
            "Un classique raffiné pour les mariages et les cérémonies.\n"
            "Prix par couvert."
        ),
    },
    {
        "file": "WhatsApp Image 2026-11-05 at 11.18.16.jpeg",
        "title": "Assiettes fleur blanches & couverts dorés",
        "subcategory": "plates",
        "price": Decimal("9500"),
        "description": (
            "Assiettes en porcelaine blanche en forme de fleur, présentées sur un set tressé naturel, "
            "avec couverts dorés à manche effet bois.\n"
            "Une ambiance bohème et naturelle pour vos réceptions.\n"
            "Prix par couvert (assiettes + couverts)."
        ),
    },
]


class Command(BaseCommand):
    help = "Ajoute à la boutique les produits « Art de la table » photographiés (idempotent : par titre)."

    def add_arguments(self, parser):
        parser.add_argument("image_dir", help="Dossier contenant les photos (frontend/image/la).")

    def handle(self, *args, image_dir, **options):
        folder = Path(image_dir)
        if not folder.is_dir():
            raise CommandError(f"Dossier introuvable : {folder}")

        created = skipped = 0
        for order, product in enumerate(PRODUCTS):
            if MarketplaceListing.objects.filter(marketplace_type=MarketplaceType.SALE, title=product["title"]).exists():
                skipped += 1
                continue
            path = folder / product["file"]
            if not path.is_file():
                raise CommandError(f"Photo manquante : {path}")
            listing = MarketplaceListing(
                marketplace_type=MarketplaceType.SALE,
                title=product["title"],
                description=product["description"],
                price=product["price"],
                currency="XAF",
                category=SaleCategory.TABLEWARE,
                subcategory=product["subcategory"],
                requires_subscription=False,
                is_active=True,
                order=order,
            )
            with path.open("rb") as handle:
                listing.photo.save(f"art-de-la-table-{order + 1}.jpg", File(handle), save=False)
            listing.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} produit(s) ajouté(s), {skipped} déjà présent(s)."))
