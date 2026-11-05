"""Envoi des notifications Web Push (VAPID) aux appareils abonnés.

Best-effort et hors du cycle de la requête : l'envoi part dans un thread
après validation de la transaction, pour ne jamais ralentir ni faire
échouer l'action métier (message, commande, réservation…). Les abonnements
expirés (404/410 renvoyés par le service push du navigateur) sont supprimés.
"""

import json
import logging
import threading

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def is_configured():
    return bool(getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", "") and getattr(settings, "WEBPUSH_VAPID_PRIVATE_KEY", ""))


def _send_now(user_id, payload):
    from pywebpush import WebPushException, webpush

    from .models import PushSubscription

    close_old_connections()
    try:
        for subscription in PushSubscription.objects.filter(user_id=user_id):
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                    },
                    data=json.dumps(payload),
                    vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.WEBPUSH_VAPID_SUBJECT},
                    ttl=60 * 60 * 24,
                    timeout=10,
                )
                PushSubscription.objects.filter(pk=subscription.pk).update(last_success_at=timezone.now())
            except WebPushException as exc:
                status = getattr(exc.response, "status_code", None)
                if status in (404, 410):
                    subscription.delete()
                else:
                    logger.warning("Web Push refusé pour %s : %s", subscription.pk, exc)
            except Exception:
                logger.warning("Web Push impossible pour %s.", subscription.pk, exc_info=True)
    finally:
        close_old_connections()


def send_web_push(notification):
    """Pousse la notification sur tous les appareils de son destinataire."""
    if not is_configured():
        return
    from .models import Notification

    payload = {
        "id": notification.id,
        "title": notification.title,
        "body": notification.message,
        "link": notification.link or "/app",
        "tag": f"notification-{notification.id}",
        # Compteur affiché sur l'icône de l'application (non lues).
        "unread_count": Notification.objects.filter(recipient_id=notification.recipient_id, is_read=False).count(),
    }
    user_id = notification.recipient_id

    def start():
        threading.Thread(target=_send_now, args=(user_id, payload), daemon=True).start()

    transaction.on_commit(start)
