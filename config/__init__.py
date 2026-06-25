# Isso garante que o app do celery seja sempre importado quando
# o Django iniciar, para que a anotação @shared_task o encontre.

import platform
import sys
from .gis_compat import install_windows_gis_fallback

if sys.platform == 'win32':
    # Previne travamento no Windows (WMI bug) quando Celery tentar ler infos do sistema
    original_system = getattr(platform, 'system', None)
    platform.system = lambda: "Windows"
    try:
        original_uname = platform.uname
        platform.uname = lambda: platform.uname_result("Windows", "localhost", "10", "10.0", "AMD64")
    except AttributeError:
        pass

    # Permite carregar modelos com campos GIS sem GDAL nativo instalado.
    install_windows_gis_fallback()

# Patch para contornar bug do Django 6 com django-ninja (UUID converter já registrado)
import django.urls.converters
import django.urls
_original_register_converter = django.urls.converters.register_converter

def _safe_register_converter(converter, type_name):
    try:
        _original_register_converter(converter, type_name)
    except ValueError:
        pass

django.urls.converters.register_converter = _safe_register_converter
django.urls.register_converter = _safe_register_converter

from .celery import app as celery_app

__all__ = ('celery_app',)
