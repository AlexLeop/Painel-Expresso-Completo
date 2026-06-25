import os
from urllib.parse import urlparse, unquote

db_url = os.environ.get('DIRECT_URL') or os.environ.get('DATABASE_URL')
if db_url:
    os.environ['DATABASE_URL'] = db_url

from .settings import *

# Remove GIS para não travar a inicialização do Django no Windows
if 'django.contrib.gis' in INSTALLED_APPS:
    INSTALLED_APPS.remove('django.contrib.gis')

# Força o uso do backend padrão para não tentar carregar PostGIS
if db_url:
    url = urlparse(db_url)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': url.path[1:] if url.path else '',
        'USER': url.username or '',
        'PASSWORD': unquote(url.password) if url.password else '',
        'HOST': url.hostname or '',
        'PORT': str(url.port) if url.port else '5432',
    }


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
