import urllib.request, urllib.error, json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.conf import settings
if not settings.configured:
    settings.configure(SECRET_KEY="django-insecure-development-key-only")

from accounts.security import create_access_token

token_superadmin = create_access_token({
    "sub": "00000000-0000-0000-0000-000000000001",
    "email": "admin@expressoneves.com.br",
    "role": "superadmin",
    "user_type": "platform_admin",
    "is_platform_admin": True,
    "operator_id": None,
})

print("[*] Testing with Superadmin token (operator_id: None)...")
for endpoint in ['/api/v1/admin/finance/payout-policy', '/api/v1/admin/finance/withdrawals?limit=100']:
    full_url = f'https://expresso-neves-django.a3rpjn.easypanel.host{endpoint}'
    req = urllib.request.Request(full_url, headers={'Authorization': f'Bearer {token_superadmin}'})
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[{resp.status}] {endpoint}: {resp.read().decode()[:150]}")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {endpoint} HTTPError: {e.read().decode()}")
