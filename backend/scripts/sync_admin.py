import os
import sys
import psycopg
from supabase import create_client

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_file = BASE_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("SUPABASE_URL=") and not os.environ.get("SUPABASE_URL"):
            os.environ["SUPABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("SUPABASE_SERVICE_ROLE_KEY=") and not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
            os.environ["SUPABASE_SERVICE_ROLE_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("DATABASE_URL=") and not os.environ.get("DATABASE_URL"):
            os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

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
