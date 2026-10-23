"""Versions allégées (WebP redimensionné) des images publiques.

`/media/<image>?w=480` renvoie l'image en 480 px de large au format WebP,
générée au premier appel puis conservée dans `MEDIA_ROOT/_variants/`. Le
navigateur ne télécharge ainsi que la taille réellement affichée (quelques
dizaines de Ko au lieu de l'original de plusieurs centaines de Ko), et la
version `w=32` sert d'aperçu flou instantané pendant le chargement.
L'original n'est jamais modifié ; il reste servi sans paramètre `w`.
"""

import logging
import os
import tempfile
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Largeurs autorisées : une liste fermée évite qu'un visiteur fasse générer
# une infinité de fichiers (w=1, w=2, ...).
VARIANT_WIDTHS = (32, 160, 320, 480, 640, 960, 1280, 1920)
PLACEHOLDER_WIDTH = 32
VARIANTS_DIR = "_variants"


def requested_width(request):
    """Largeur demandée via `?w=`, None sans paramètre ; 404 si non autorisée."""
    raw = request.GET.get("w")
    if raw is None:
        return None
    try:
        width = int(raw)
    except ValueError:
        raise Http404("Taille d'image inconnue.")
    if width not in VARIANT_WIDTHS:
        raise Http404("Taille d'image inconnue.")
    return width


def variant_response(storage_name, width, cache_control):
    """Réponse WebP de `storage_name` en `width` px, générée si besoin."""
    variant_name = f"{VARIANTS_DIR}/w{width}/{storage_name}.webp"
    try:
        if _is_stale(variant_name, storage_name):
            _build_variant(storage_name, variant_name, width)
        handle = default_storage.open(variant_name, "rb")
    except (FileNotFoundError, OSError, Image.DecompressionBombError, Image.UnidentifiedImageError):
        logger.warning("Version %spx impossible pour %s.", width, storage_name, exc_info=True)
        raise Http404("Image introuvable.")

    response = FileResponse(handle, content_type="image/webp")
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Cache-Control"] = cache_control
    return response


def _is_stale(variant_name, storage_name):
    if not default_storage.exists(variant_name):
        return True
    # Original remplacé sous le même nom : la version doit être régénérée.
    return default_storage.get_modified_time(storage_name) > default_storage.get_modified_time(variant_name)


def _build_variant(storage_name, variant_name, width):
    with default_storage.open(storage_name, "rb") as source:
        image = Image.open(source)
        image = ImageOps.exif_transpose(image)
        image.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info or image.mode in ("LA", "P") else "RGB")
        buffer = BytesIO()
        quality = 40 if width == PLACEHOLDER_WIDTH else 82
        image.save(buffer, format="WEBP", quality=quality, method=4)

    content = buffer.getvalue()
    try:
        target = default_storage.path(variant_name)
    except NotImplementedError:
        if default_storage.exists(variant_name):
            default_storage.delete(variant_name)
        default_storage.save(variant_name, ContentFile(content))
        return
    # Écriture atomique : deux visiteurs simultanés ne lisent jamais un
    # fichier à moitié écrit.
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".tmp")
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)
    os.chmod(temp_path, 0o644)
    os.replace(temp_path, target)
