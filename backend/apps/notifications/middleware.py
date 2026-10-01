from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user_from_token(token):
    from apps.accounts.models import User

    try:
        validated = AccessToken(token)
        return User.objects.get(pk=validated["user_id"])
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware:
    """Authentifie la connexion WebSocket avec le même JWT que l'API REST
    (l'application n'utilise pas l'authentification par session Django).

    Le token est transmis en query string, ex: /ws/notifications/?token=...,
    car les en-têtes personnalisés ne sont pas disponibles pour l'API WebSocket
    du navigateur.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)
