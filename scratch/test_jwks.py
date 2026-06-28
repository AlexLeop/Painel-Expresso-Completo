import requests

url = "https://mdrutawgropwgsmwygtz.supabase.co/auth/v1/jwks"
try:
    headers = {"apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"}
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("JWKS:", response.json())
except Exception as e:
    print("Error:", e)
