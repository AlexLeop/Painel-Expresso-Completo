import psycopg
from supabase import create_client
import json

SUPABASE_URL = 'https://mdrutawgropwgsmwygtz.supabase.co'
SUPABASE_SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY'
DATABASE_URL = 'postgresql://postgres.mdrutawgropwgsmwygtz:91203095_%23%23%40@aws-1-us-west-2.pooler.supabase.com:5432/postgres'

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
users = client.auth.admin.list_users()

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        for u in users:
            uid = u.id
            email = u.email
            cur.execute('SELECT id FROM "PlatformAdmin" WHERE supabase_uid = %s', (uid,))
            if cur.fetchone():
                print(f'User {email} already in PlatformAdmin')
            else:
                cur.execute('INSERT INTO "PlatformAdmin" (email, name, supabase_uid) VALUES (%s, %s, %s)', (email, (email or "").split('@')[0], uid))
                print(f'User {email} inserted into PlatformAdmin')
            
            cur.execute('SELECT raw_app_meta_data FROM auth.users WHERE id = %s', (uid,))
            meta_row = cur.fetchone()
            if meta_row:
                meta = meta_row[0] or {}
                if isinstance(meta, str):
                    meta = json.loads(meta)
                meta['role'] = 'platform_admin'
                cur.execute('UPDATE auth.users SET raw_app_meta_data = %s WHERE id = %s', (json.dumps(meta), uid))
                print(f'Role updated for {email}')
        conn.commit()
