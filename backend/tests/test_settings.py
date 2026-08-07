from config.settings import *

# Removemos as apps geográficas que dependem de GDAL para os testes unitários da camada de negócios
INSTALLED_APPS = [
    app for app in INSTALLED_APPS if not app.startswith("django.contrib.gis")
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
