"""Django settings for backend-api."""

import os
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = SERVICE_DIR


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-local-fb-api-change-me",
)
DEBUG = env_bool("DEBUG", default=True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "applications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ProjectConfig.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ProjectConfig.wsgi.application"

if os.getenv("POSTGRES_HOST") or os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "NAME": os.getenv("POSTGRES_DB", "fb_api_db"),
            "USER": os.getenv("POSTGRES_USER", "fb_api_user"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "fb_api_password"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Ho_Chi_Minh")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FACEBOOK_GRAPH_VERSION = os.getenv("FACEBOOK_GRAPH_VERSION", "v20.0")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
FACEBOOK_API_MODE = os.getenv("FACEBOOK_API_MODE", "mock")
FACEBOOK_REQUEST_TIMEOUT_SECONDS = float(os.getenv("FACEBOOK_REQUEST_TIMEOUT_SECONDS", "10"))

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_ENABLED = env_bool("KAFKA_ENABLED", default=True)
KAFKA_REPLY_COMMANDS_TOPIC = os.getenv("KAFKA_REPLY_COMMANDS_TOPIC", "reply_commands")
KAFKA_SEND_RETRY_TOPIC = os.getenv("KAFKA_SEND_RETRY_TOPIC", "send_retry")
KAFKA_SEND_FAILED_TOPIC = os.getenv("KAFKA_SEND_FAILED_TOPIC", "send_failed")

DASHBOARD_API_TOKEN = os.getenv("DASHBOARD_API_TOKEN", "")

FACEBOOK_CIRCUIT_FAILURE_THRESHOLD = int(os.getenv("FACEBOOK_CIRCUIT_FAILURE_THRESHOLD", "5"))
FACEBOOK_CIRCUIT_RECOVERY_SECONDS = int(os.getenv("FACEBOOK_CIRCUIT_RECOVERY_SECONDS", "30"))
