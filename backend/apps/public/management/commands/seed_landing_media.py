import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from apps.public.models import LandingMedia

# Sélection curatée des plus belles photos réelles InnovEvent, une sous-liste par
# catégorie de la page d'accueil publique. Chaque catégorie lit son propre
# sous-dossier source (mêmes noms que les dossiers fournis par l'administration :
# deco, formation, gal, accesoire), pour ne jamais mélanger le contenu d'une
# catégorie avec une autre.
# (sous-dossier source, nom de fichier, libellé, légende courte)
CURATION = {
    LandingMedia.Category.DECO: (
        "deco",
        [
            ("WhatsApp_Image_2026-09-07_at_09.36.20.jpeg", "Arche florale & table d'honneur", "Cérémonie sous arche fleurie"),
            ("WhatsApp_Image_2026-09-07_at_09.37.06_3.jpeg", "Arche florale, ambiance nocturne", "Décor romantique en soirée"),
            ("WhatsApp_Image_2026-09-07_at_09.37.08.jpeg", "Candélabre cristal & table dorée", "Élégance et raffinement"),
            ("WhatsApp_Image_2026-09-07_at_09.40.13.jpeg", "Centre de table floral", "Compositions florales sur-mesure"),
            ("WhatsApp_Image_2026-09-07_at_09.40.14.jpeg", "Table d'honneur florale", "Roses blanches et pourpres"),
            ("WhatsApp_Image_2026-09-07_at_09.40.18.jpeg", "Centre de table original", "Une touche créative et unique"),
            ("WhatsApp_Image_2026-09-07_at_09.37.05.jpeg", "Lustre suspendu & table ronde", "Mise en scène lumineuse"),
            ("WhatsApp_Image_2026-09-07_at_09.40.19.jpeg", "Table ronde dorée & verdure", "Réception festive et raffinée"),
        ],
    ),
    LandingMedia.Category.REALISATION: (
        "gal",
        [
            ("WhatsApp_Image_2026-09-07_at_11.07.03.jpeg", "Réception sur toit-terrasse", "Ambiance bohème et végétale"),
            ("WhatsApp_Image_2026-09-07_at_11.07.03_1.jpeg", "Grande réception sous tente", "Capacité et confort pour vos invités"),
            ("WhatsApp_Image_2026-09-07_at_11.07.04_1.jpeg", "Centre de table floral rose & or", "Raffinement et couleurs douces"),
            ("WhatsApp_Image_2026-09-07_at_11.11.20_1.jpeg", "Allée de cérémonie extérieure", "Cérémonie en plein air, thème mauve"),
            ("WhatsApp_Image_2026-09-07_at_11.11.21.jpeg", "Table d'honneur au bord de la piscine", "Réception au coucher du soleil"),
            ("WhatsApp_Image_2026-09-07_at_11.11.22.jpeg", "Scénographie arche verte & dorée", "Mise en scène spectaculaire"),
            ("WhatsApp_Image_2026-09-07_at_11.07.04.jpeg", "Table rose & centre floral", "Douceur des tons pastel"),
            ("WhatsApp_Image_2026-09-07_at_11.07.05.jpeg", "Table d'honneur florale rouge & blanc", "Élégance classique et intemporelle"),
            ("WhatsApp_Image_2026-09-07_at_11.11.21_1.jpeg", "Vue aérienne, réception rosée", "Organisation de grande envergure"),
            ("WhatsApp_Image_2026-09-07_at_11.11.22_1.jpeg", "Thème rouge & rayures graphiques", "Une scénographie audacieuse"),
            ("WhatsApp_Image_2026-09-07_at_11.07.05_1.jpeg", "Candélabre doré, table mauve", "Raffinement et lumière"),
            ("WhatsApp_Image_2026-09-07_at_11.07.05_2.jpeg", "Vue aérienne, table mauve", "Réception vue du dessus"),
        ],
    ),
    LandingMedia.Category.ACCESSOIRE: (
        "accesoire",
        [
            ("WhatsApp_Image_2026-09-07_at_13.29.41.jpeg", "Table ronde pliante", "Location de mobilier événementiel", "3 000 FCFA / table / jour"),
            ("WhatsApp_Image_2026-09-07_at_13.30.05.jpeg", "Tentes de réception", "Structures pour événements extérieurs", "80 000 FCFA / tente / jour"),
            ("WhatsApp_Image_2026-09-07_at_13.30.23.jpeg", "Chaises empilables", "Mobilier robuste, grande capacité", "500 FCFA / chaise / jour"),
            ("WhatsApp_Image_2026-09-07_at_13.30.37.jpeg", "Table ronde bois", "Location de tables pour tout format", "4 000 FCFA / table / jour"),
            ("WhatsApp_Image_2026-09-07_at_13.40.58.jpeg", "Projecteur LED à léds", "Éclairage scénique et ambiance", "5 000 FCFA / unité / jour"),
            ("WhatsApp_Image_2026-09-07_at_13.41.17.jpeg", "Système de sonorisation ligne", "Sonorisation professionnelle", "100 000 FCFA / pack / jour"),
        ],
    ),
    LandingMedia.Category.FORMATION: (
        "formation",
        [
            ("WhatsApp_Image_2026-09-07_at_11.11.18_1.jpeg", "Atelier composition florale", "Apprentissage de l'art floral"),
            ("WhatsApp_Image_2026-09-07_at_11.11.18_3.jpeg", "Atelier pratique en groupe", "Formation wedding planning & art floral"),
            ("WhatsApp_Image_2026-09-07_at_11.11.18.jpeg", "Remise des certificats", "Une promotion diplômée par l'Academy"),
            ("WhatsApp_Image_2026-09-07_at_11.11.19.jpeg", "Félicitations aux apprenants", "Un accompagnement jusqu'à la réussite"),
        ],
    ),
}


