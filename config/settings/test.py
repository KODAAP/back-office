from .common import *
from .local import ADMIN_URL

# Désactivation du mode debug pour les tests
DEBUG = False

# Clé secrète de secours si non définie dans l'environnement
SECRET_KEY = getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-test-key-only-for-ci-and-testing-purposes",
)

# Configuration de la base PostgreSQL de test
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": getenv("POSTGRES_DB", "test_kodaap"),
        "USER": getenv("POSTGRES_USER", "test_user"),
        "PASSWORD": getenv("POSTGRES_PASSWORD", "test_pass"),
        "HOST": getenv("POSTGRES_HOST", "localhost"),
        "PORT": getenv("POSTGRES_PORT", "5432"),
    }
}

# Algorithme de hachage ultra-rapide pour accélérer l'exécution des tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Capturer les emails en mémoire au lieu d'essayer d'enoyer de vrais courriels
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ADMIN_URL = ADMIN_URL
