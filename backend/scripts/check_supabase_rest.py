import requests

url = "https://mdrutawgropwgsmwygtz.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

res = requests.get(f"{url}/rest/v1/PlatformAdmin?select=id,email,supabase_uid", headers=headers)
print("Platform Admins:", res.json())

res2 = requests.get(f"{url}/rest/v1/StaffMember?select=id,email,supabase_uid", headers=headers)
print("Staff:", res2.json())
