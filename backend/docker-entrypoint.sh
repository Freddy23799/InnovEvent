#!/bin/sh
set -e

echo "En attente de PostgreSQL..."
until python -c "
import os, sys, psycopg2
try:
    psycopg2.connect(
        dbname=os.environ.get('POSTGRES_DB', 'innovevent'),
        user=os.environ.get('POSTGRES_USER', 'innovevent'),
        password=os.environ.get('POSTGRES_PASSWORD', ''),
        host=os.environ.get('POSTGRES_HOST', 'db'),
        port=os.environ.get('POSTGRES_PORT', '5432'),
    )
except Exception:
    sys.exit(1)
"; do
  sleep 1
done

python manage.py migrate --noinput
python manage.py ensure_initial_admin
python manage.py seed_landing_media /opt/innovevent-seed/acceuil --if-empty
# Initialise les paliers et fonctionnalités Marketplace dans les bases neuves.
# La commande est idempotente et ne remplace pas les réglages existants.
python manage.py seed_marketplace_features
python manage.py collectstatic --noinput

# Daphne (ASGI) plutôt que gunicorn (WSGI) : un seul processus sert à la fois
# l'API REST classique et les WebSocket temps réel (apps/notifications).
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
