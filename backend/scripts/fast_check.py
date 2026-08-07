import os
import sys

# Injetar o Fake GIS antes de qualquer coisa para não travar no Windows
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_migrate")

import django

django.setup()

from django.core.management import call_command

try:
    call_command("check")
    print("ALL OK")
except Exception:
    import traceback

    traceback.print_exc()
