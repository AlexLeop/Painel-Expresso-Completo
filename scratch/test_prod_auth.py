import requests
from supabase import create_client

SUPABASE_URL = 'https://mdrutawgropwgsmwygtz.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3NDUyNzUsImV4cCI6MjA5NzMyMTI3NX0.EVGv7fEupCR3Ru4wAffCeeR2Uq5Bl_HQxvJUY2HV3T0'

client = create_client(SUPABASE_URL, SUPABASE_KEY)
res = client.auth.sign_in_with_password({"email": "master@expressoneves.com", "password": "expressomaster"})
token = res.session.access_token if res.session else None

print(f"Token obtained: {token[:20]}...")

# Now test the production backend
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

resp = requests.get("https://expresso-neves-django.a3rpjn.easypanel.host/api/auth/me", headers=headers)
print(f"Status Code: {resp.status_code}")
print(f"Response: {resp.text}")
