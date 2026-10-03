"""
Configuration Django pour InnovEvent-GS.

Choix documentés :
- Tous les secrets sont lus depuis les variables d'environnement (jamais en dur),
  conformément à la section 15 du CDC.
- Redis sert à la fois de cache par défaut et de backend de rate limiting (django-ratelimit
  ou throttling DRF s'appuient sur ce même cache).
- SimpleJWT fournit access + refresh token conformément à la section 5 du CDC.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Dev only, jamais utilisé si DJANGO_DEBUG=False : évite de bloquer un
        # premier clonage local sans .env, sans jamais laisser filer un secret
        # connu/prévisible en production (voir la levée d'erreur ci-dessous).
        SECRET_KEY = "django-insecure-local-dev-only-set-DJANGO_SECRET_KEY-in-env"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY doit être défini (variable d'environnement) dès que DJANGO_DEBUG=False."
        )

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "daphne",  # doit précéder staticfiles : fournit la commande runserver ASGI
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tiers
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "channels",
    # Applications métier (voir section 3 du CDC)
    "apps.accounts",
    "apps.events",
    "apps.venues",
    "apps.providers",
    "apps.equipment",
    "apps.bookings",
    "apps.tickets",
    "apps.payments",
    "apps.messaging",
    "apps.ai_assistant",
    "apps.training",
    "apps.employees",
    "apps.payroll",
    "apps.notifications",
    "apps.documents",
    "apps.audit",
    "apps.reviews",
    "apps.games",
    "apps.public",
    "apps.marketplace",
    "apps.deliveries",
    "apps.referrals",
    "apps.companies",
    "apps.talents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditLogMiddleware",
    "apps.accounts.middleware.TrackLastSeenMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "innovevent"),
        "USER": os.environ.get("POSTGRES_USER", "innovevent"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

STATIC_URL = os.environ.get("STATIC_URL", "/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
# En Docker, le volume `backend_media` est monté sur ce dossier. Sur cPanel,
# MEDIA_ROOT peut pointer vers un dossier persistant du compte d'hébergement ;
# le serveur web (Apache/Passenger) doit publier MEDIA_URL vers ce dossier.
# Les barres initiales garantissent que les URLs retournées par l'API sont
# absolues (`/media/...`) et non relatives à une route `/api/...`.
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Limites d'upload (aucune n'était définie : les valeurs par défaut de
# Django, 2.5 Mo, ne s'appliquent qu'au tamponnage en mémoire, pas à un rejet
# effectif des fichiers volumineux) — plafond explicite appliqué à toute
# requête/upload, en complément des validateurs de fichiers par app. -------
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024  # 15 Mo (corps de requête, hors fichiers)
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024))  # 10 Mo par fichier

# --- Cache / Redis (session courte durée, rate limiting) --------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# --- Notifications temps réel (WebSocket / Django Channels) -----------------
# Même instance Redis que le cache : un canal par utilisateur, alimenté par
# apps.notifications.services.notify_user à chaque notification créée.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    },
}

# --- Django REST Framework ---------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "auth": "10/minute",
        "ticket_purchase": "20/minute",
        "qr_scan": "60/minute",
        "payment_webhook": "30/minute",
        "coupon_validate": "20/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.accounts.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "InnovEvent-GS API",
    "DESCRIPTION": "API REST de la plateforme de gestion événementielle InnovEvent-GS.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", 15))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_LIFETIME_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]

# --- Emails transactionnels --------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@innovevent.example")
# Sans timeout explicite, smtplib attend indéfiniment si le serveur SMTP est
# injoignable — ce qui bloquerait la requête HTTP entière (ex. création d'une
# réservation) tant que la connexion n'échoue pas. Le code appelant capture déjà
# les erreurs d'envoi (voir EmailLog) ; ce timeout garantit juste qu'elles
# surviennent vite plutôt que de faire pendre la requête.
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", 10))
if DEBUG and not EMAIL_HOST_PASSWORD:
    # Sans identifiants SMTP réels, on affiche les emails dans les logs plutôt que
    # d'échouer silencieusement ; dès qu'un mot de passe SMTP est fourni (même en
    # DEBUG), il est réellement utilisé pour l'envoi.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- Paiements & IA (secrets, jamais exposés au frontend) -------------------
PAYMENTS_DEMO_MODE = os.environ.get("PAYMENTS_DEMO_MODE", "True") == "True"
# Secret partagé attendu sur chaque webhook entrant (en-tête X-Webhook-Secret) —
# faute d'un identifiant marchand réel par fournisseur pour l'instant, c'est le
# seul moyen de s'assurer qu'un appel provient bien du serveur de paiement et
# non d'un tiers qui aurait deviné/obtenu une `transaction_ref`. À remplacer par
# la vérification de signature propre à chaque fournisseur dès que ses secrets
# de webhook réels sont fournis.
PAYMENT_WEBHOOK_SECRET = os.environ.get("PAYMENT_WEBHOOK_SECRET", "")
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
FREEMOPAY_API_KEY = os.environ.get("FREEMOPAY_API_KEY", "")
KOB_API_KEY = os.environ.get("KOB_API_KEY", "")
SUPPORTED_CURRENCIES = ["XAF", "EUR", "USD", "GBP"]

# Abonnement Premium Marketplace (section « marketplaces premium ») : le tarif
# et la durée de chaque formule sont définis côté serveur — jamais acceptés
# depuis le frontend — mais l'abonné choisit lui-même la formule (mensuelle ou
# annuelle) au moment de s'abonner.
PREMIUM_SUBSCRIPTION_PRICE_XAF = int(os.environ.get("PREMIUM_SUBSCRIPTION_PRICE_XAF", 15000))
PREMIUM_SUBSCRIPTION_DURATION_DAYS = int(os.environ.get("PREMIUM_SUBSCRIPTION_DURATION_DAYS", 30))
PREMIUM_SUBSCRIPTION_YEARLY_PRICE_XAF = int(os.environ.get("PREMIUM_SUBSCRIPTION_YEARLY_PRICE_XAF", 150000))
PREMIUM_SUBSCRIPTION_YEARLY_DURATION_DAYS = int(os.environ.get("PREMIUM_SUBSCRIPTION_YEARLY_DURATION_DAYS", 365))

AI_PROVIDER = os.environ.get("AI_PROVIDER", "demo")
AI_PROVIDER_API_KEY = os.environ.get("AI_PROVIDER_API_KEY", "")
AI_PROVIDER_BASE_URL = os.environ.get("AI_PROVIDER_BASE_URL", "https://api.openai.com/v1")
AI_PROVIDER_MODEL = os.environ.get("AI_PROVIDER_MODEL", "gpt-4o-mini")

QR_SIGNING_SECRET = os.environ.get("QR_SIGNING_SECRET", SECRET_KEY)

# Clé dédiée au chiffrement des messages (apps.messaging.crypto) — distincte de
# SECRET_KEY afin qu'une rotation de SECRET_KEY (JWT, sessions, tokens signés)
# n'invalide jamais le contenu déjà chiffré des conversations. Si absente, le
# code applicatif se replie sur SECRET_KEY (comportement historique).
MESSAGING_ENCRYPTION_KEY = os.environ.get("MESSAGING_ENCRYPTION_KEY", "")

# --- Connexion sociale (section hors CDC, ajoutée à la demande) -------------
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")

# --- SMS (mode démonstration par défaut ; Twilio nécessite des identifiants réels) ---
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "demo")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS : absent jusqu'ici (aucun en-tête Strict-Transport-Security n'était
    # jamais envoyé, même en production) — activé uniquement hors DEBUG, une
    # fois HTTPS réellement en place devant l'application (reverse proxy).
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
