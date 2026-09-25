"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

try:
    from config.db_api import _ensure_database_schema
    _ensure_database_schema()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Could not auto-align database schema on WSGI startup: {e}")
