import urllib.request, urllib.error, json

def test_endpoints(email, password, label):
    print(f"\n--- Testing for {label} ({email}) ---")
    url = 'https://expresso-neves-django.a3rpjn.easypanel.host/api/auth/login'
    data = json.dumps({'email': email, 'password': password}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        token = res['access_token']
        print(f"Token obtained for {label}")

    for endpoint in ['/api/v1/admin/finance/payout-policy', '/api/v1/admin/finance/withdrawals?limit=100']:
        full_url = f'https://expresso-neves-django.a3rpjn.easypanel.host{endpoint}'
        req2 = urllib.request.Request(full_url, headers={'Authorization': f'Bearer {token}'})
        try:
            with urllib.request.urlopen(req2) as resp2:
                print(f"[{resp2.status}] {endpoint}: {resp2.read().decode()[:150]}")
        except urllib.error.HTTPError as e:
            print(f"[{e.code}] {endpoint} HTTPError: {e.read().decode()}")

test_endpoints('marcelo.neves@gmail.com', '123456', 'Operador Marcelo')
test_endpoints('admin@expressoneves.com.br', 'admin', 'Superadmin')
