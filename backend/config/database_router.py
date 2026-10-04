"""Routage PostgreSQL primaire/réplica, activé via POSTGRES_REPLICA_HOST."""

from django.conf import settings
from django.db import connections


class PrimaryReplicaRouter:
    """Envoie les lectures vers la réplique et garde les écritures au primaire.

    Django reste sur le primaire pendant une transaction pour préserver les
    lectures cohérentes immédiatement après une écriture. Une réplique en
    streaming peut néanmoins avoir un léger retard hors transaction.
    """

    def db_for_read(self, model, **hints):
        if "replica" not in settings.DATABASES:
            return "default"
        if connections["default"].in_atomic_block:
            return "default"
        return "replica"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db and obj2._state.db:
            return obj1._state.db == obj2._state.db or {obj1._state.db, obj2._state.db} <= {"default", "replica"}
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
