import os
from urllib.parse import urlparse, unquote

db_url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
if db_url:
    os.environ["DATABASE_URL"] = db_url

from .settings import *

import sys

# Remove GIS no Windows nativo para evitar crash por falta de bibliotecas GDAL C
if sys.platform == "win32":
    if "django.contrib.gis" in INSTALLED_APPS:
        INSTALLED_APPS.remove("django.contrib.gis")
    if "default" in DATABASES and DATABASES["default"].get("ENGINE") == "django.contrib.gis.db.backends.postgis":
        DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
