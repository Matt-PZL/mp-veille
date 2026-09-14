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
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "apps.api",
    "apps.bdp",
    "apps.bdc",
    "apps.catalogue",
    "apps.matching",
    "apps.ingestion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# Le panel vit desormais dans le front Next.js, qui gere sa propre page de
# connexion via /api/auth/. Ne reste cote Django que l'admin, qui a sa propre
# page de connexion — LOGIN_URL n'y sert que de repli.
LOGIN_URL = "/admin/login/"

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

# --- Front Next.js ---
# Le front tourne sur son propre port et s'authentifie par cookie de session :
# CORS doit autoriser les identifiants, et l'origine doit etre listee
# explicitement (un "*" est refuse des qu'on envoie des cookies).
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# Chrome/Edge recents bloquent silencieusement (ERR_BLOCKED_BY_CLIENT) toute
# requete JS depuis une page vers une IP privee (Private Network Access),
# sauf si le serveur repond explicitement qu il l autorise. Notre front et
# notre API tournent tous deux sur le LAN (192.168.1.x) : sans ce flag, la
# verification de session ("/auth/moi") echoue en boucle sans jamais lever
# d erreur visible cote reseau.
CORS_ALLOW_PRIVATE_NETWORK = True

# Le front lit le cookie CSRF en JS pour le renvoyer en en-tete : il ne peut
# donc pas etre httpOnly. Le cookie de SESSION, lui, le reste.
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000",
    cast=Csv(),
)
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- Statiques servis par WhiteNoise ---
# Evite d'exiger un nginx devant Django juste pour l'admin et les gabarits.
# En DEBUG, Django sert les statiques lui-meme et WhiteNoise ne gene pas.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Durcissement, actif uniquement hors DEBUG ---
# Ces reglages supposent un reverse proxy en HTTPS devant l'application.
# Sans HTTPS, SECURE_SSL_REDIRECT boucle : laisser DJANGO_HTTPS a 0 tant que
# le certificat n'est pas en place.
if not DEBUG:
    _https = config("DJANGO_HTTPS", default=False, cast=bool)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _https
    SESSION_COOKIE_SECURE = _https
    CSRF_COOKIE_SECURE = _https
    SECURE_HSTS_SECONDS = 31536000 if _https else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _https
    SECURE_HSTS_PRELOAD = _https
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# --- Chiffrement BDC ---
# Cle Fernet dediee aux champs sensibles de la BDC (justificatifs, commentaires...).
# Le Matching ne lit jamais ces champs : il ne travaille que sur des identifiants
# de taxonomie et de statut, non sensibles. Voir apps/bdc/fields.py.
BDC_ENCRYPTION_KEY = config("BDC_ENCRYPTION_KEY")

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://192.168.1.24:3000",
    cast=Csv(),
)

# --- Journalisation de l'ingestion ---
# Avant ceci, les echecs (reseau, parsing) dans apps/ingestion/tasks.py
# etaient avales en silence : impossible de diagnostiquer une baisse de
# collecte sans ca. INFO -> visible via 'docker compose logs worker'.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'ingestion': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
