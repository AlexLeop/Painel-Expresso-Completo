#!/usr/bin/env python
"""
Wrapper para manage.py que injeta os mocks GDAL/GEOS e o fix do UUID converter
ANTES de inicializar o Django. Necessário no Windows sem binários GDAL.

Uso: python manage_dev.py makemigrations
     python manage_dev.py migrate
     python manage_dev.py showmigrations
"""
import os
import sys

from config.gis_compat import install_windows_gis_fallback

install_windows_gis_fallback()

# 2. Agora roda o manage.py normal
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc

execute_from_command_line(sys.argv)
