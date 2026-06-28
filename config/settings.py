"""
Django settings for config project.
Configuração otimizada para integração com Supabase (PostGIS) e Celery.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-development-key-only")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# Application definition
INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Engine Espacial Obrigatório para as GeoQueries (Store, Driver, Stop, etc)
    "django.contrib.gis",
    # Módulos Core do Expresso Neves
    "accounts.apps.AccountsConfig",
    "logistics.apps.LogisticsConfig",
    "finance.apps.FinanceConfig",
    "integration.apps.IntegrationConfig",
    "todos.apps.TodosConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Middleware de Isolamento RLS nativo
    "config.middleware.SupabaseRLSMiddleware",
]

ROOT_URLCONF = "config.urls"

CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-user-role",
]

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

import sys
from urllib.parse import urlparse, unquote

# Usa DATABASE_URL para conexão normal
db_url = os.environ.get("DATABASE_URL")
if db_url:
    url = urlparse(db_url)
    # Remove o slash inicial do path
    db_name = url.path[1:] if url.path else ""
    db_user = url.username or ""
    db_password = unquote(url.password) if url.password else ""
    db_host = url.hostname or ""
    db_port = str(url.port) if url.port else "5432"

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "CONN_MAX_AGE": 600,
        }
    }
else:
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("DATABASE_URL environment variable is missing in production!")

    # Fallback para ambiente de desenvolvimento local (ex: Supabase CLI)
    DATABASES = {
        "default": {
            "ENGINE": os.environ.get(
                "SUPABASE_DB_ENGINE", "django.contrib.gis.db.backends.postgis"
            ),
            "NAME": os.environ.get("SUPABASE_DB_NAME", "postgres"),
            "USER": os.environ.get("SUPABASE_DB_USER", "postgres"),
            "PASSWORD": os.environ.get("SUPABASE_DB_PASSWORD", "postgres"),
            "HOST": os.environ.get("SUPABASE_DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("SUPABASE_DB_PORT", "54322"),
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }

# Password validation
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
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if sys.platform == "win32":
    # Desabilita o GIS no Windows nativo para evitar crash por falta de GDAL
    if "django.contrib.gis" in INSTALLED_APPS:
        INSTALLED_APPS.remove("django.contrib.gis")
    if DATABASES["default"]["ENGINE"] == "django.contrib.gis.db.backends.postgis":
        DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==========================================
# Celery (Redis)
# ==========================================
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# ==========================================
# Produção Hardening & Observabilidade
# ==========================================
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "INFO"),
        },
    }
