from .common import *

DEBUG = True

SITE_NAME = getenv("SITE_NAME")

SECRET_KEY = getenv(
    "DJANGO_SECRET_KEY", "UUc-qwrxzkZFyx4mrxXFfgHpA1VLOIuAojmk8T9q7n35A6-k-yM"
)

CSRF_TRUSTED_ORIGINS = ["http://localhost:8080"]


ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True  # TODO change this to False in production
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5555",
    "http://127.0.0.1:5555",
    "http://localhost:8025",
    "http://127.0.0.1:8025",
    "https://drive.google.com",
    "https://googleusercontent.com",
    "https://odk.insuco.net",
]

ADMIN_URL = getenv("DJANGO_ADMIN_URL")
EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = getenv("EMAIL_HOST")
EMAIL_PORT = getenv("EMAIL_PORT")
DEFAULT_FROM_EMAIL = getenv("DEFAULT_FROM_EMAIL")
DOMAIN = getenv("DOMAIN")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(name)-12s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}
