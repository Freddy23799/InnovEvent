import json
import logging
import re
from datetime import timedelta
from functools import wraps

from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from .models import IdempotencyRecord

logger = logging.getLogger(__name__)

KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
# Au-delà, une demande restée « en cours » est considérée comme interrompue
# (processus arrêté pendant l'appel à la passerelle) et peut être rejouée.
STALE_AFTER = timedelta(minutes=2)
# Les réponses rejouables sont conservées un jour : bien plus que le temps
# d'un nouvel essai après une coupure réseau.
RETENTION = timedelta(days=1)


def idempotent_payment(view_method):
    """Décorateur pour les actions de paiement (méthodes de vue DRF).

    - même clé, paiement terminé : la réponse d'origine est renvoyée telle
      quelle (en-tête `Idempotent-Replayed: true`), rien n'est encaissé ;
    - même clé, paiement encore en cours : 409, le client patiente ;
    - échec (réponse non 2xx ou exception) : la clé est libérée pour
      permettre un nouvel essai avec la même clé.
    Sans clé (anciens clients), la vue s'exécute normalement.
    """

    @wraps(view_method)
    def wrapper(self, request, *args, **kwargs):
        key = (request.headers.get("Idempotency-Key") or "").strip()
        if not key or not request.user.is_authenticated:
            return view_method(self, request, *args, **kwargs)
        if not KEY_PATTERN.match(key):
            return Response({"detail": "Clé de paiement invalide. Rechargez la page puis réessayez."}, status=status.HTTP_400_BAD_REQUEST)

        scope = f"{request.method} {request.path}"[:200]
        record = _reserve(request.user, key, scope)
        if isinstance(record, Response):
            return record

        try:
            response = view_method(self, request, *args, **kwargs)
        except Exception:
            record.delete()
            raise

        if 200 <= response.status_code < 300 and hasattr(response, "data"):
            record.status_code = response.status_code
            record.response = json.loads(json.dumps(response.data, cls=DjangoJSONEncoder))
            record.save(update_fields=["status_code", "response"])
        else:
            record.delete()
        return response

    return wrapper


def _reserve(user, key, scope):
    """Crée l'enregistrement « en cours », ou renvoie la réponse à rejouer."""
    IdempotencyRecord.objects.filter(user=user, created_at__lt=timezone.now() - RETENTION).delete()
    try:
        with transaction.atomic():
            return IdempotencyRecord.objects.create(user=user, key=key, scope=scope)
    except IntegrityError:
        pass

    existing = IdempotencyRecord.objects.filter(user=user, key=key).first()
    if existing is None:
        # Supprimé entre-temps (échec du premier essai) : on retente une fois.
        try:
            with transaction.atomic():
                return IdempotencyRecord.objects.create(user=user, key=key, scope=scope)
        except IntegrityError:
            return _in_progress()
    if existing.scope != scope:
        return Response(
            {"detail": "Cette clé de paiement a déjà servi pour une autre opération. Rechargez la page."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if existing.status_code is None:
        if existing.created_at < timezone.now() - STALE_AFTER:
            logger.warning("Paiement interrompu détecté (clé %s, utilisateur %s) : nouvel essai autorisé.", key, user.pk)
            existing.created_at = timezone.now()
            existing.save(update_fields=["created_at"])
            return existing
        return _in_progress()

    response = Response(existing.response, status=existing.status_code)
    response["Idempotent-Replayed"] = "true"
    return response


def _in_progress():
    return Response(
        {"detail": "Ce paiement est déjà en cours de traitement. Patientez quelques secondes, il ne sera pas débité deux fois."},
        status=status.HTTP_409_CONFLICT,
    )
