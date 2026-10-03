FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libzbar0 libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app

# Photothèque réelle prévue pour la vitrine. Elle est importée au premier
# démarrage uniquement si la table LandingMedia est vide (voir entrypoint).
COPY --chown=appuser:appuser frontend/acceuil /opt/innovevent-seed/acceuil
USER appuser

EXPOSE 8000

COPY --chown=appuser:appuser backend/docker-entrypoint.sh /app/docker-entrypoint.sh

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
