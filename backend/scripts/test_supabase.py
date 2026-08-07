import os
import sys

# Setup mock environment
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "fake-key"

from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

try:
    res = supabase.auth.get_user("fake_token")
    print("Success:", res)
except Exception as e:
    print("Exception type:", type(e))
    print("Exception:", e)
