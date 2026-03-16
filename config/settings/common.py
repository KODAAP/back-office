from datetime import timedelta
from os import getenv, path
from pathlib import Path

from dotenv import load_dotenv

from config.env import CUR_ENV_FILE

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

APPS_DIR = BASE_DIR / "core_apps"

if path.isfile(CUR_ENV_FILE):
    load_dotenv(CUR_ENV_FILE)


# Application definition

DJANGO_APPS = [
    # "whitenoise.runserver_nostatic",
    "config.settings.custom_app.CustomAdminInterfaceConfig",
    "colorfield",
    "django.contrib.admin",
    "config.settings.custom_app.CustomAuthConfig",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_countries",
    "phonenumber_field",
    "drf_yasg",
    "djoser",
    "corsheaders",
    "social_django",
    "django_filters",
    "djcelery_email",
    "guardian",
    # 'rest_flex_fields',
    # 'django_odata',
    # "django_celery_beat",
]

# Redis cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

LOCAL_APPS = [
    "core_apps.users",
    "core_apps.common",
    "core_apps.profiles",
    "core_apps.odk",
    "core_apps.projects",
    "core_apps.invitations",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
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
        "DIRS": [str(APPS_DIR / "templates")],
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


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": getenv("POSTGRES_DB"),
        "USER": getenv("POSTGRES_USER"),
        "PASSWORD": getenv("POSTGRES_PASSWORD"),
        "HOST": getenv("POSTGRES_HOST"),
        "PORT": getenv("POSTGRES_PORT"),
        "ATOMIC_REQUESTS": True,
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"
#
# LANGUAGES = [
#     ("en", "English"),
#     ("fr", "Français"),
#     ("es", "Español"),
# ]
#
# LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Africa/Lome"

USE_I18N = True

USE_TZ = True

SITE_ID = 1

FILE_UPLOAD_PERMISSIONS = None
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Optionnel : pour éviter les avertissements en production
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


TAGGIT_CASE_INSENSITIVE = True

AUTH_USER_MODEL = "users.User"


if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_URL = getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = getenv("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_RESULT_BACKEND_MAX_RETRIES = 10

CELERY_TASK_SEND_SENT_EVENT = True
CELERY_RESULT_EXTENDED = True

CELERY_RESULT_BACKEND_ALWAYS_RETRY = True

CELERY_TASK_TIME_LIMIT = 5 * 60

CELERY_TASK_SOFT_TIME_LIMIT = 60

# CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_WORKER_SEND_TASK_EVENTS = True

# CELERY_BEAT_SCHEDULE = {
#     # "update-reputations-every-day": {
#     #     "task": "update_all_reputations",
#     # }
# }

COOKIE_NAME = "access"
COOKIE_SAMESITE = "Lax"
COOKIE_PATH = "/"
COOKIE_HTTPONLY = True
COOKIE_SECURE = getenv("COOKIE_SECURE", "True") == "True"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "core_apps.common.cookie_auth.CookieAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "PAGE_SIZE": 10,
    "PAGE_SIZE_QUERY_PARAM": "page_size",  # Permet de personnaliser la taille
    "MAX_PAGE_SIZE": 100,  # Limite maximum
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "2000/day",
        "user": "200000/day",
    },
    # 'DEFAULT_RENDERER_CLASSES': [
    #     'core_apps.common.renderers.GenericJSONRenderer',
    #     'rest_framework.renderers.BrowsableAPIRenderer',  # Optional for development
    # ],
}

SIMPLE_JWT = {
    "SIGNING_KEY": getenv("SIGNING_KEY"),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=3600),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

DJOSER = {
    "USER_ID_FIELD": "id",
    "LOGIN_FIELD": "email",
    "TOKEN_MODEL": None,
    "USER_CREATE_PASSWORD_RETYPE": True,
    "SEND_ACTIVATION_EMAIL": True,
    "PASSWORD_CHANGED_EMAIL_CONFIRMATION": True,
    "PASSWORD_RESET_CONFIRM_RETYPE": True,
    "ACTIVATION_URL": "activate/{uid}/{token}",
    "PASSWORD_RESET_CONFIRM_URL": "password-reset/{uid}/{token}",
    "SOCIAL_AUTH_ALLOWED_REDIRECT_URIS": getenv("REDIRECT_URIS", "").split(","),
    "SERIALIZERS": {
        "user_create": "core_apps.users.serializers.CreateUserSerializer",
        "current_user": "core_apps.users.serializers.CustomUserSerializer",
    },
}

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = getenv("GOOGLE_CLIENT_ID")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = getenv("GOOGLE_CLIENT_SECRET")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]
SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_DATA = ["first_name", "last_name"]

SOCIAL_AUTH_PIPELINE = [
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "core_apps.profiles.pipeline.save_profile",
]

AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]
# Google Drive settings
GOOGLE_SERVICE_ACCOUNT_FILE = path.join(
    BASE_DIR, "credentials", "sycosur2-0-68f9e20fe81e.json"
)
GOOGLE_DRIVE_FOLDER_ID = getenv("GOOGLE_DRIVE_FOLDER_ID")
# DEFAULT_FILE_STORAGE = "core_apps.common.drive_storage.GoogleDriveStorage"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = BASE_DIR / "media"  # Directory for uploaded files
MEDIA_URL = "/media/"
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "."

# ODK account settings
ODK_ADMIN_EMAIL = "admin@insuco.com"
ODK_ADMIN_PASSWORD = "INSUCO2520"

ODK_ADMIN_EMAIL2 = getenv("ODK_ADMIN_EMAIL2")
ODK_ADMIN_PASSWORD2 = getenv("ODK_ADMIN_PASSWORD2")

# Guardian settings
ANONYMOUS_USER_NAME = "AnonymousUser"
GUARDIAN_RENDER_403 = True  # Page d'erreur personnalisable

# DJANGO_ODATA = {
#     'SERVICE_ROOT': '/odata/',  # Base URL for OData endpoints
#     'MAX_PAGE_SIZE': 1000,     # Prevent overload
#     'DEFAULT_PAGE_SIZE': 50,
#     'ENABLE_METADATA': True,   # Expose $metadata endpoint
#     'ENABLE_SERVICE_DOCUMENT': True,  # Expose service document
# }

# Invitation settings
FRONTEND_URL = getenv("FRONTEND_URL", "http://localhost:8080")
