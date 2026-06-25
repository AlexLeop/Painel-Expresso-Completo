import os

# Ensure root conftest.py has already mocked GDAL/GEOS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')
