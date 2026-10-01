from django.utils import timezone

UPDATE_INTERVAL_SECONDS = 60


class TrackLastSeenMiddleware:
    """Met à jour `User.last_seen` pour la présence en ligne, avec un débit limité
    (une écriture par minute maximum par utilisateur) pour ne pas surcharger la base."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            now = timezone.now()
            if not user.last_seen or (now - user.last_seen).total_seconds() > UPDATE_INTERVAL_SECONDS:
                user.__class__.objects.filter(pk=user.pk).update(last_seen=now)
        return response
