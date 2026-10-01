def log_action(actor=None, action="", metadata=None, ip_address=None, method="", path="", status_code=None):
    """Point d'entrée unique pour journaliser une action métier sensible.

    Import différé du modèle pour éviter les imports circulaires au chargement
    des apps (accounts, tickets, payments, etc. appellent cette fonction).
    """
    from .models import AuditLog

    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        method=method,
        path=path,
        status_code=status_code,
        ip_address=ip_address,
        metadata=metadata or {},
    )


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
