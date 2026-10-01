"""Signature des QR codes de billets (section 9 du CDC).

Le contenu encodé est signé côté serveur (django.core.signing) : un QR falsifié
ou copié depuis un autre billet ne peut pas passer la vérification de signature.
La génération de l'image QR elle-même est mutualisée dans apps.documents.qr_utils.
"""

from django.conf import settings
from django.core import signing

from apps.documents.qr_utils import build_qr_image, build_qr_png_bytes  # noqa: F401 (ré-exporté)

SALT = "innovevent.ticket.qr"


def _signing_key() -> str:
    # Clé dédiée (QR_SIGNING_SECRET), distincte de SECRET_KEY : une rotation de
    # SECRET_KEY (JWT, sessions...) n'invalide pas les QR codes déjà imprimés/
    # téléchargés par les participants, et inversement.
    return getattr(settings, "QR_SIGNING_SECRET", None) or settings.SECRET_KEY


def sign_ticket_code(code) -> str:
    return signing.dumps({"ticket_code": str(code)}, salt=SALT, key=_signing_key())


def verify_ticket_token(token: str, max_age_seconds=None):
    """Renvoie le code de billet si la signature est valide, sinon None."""
    try:
        payload = signing.loads(token, salt=SALT, max_age=max_age_seconds, key=_signing_key())
    except signing.BadSignature:
        return None
    return payload.get("ticket_code")
