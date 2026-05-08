from .common import *

DEBUG = False


SECRET_KEY = getenv(
    "DJANGO_SECRET_KEY", "UUc-qwrxzkZFyx4mrxXFfgHpA1VLOIuAojmk8T9q7n35A6-k-yM"
)
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY must be set in the environment.")

CSRF_TRUSTED_ORIGINS = [
    "https://sycosur.insuco.net",
    "https://www.sycosur.insuco.net",
    "https://insuco.com",
]


ALLOWED_HOSTS = [".insuco.net"]

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://sycosur.insuco.net",
    "https://drive.google.com",
    "https://googleusercontent.com",
    "https://flower.insuco.net",
    "https://insuco.com",
]
# CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]


SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Security settings

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

ADMIN_URL = getenv("DJANGO_ADMIN_URL")
EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = getenv("EMAIL_HOST")
EMAIL_PORT = getenv("EMAIL_PORT")
DEFAULT_FROM_EMAIL = getenv("DEFAULT_FROM_EMAIL", "sycosur@insuco.com")
SITE_NAME = getenv("SITE_NAME", "Sycosur2")
if SITE_NAME and "<" not in DEFAULT_FROM_EMAIL:
    DEFAULT_FROM_EMAIL = f"{SITE_NAME} <{DEFAULT_FROM_EMAIL}>"
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_HOST_USER = getenv("DEFAULT_FROM_EMAIL", "sycosur@insuco.com")
EMAIL_HOST_PASSWORD = getenv("EMAIL_PASS")
DOMAIN = getenv("DOMAIN")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "mail_admins": {  # Envoi des erreurs par email aux administrateurs
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {  # Logging dans la console
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.request": {  # Gestion des erreurs de requêtes
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security.DisallowedHost": {  # Gestion des tentatives d'accès non autorisées
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}


ENKETO_ENCRYPTION_KEY = getenv("ENKETO_ENCRYPTION_KEY")
ENKETO_LESS_SECURE_ENCRYPTION_KEY = getenv("ENKETO_LESS_SECURE_ENCRYPTION_KEY")

if (
    not ENKETO_API_KEY
    or not ENKETO_ENCRYPTION_KEY
    or not ENKETO_LESS_SECURE_ENCRYPTION_KEY
):
    raise ValueError(
        "ENKETO_API_KEY, ENKETO_ENCRYPTION_KEY, and ENKETO_LESS_SECURE_ENCRYPTION_KEY must be \
        set in production environment variables."
    )
