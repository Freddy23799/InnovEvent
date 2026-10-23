from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from apps.documents.image_variants import VARIANTS_DIR, _build_variant, _is_stale
from apps.public.views import PUBLIC_MEDIA_FIELDS

# Tailles demandées par le frontend pour l'aperçu flou, les vignettes et les
# grandes images ; les autres sont générées à la première consultation.
DEFAULT_WIDTHS = (32, 480, 960)
EXTRA_FIELDS = [("public.LandingMedia", "image"), ("events.Event", "photo")]


class Command(BaseCommand):
    help = "Prépare les versions WebP allégées des images publiques (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--widths", type=int, nargs="+", default=list(DEFAULT_WIDTHS))

    def handle(self, *args, widths, **options):
        fields = [field for group in PUBLIC_MEDIA_FIELDS.values() for field in group] + EXTRA_FIELDS
        created = failed = 0
        for model_label, field_name in fields:
            model = apps.get_model(model_label)
            names = model._default_manager.exclude(**{field_name: ""}).exclude(**{f"{field_name}__isnull": True})
            for name in names.values_list(field_name, flat=True).distinct():
                if not default_storage.exists(name):
                    continue
                for width in widths:
                    variant_name = f"{VARIANTS_DIR}/w{width}/{name}.webp"
                    try:
                        if _is_stale(variant_name, name):
                            _build_variant(name, variant_name, width)
                            created += 1
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(f"{name} ({width}px) : {exc}")
        self.stdout.write(f"{created} version(s) d'image générée(s), {failed} échec(s).")