def _normalised_filename(filename):
    """Compare les noms fournis avec ceux exportés par WhatsApp.

    Les fichiers sources gardent les espaces et les suffixes ``(1)`` de
    WhatsApp, tandis que la curation utilisait des underscores (``_1``).
    Ces graphies désignent la même photo : aucun renommage des originaux n'est
    nécessaire pour les importer.
    """
    return re.sub(r"[\s_()]+", "", Path(filename).stem).casefold()


def _find_source_file(photos_dir, expected_filename):
    matches = [
        path for path in photos_dir.iterdir()
        if path.is_file() and _normalised_filename(path.name) == _normalised_filename(expected_filename)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise CommandError(
            f"Plusieurs fichiers correspondent à {expected_filename!r} dans {photos_dir} : "
            f"{', '.join(path.name for path in matches)}"
        )
    return None


class Command(BaseCommand):
    """Attache la sélection curatée de photos réelles InnovEvent à la photothèque
    de la page d'accueil (LandingMedia), une par catégorie et son propre dossier
    source. Idempotent (get_or_create par libellé+catégorie)."""

    help = "Seed de la photothèque de la page d'accueil à partir d'un dossier de base contenant un sous-dossier par catégorie."

    def add_arguments(self, parser):
        parser.add_argument("base_dir", type=str, help="Dossier contenant les sous-dossiers deco/, formation/, gal/, accesoire/")
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="N'importe rien si la photothèque contient déjà au moins un média.",
        )

    def handle(self, *args, **options):
        base_dir = Path(options["base_dir"])
        if not base_dir.is_dir():
            raise CommandError(f"Dossier introuvable : {base_dir}")

        # Préserve la photothèque gérée depuis le back-office. L'initialisation
        # automatique ne sert qu'à rendre une nouvelle base immédiatement
        # présentable, jamais à rétablir des médias supprimés volontairement.
        if options["if_empty"] and LandingMedia.objects.exists():
            self.stdout.write("Photothèque déjà renseignée ; import initial ignoré.")
            return

        created_count = 0
        for category, (subfolder, items) in CURATION.items():
            photos_dir = base_dir / subfolder
            for order, item in enumerate(items):
                filename, label, caption = item[0], item[1], item[2]
                price_label = item[3] if len(item) > 3 else ""
                path = _find_source_file(photos_dir, filename)
                if path is None:
                    self.stdout.write(self.style.WARNING(f"Fichier manquant, ignoré : {subfolder}/{filename}"))
                    continue

                media, created = LandingMedia.objects.get_or_create(
                    category=category,
                    label=label,
                    defaults={
                        "caption": caption,
                        "price_label": price_label,
                        "order": order,
                        "is_active": True,
                    },
                )
                if created:
                    with open(path, "rb") as f:
                        media.image.save(path.name, File(f), save=True)
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Créé : [{category}] {label}"))
                else:
                    self.stdout.write(f"Déjà présent, ignoré : [{category}] {label}")

        self.stdout.write(self.style.SUCCESS(f"\n{created_count} médias créés."))
