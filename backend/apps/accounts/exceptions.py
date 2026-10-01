"""Gestion d'erreurs centralisée pour l'API (section 30 du CDC) : toute exception
DRF renvoie une enveloppe JSON cohérente, sans jamais divulguer de trace interne."""

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "detail": response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data,
            "errors": response.data if isinstance(response.data, dict) else None,
            "status_code": response.status_code,
        }
    return response
