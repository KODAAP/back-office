import environ

from .common import *  # Récupère toute la configuration principale

env = environ.Env()

DEBUG = False
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-test-key-only-for-ci-and-testing-purposes",
)

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://test_user:test_pass@localhost:5432/test_kodaap",
    )
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
