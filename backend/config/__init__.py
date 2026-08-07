# Isso garante que o app do celery seja sempre importado quando
# o Django iniciar, para que a anotação @shared_task o encontre.

import platform
import sys


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

__all__ = ("celery_app",)
