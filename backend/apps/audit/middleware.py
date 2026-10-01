from .utils import get_client_ip, log_action

SENSITIVE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditLogMiddleware:
    """Journalise automatiquement toute requête API qui modifie des données.

    Complète les appels explicites à `log_action` (auth, paiements, QR) par une
    traçabilité systématique des écritures, sans avoir à l'ajouter vue par vue.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and request.method in SENSITIVE_METHODS:
            log_action(
                actor=getattr(request, "user", None),
                action=f"{request.method} {request.path}",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                ip_address=get_client_ip(request),
            )
        return response
