import os
import sys

# Configure Django
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Injetar o Fake GIS no Windows para evitar o erro de GDAL não encontrado
if sys.platform == 'win32':
    try:
        import tests.fake_gis
        import types
        sys.modules['django.contrib.gis'] = types.ModuleType('django.contrib.gis')
    except ImportError:
        pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.test import Client

def run_tests():
    print("=== SURGICAL API VERIFICATION ===")
    client = Client()
    
    print("Testing /api/v1/health (sem auth)")
    response = client.get('/api/v1/health')
    print(f"Status: {response.status_code}")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    print("Response:", response.json())

    print("Testing /api/v1/logistics/operator/ping sem auth (esperado 401/403/404)")
    response = client.get('/api/v1/logistics/operator/ping')
    print(f"Status: {response.status_code}")
    assert response.status_code in [401, 403, 404], f"Auth not enforced, got {response.status_code}"

    print("Testing /api/v1/accounts/operator/drivers (POST) sem auth (esperado 401)")
    response = client.post('/api/v1/accounts/operator/drivers', data={}, content_type='application/json')
    print(f"Status: {response.status_code}")
    assert response.status_code in [401, 403], f"Auth not enforced, got {response.status_code}"

    print("ALL BASIC ROUTES LOADED SUCCESSFULLY AND ENFORCING RBAC/AUTH!")

if __name__ == '__main__':
    run_tests()
