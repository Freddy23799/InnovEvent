"""Chiffrement au repos des messages et pièces jointes (section messagerie).

Le texte et les fichiers ne sont jamais stockés en clair en base ou sur le
disque : ils sont chiffrés symétriquement (Fernet — AES 128 CBC + HMAC) avant
écriture, et déchiffrés uniquement à la volée pour un participant authentifié
de la conversation. Combiné au chiffrement en transit (HTTPS/TLS, déjà en
place), une fuite de la base de données ou du volume de stockage seul ne
suffit pas à lire le contenu des conversations.

Ce n'est PAS un chiffrement de bout en bout façon Signal/WhatsApp : la clé vit
côté serveur (dérivée de SECRET_KEY, ou de MESSAGING_ENCRYPTION_KEY si
configurée séparément), donc le serveur peut toujours déchiffrer — nécessaire
pour l'aperçu de notification et la modération. Un vrai chiffrement de bout
en bout exigerait des clés générées et conservées uniquement sur l'appareil
de chaque utilisateur, jamais sur le serveur.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_fernet() -> Fernet:
    key_material = getattr(settings, "MESSAGING_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(key_material.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_text(plain: str) -> str:
    if not plain:
        return ""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_text(token: str) -> str:
    if not token:
        return ""
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Clé changée ou donnée corrompue — on dégrade proprement plutôt que
        # de faire planter l'affichage de toute la conversation.
        return "⚠ Message illisible"


def encrypt_bytes(data: bytes) -> bytes:
    return _get_fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _get_fernet().decrypt(token)
