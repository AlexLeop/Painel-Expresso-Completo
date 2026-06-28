import os
from supabase import create_client

url = "https://mdrutawgropwgsmwygtz.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3NDUyNzUsImV4cCI6MjA5NzMyMTI3NX0.EVGv7fEupCR3Ru4wAffCeeR2Uq5Bl_HQxvJUY2HV3T0"
client = create_client(url, key)

try:
    res = client.auth.get_user("fake_token_just_to_see_exception")
    print(res)
except Exception as e:
    print(e.__class__.__name__)
    print(e)
