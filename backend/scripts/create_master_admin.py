import os
import requests
import psycopg2
import uuid

SUPABASE_URL = "https://mdrutawgropwgsmwygtz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"

# Using DIRECT_URL (port 5432) for simple inserts without pgbouncer issues
DATABASE_URL = "postgresql://postgres.mdrutawgropwgsmwygtz:91203095_%23%23%40@aws-1-us-west-2.pooler.supabase.com:5432/postgres"

def create_admin():
    # 1. Create user in Supabase Auth
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": "master@expressoneves.com",
        "password": "ExpressoAdmin@2026",
        "email_confirm": True,
        "user_metadata": {
            "name": "Admin Mestre"
        }
    }
    print("Criando usuário no Supabase Auth...")
    response = requests.post(f"{SUPABASE_URL}/auth/v1/admin/users", headers=headers, json=data)
    
    if response.status_code not in (200, 201):
        if "already been registered" in response.text:
            print("Usuário já existe no Auth! Tentando buscar o ID...")
            # We don't have a direct endpoint to get user by email simply without extra perms, 
            # but since we are admin we could list users. Let's just create a new email if so.
        print("Erro ao criar usuário no Auth:", response.text)
        # Let's list users to find it
        res = requests.get(f"{SUPABASE_URL}/auth/v1/admin/users", headers=headers)
        users = res.json().get('users', [])
        for u in users:
            if u['email'] == data['email']:
                supabase_uid = u['id']
                print(f"Usuário encontrado! UID: {supabase_uid}")
                break
        else:
            return
    else:
        user_data = response.json()
        supabase_uid = user_data["id"]
        print(f"Usuário criado com sucesso. UID: {supabase_uid}")
    
    # 2. Insert into PlatformAdmin
    print("Conectando ao banco de dados para inserir em PlatformAdmin...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    admin_id = str(uuid.uuid4())
    
    try:
        cur.execute("""
            INSERT INTO public."PlatformAdmin" (id, supabase_uid, name, email, "createdAt")
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (email) DO UPDATE SET supabase_uid = EXCLUDED.supabase_uid;
        """, (admin_id, supabase_uid, "Admin Mestre", "master@expressoneves.com"))
        conn.commit()
        print("PlatformAdmin criado ou atualizado com sucesso!")
    except Exception as e:
        print("Erro ao inserir em PlatformAdmin:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_admin()
