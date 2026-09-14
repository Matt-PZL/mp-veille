from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "django_celery_beat",
    "django_celery_results",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.accounts",
    "apps.vitrine",
    "apps.bdp",
    "apps.bdc",
    "apps.catalogue",
    "apps.matching",
    "apps.ingestion",
    "apps.panel",
    "apps.api",
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
    "django_htmx.middleware.HtmxMiddleware",
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

# --- Base de donnees ---
# Postgre unique au niveau infra : la separation logique BDP / BDC se fait par
# app (apps.bdp / apps.bdc), pas par base physique, pour rester simple en V1.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST", default="db"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Preuves de traitement (fichiers uploades a la cloture) — donnee BDC.
# Pas chiffre au niveau stockage pour ce POC (limite connue, a traiter en V2 :
# storage applicatif chiffre, contrairement aux champs texte deja chiffres).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 Mo

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "panel:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# --- Celery ---
CELERY_BROKER_URL = config("REDIS_URL")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Cycle d'ingestion automatique (brief section 2 : boucle ~12h).
CELERY_BEAT_SCHEDULE = {
    "cycle-ingestion-12h": {
        "task": "apps.ingestion.tasks.cycle_ingestion",
        "schedule": crontab(hour="*/12", minute=0),
    },
}

# --- Chiffrement BDC ---
# Cle Fernet dediee aux champs sensibles de la BDC (justificatifs, commentaires...).
# Le Matching ne lit jamais ces champs : il ne travaille que sur des identifiants
# de taxonomie et de statut, non sensibles. Voir apps/bdc/fields.py.
BDC_ENCRYPTION_KEY = config("BDC_ENCRYPTION_KEY")

# --- API (apps.api) : couche REST/JWT pour le frontend Next.js -------------
# Coexiste avec les vues Django historiques (apps.panel) pendant la migration
# progressive — les deux interfaces lisent les memes modeles/regles metier.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
}

# Origines autorisees a appeler l'API en cross-origin : le serveur de dev
# Next.js (localhost:3000) et la VM elle-meme quand le frontend y est deploye.
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://192.168.1.24:3000",
    cast=Csv(),
)
