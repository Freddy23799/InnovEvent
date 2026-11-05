import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Génère une paire de clés VAPID pour les notifications Web Push (à copier dans backend/.env)."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        raw_private = private_key.private_numbers().private_value.to_bytes(32, "big")
        raw_public = private_key.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint,
        )
        self.stdout.write(f"WEBPUSH_VAPID_PUBLIC_KEY={_b64url(raw_public)}")
        self.stdout.write(f"WEBPUSH_VAPID_PRIVATE_KEY={_b64url(raw_private)}")
