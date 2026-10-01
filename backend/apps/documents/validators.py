"""Validation des fichiers/images téléversés par les utilisateurs (audit de
sécurité — section 14/15 du cahier des charges).

Principe : liste blanche, jamais liste noire. On n'autorise que les
extensions/signatures explicitement connues plutôt que d'essayer de deviner
tous les formats dangereux à bloquer — un `.php`/`.exe`/`.sh` renommé en
`.jpg` échoue simplement la vérification de signature ci-dessous, il n'a pas
besoin d'être nommément blacklisté.

Ne remplace PAS un antivirus ; combiné au fait que les fichiers sont servis
par Django (jamais interprétés par le serveur web comme du code exécutable,
voir `nginx/nginx.conf`), cela suffit à éliminer la classe de vulnérabilité
« upload de fichier malveillant exécuté côté serveur »."""

from django.conf import settings
from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_BYTES = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)

# Signature (« magic bytes ») de chaque format autorisé — vérifiée en plus de
# l'extension, pour qu'un fichier ne puisse pas mentir sur sa propre nature.
_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "gif": [b"GIF87a", b"GIF89a"],
    "webp": [b"RIFF"],  # suivi de "WEBP" à l'octet 8, vérifié séparément
    # Formats Office modernes (docx/xlsx/pptx) et .odt sont des archives ZIP.
    "docx": [b"PK\x03\x04"],
    "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # ancien format OLE2 (.doc)
    "odt": [b"PK\x03\x04"],
}

DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "odt"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _check_signature(uploaded_file, extension: str):
    signatures = _SIGNATURES.get(extension)
    if not signatures:
        return
    uploaded_file.seek(0)
    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    if extension == "webp":
        if not (header[:4] == b"RIFF" and header[8:12] == b"WEBP"):
            raise ValidationError("Le contenu du fichier ne correspond pas à son extension.")
        return
    if not any(header.startswith(sig) for sig in signatures):
        raise ValidationError("Le contenu du fichier ne correspond pas à son extension.")


def validate_file_size(uploaded_file, max_size=None):
    limit = max_size or MAX_UPLOAD_SIZE_BYTES
    if uploaded_file.size > limit:
        raise ValidationError(f"Fichier trop volumineux (maximum {limit // (1024 * 1024)} Mo).")


def validate_document_file(uploaded_file, allowed_extensions=None, max_size=None):
    """CV, pièces justificatives... — PDF/Word/OpenDocument uniquement par défaut."""
    allowed = allowed_extensions or DOCUMENT_EXTENSIONS
    validate_file_size(uploaded_file, max_size)
    extension = _extension(uploaded_file.name)
    if extension not in allowed:
        raise ValidationError(f"Format non autorisé — formats acceptés : {', '.join(sorted(allowed))}.")
    _check_signature(uploaded_file, extension)


def validate_image_file(uploaded_file, allowed_extensions=None, max_size=None, max_dimension=6000):
    """Photos de profil, CNI, permis... — sniffing réel via Pillow (pas
    seulement l'extension), plafond de résolution contre les bombes de
    décompression (image minuscule sur disque, énorme une fois décodée)."""
    from PIL import Image

    allowed = allowed_extensions or IMAGE_EXTENSIONS
    validate_file_size(uploaded_file, max_size)
    extension = _extension(uploaded_file.name)
    if extension not in allowed:
        raise ValidationError(f"Format non autorisé — formats acceptés : {', '.join(sorted(allowed))}.")
    _check_signature(uploaded_file, extension)

    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        image.verify()
    except Exception:
        raise ValidationError("Le fichier n'est pas une image valide.")
    finally:
        uploaded_file.seek(0)

    # `verify()` referme le fichier interne de Pillow — on le réouvre pour lire
    # les dimensions réelles avant décompression complète.
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    if image.width > max_dimension or image.height > max_dimension:
        raise ValidationError(f"Image trop grande (maximum {max_dimension}×{max_dimension} pixels).")
    uploaded_file.seek(0)


def validate_attachment_file(uploaded_file, max_size=None):
    """Pièce jointe de messagerie — accepte images + documents (le type exact
    est de toute façon reclassé par `MessageSerializer` pour l'affichage)."""
    validate_file_size(uploaded_file, max_size)
    extension = _extension(uploaded_file.name)
    allowed = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS | {"mp3", "wav", "ogg", "m4a", "mp4", "webm", "mov", "txt", "csv"}
    if extension not in allowed:
        raise ValidationError(f"Format non autorisé — formats acceptés : {', '.join(sorted(allowed))}.")
    if extension in _SIGNATURES:
        _check_signature(uploaded_file, extension)
