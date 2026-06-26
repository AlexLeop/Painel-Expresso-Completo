import os
import sys

# Mock platform functions that hang on Windows due to WMI issues
import platform

platform.system = lambda: "Windows"
platform.uname = lambda: platform.uname_result(
    "Windows", "localhost", "10", "10.0", "AMD64"
)

# Injetar o Fake GIS antes de qualquer coisa para não travar no Windows
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import types

sys.modules["django.contrib.gis"] = types.ModuleType("django.contrib.gis")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_migrate")

import django

django.setup()

from django.core.management import call_command

try:
    print("Iniciando Migrations...")
    call_command("migrate", interactive=False)
    print("ALL OK")
except Exception:
    import traceback

    traceback.print_exc()
