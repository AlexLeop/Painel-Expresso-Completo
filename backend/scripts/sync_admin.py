import os
import sys
import psycopg
from supabase import create_client

SUPABASE_URL = "https://mdrutawgropwgsmwygtz.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"
DATABASE_URL = "postgresql://postgres.mdrutawgropwgsmwygtz:91203095_%23%23%40@aws-1-us-west-2.pooler.supabase.com:5432/postgres"

# 1. Obter usuários do Supabase Auth
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
try:
    response = supabase.auth.admin.list_users()
    users = response
    if not users:
        print("Nenhum usuário encontrado no Supabase Auth.")
        sys.exit(0)
    
    first_user = users[0]
    uid = first_user.id
    email = first_user.email
    print(f"Encontrado usuário: {email} (UID: {uid})")
    
except Exception as e:
    print(f"Erro ao obter usuários do Supabase: {e}")
    sys.exit(1)

# 2. Inserir no banco de dados do Django
try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Verifica se o usuário já existe
            cur.execute('SELECT id FROM "PlatformAdmin" WHERE supabase_uid = %s', (uid,))
            if cur.fetchone():
                print(f"Usuário {email} já é um PlatformAdmin.")
            else:
                cur.execute(
                    """
                    INSERT INTO "PlatformAdmin" (email, name, supabase_uid)
                    VALUES (%s, %s, %s)
                    """,
                    (email, email.split('@')[0] if email else 'Admin', uid)
                )
                print(f"PlatformAdmin criado para {email} com sucesso!")
            
            # ATUALIZA O RAW_APP_META_DATA NO SUPABASE AUTH PARA INCLUIR A ROLE DE PLATFORM_ADMIN
            print(f"Atualizando app_metadata no Supabase para o usuário {email}...")
            cur.execute("SELECT raw_app_meta_data FROM auth.users WHERE id = %s", (uid,))
            meta_row = cur.fetchone()
            if meta_row:
                import json
                meta = meta_row[0] or {}
                if isinstance(meta, str):
                    meta = json.loads(meta)
                
                meta['role'] = 'platform_admin'
                
                cur.execute("UPDATE auth.users SET raw_app_meta_data = %s WHERE id = %s", (json.dumps(meta), uid))
                print(f"Role 'platform_admin' injetada no app_metadata de {email} com sucesso!")
            
            conn.commit()
except psycopg.errors.UndefinedTable as e:
    print(f"Erro: A tabela 'PlatformAdmin' não existe. Erro original: {e}")
except Exception as e:
    print(f"Erro ao inserir no banco: {e}")
