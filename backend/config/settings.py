"""Application configuration for the Hospital Management System."""

import os
from pathlib import Path
from datetime import timedelta

import environ


# ============================================================================
# BASE CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

# Load .env for local development.
# Render environment variables will take precedence in production.
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


# ============================================================================
# SECURITY
# ============================================================================

SECRET_KEY = env(
    "SECRET_KEY",
    default="dev-insecure-secret-key-change-me",
)

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "hospital-management-system-j852.onrender.com",
    ],
)


# ============================================================================
# APPLICATIONS
# ============================================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",

    # Local apps
    "apps.accounts",
    "apps.core",
    "apps.departments",
    "apps.staff",
    "apps.patients",
    "apps.appointments",
    "apps.clinical",
    "apps.laboratory",
    "apps.radiology",
    "apps.pharmacy",
    "apps.inpatient",
    "apps.billing",
    "apps.insurance",
    "apps.inventory",
    "apps.emergency",
]


# ============================================================================
# MIDDLEWARE
# ============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # CORS must be before CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Custom audit middleware
    "apps.core.middleware.AuditMiddleware",
]


# ============================================================================
# URL / WSGI
# ============================================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================================
# TEMPLATES
# ============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
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


# ============================================================================
# DATABASE
# ============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",

        "NAME": env(
            "DB_NAME",
            default="hospital_db",
        ),

        "USER": env(
            "DB_USER",
            default="hms_user",
        ),

        "PASSWORD": env(
            "DB_PASSWORD",
            default="hms_secure_pass_2026",
        ),

        "HOST": env(
            "DB_HOST",
            default="localhost",
        ),

        "PORT": env(
            "DB_PORT",
            default="5432",
        ),
    }
}


# ============================================================================
# CUSTOM USER MODEL
# ============================================================================

AUTH_USER_MODEL = "accounts.User"


# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# ============================================================================
# STATIC / MEDIA FILES
# ============================================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================================
# DJANGO REST FRAMEWORK
# ============================================================================

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

    "DEFAULT_PAGINATION_CLASS": (
        "apps.core.pagination.StandardResultsSetPagination"
    ),

    "PAGE_SIZE": 20,

    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),

    "EXCEPTION_HANDLER": (
        "apps.core.exceptions.api_exception_handler"
    ),
}


# ============================================================================
# SIMPLE JWT
# ============================================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int(
            "JWT_ACCESS_TOKEN_MINUTES",
            default=60,
        )
    ),

    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int(
            "JWT_REFRESH_TOKEN_DAYS",
            default=7,
        )
    ),

    "ROTATE_REFRESH_TOKENS": True,

    "BLACKLIST_AFTER_ROTATION": True,

    "UPDATE_LAST_LOGIN": True,

    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),

    "TOKEN_USER_CLASS": "accounts.User",
}


# ============================================================================
# DRF SPECTACULAR
# ============================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "Hospital Management System API",

    "DESCRIPTION": (
        "REST API for the full-stack "
        "Hospital Management System."
    ),

    "VERSION": "1.0.0",

    "SERVE_INCLUDE_SCHEMA": False,

    "COMPONENT_SPLIT_REQUEST": True,
}


# ============================================================================
# CORS / CSRF
# ============================================================================

# IMPORTANT:
# These are the frontend origins allowed to communicate with Django.
#
# Your current Vercel deployment:
# https://hospital-management-system-k6a7-git-main-caren-m-s-projects.vercel.app
#
# Your previous Vercel deployment:
# https://hospital-management-system-anuh5f08h-caren-m-s-projects.vercel.app

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Vercel deployments
        "https://hospital-management-system-k6a7-git-main-caren-m-s-projects.vercel.app",
        "https://hospital-management-system-anuh5f08h-caren-m-s-projects.vercel.app",
        "https://hospital-management-system-k6a7-7xtfddvqt-caren-m-s-projects.vercel.app",
    ],
)


# CSRF trusted origins.
#
# This is especially useful if you later have Django endpoints
# that use CSRF protection.

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Vercel
        "https://hospital-management-system-k6a7-git-main-caren-m-s-projects.vercel.app",
        "https://hospital-management-system-anuh5f08h-caren-m-s-projects.vercel.app",
        "https://hospital-management-system-k6a7-7xtfddvqt-caren-m-s-projects.vercel.app",
    ],
)


CORS_ALLOW_CREDENTIALS = True


# ============================================================================
# FILE UPLOAD VALIDATION
# ============================================================================

MAX_UPLOAD_SIZE_MB = 10

ALLOWED_DOCUMENT_TYPES = [
    "application/pdf",

    "image/jpeg",
    "image/png",
    "image/webp",

    "application/msword",

    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",

    "text/csv",

    "application/vnd.ms-excel",

    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]


# ============================================================================
# CELERY
# ============================================================================

CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default="redis://localhost:6379/0",
)

CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/0",
)

CELERY_TASK_TRACK_STARTED = True


# ============================================================================
# EMAIL
# ============================================================================

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = env(
    "EMAIL_HOST",
    default="smtp.gmail.com",
)

EMAIL_PORT = env.int(
    "EMAIL_PORT",
    default=587,
)

EMAIL_USE_TLS = env.bool(
    "EMAIL_USE_TLS",
    default=True,
)

EMAIL_USE_SSL = env.bool(
    "EMAIL_USE_SSL",
    default=False,
)

EMAIL_HOST_USER = env(
    "EMAIL_HOST_USER",
    default="",
)

EMAIL_HOST_PASSWORD = env(
    "EMAIL_HOST_PASSWORD",
    default="",
)

DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="no-reply@hospital.local",
)


# ============================================================================
# FRONTEND URL
# ============================================================================

FRONTEND_URL = env(
    "FRONTEND_URL",
    default="http://localhost:5173",
)


# ============================================================================
# LOGIN ATTEMPT PROTECTION
# ============================================================================

MAX_LOGIN_ATTEMPTS = 5

LOCKOUT_MINUTES = 15


# ============================================================================
# SEED ADMIN DEFAULTS
# ============================================================================

SEED_ADMIN_USERNAME = env(
    "SEED_ADMIN_USERNAME",
    default="admin",
)

SEED_ADMIN_EMAIL = env(
    "SEED_ADMIN_EMAIL",
    default="admin@hospital.local",
)

SEED_ADMIN_PASSWORD = env(
    "SEED_ADMIN_PASSWORD",
    default="Admin@12345",
)


# ============================================================================
# PRODUCTION SECURITY
# ============================================================================

# Render serves your application over HTTPS.
# These settings only become active when DEBUG=False.

if not DEBUG:

    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"


# ============================================================================
# LOGGING
# ============================================================================

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },

    "root": {
        "handlers": [
            "console",
        ],
        "level": "INFO",
    },
}