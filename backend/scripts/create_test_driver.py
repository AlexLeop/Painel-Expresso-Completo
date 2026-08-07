import os
import uuid
from dotenv import load_dotenv
import psycopg

SUPABASE_URL = "https://mdrutawgropwgsmwygtz.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"
DATABASE_URL = "postgresql://postgres.mdrutawgropwgsmwygtz:91203095_%23%23%40@aws-1-us-west-2.pooler.supabase.com:5432/postgres"

if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL]):
    print("Faltam variáveis de ambiente no .env")
    exit(1)

import requests

def create_supabase_user(email, password):
    print(f"Criando usuário no Supabase Auth: {email}...")
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "password": password,
        "email_confirm": True
    }
    resp = requests.post(f"{SUPABASE_URL}/auth/v1/admin/users", headers=headers, json=data)
    if resp.status_code == 200 or resp.status_code == 201:
        return resp.json()["id"]
    elif resp.status_code == 422 and "already registered" in resp.text:
        # Busca o usuário existente
        resp_get = requests.get(f"{SUPABASE_URL}/auth/v1/admin/users", headers=headers)
        users = resp_get.json().get("users", [])
        for u in users:
            if u["email"] == email:
                print(f"Usuário {email} já existe. UID: {u['id']}")
                return u["id"]
        raise Exception("Usuário já existe mas não foi encontrado na listagem")
    else:
        raise Exception(f"Erro ao criar usuário: {resp.text}")

try:
    uid = create_supabase_user("motoboy@teste.com", "senha123")
    print(f"Motoboy UID no Supabase Auth: {uid}")
    
    print("Conectando ao banco de dados via psycopg...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Verificar/Criar Operator
            cur.execute('SELECT id FROM "Operator" LIMIT 1')
            op_row = cur.fetchone()
            if not op_row:
                print("Nenhum Operator encontrado. Criando operador Logístico de Teste...")
                operator_id = str(uuid.uuid4())
                cur.execute(
                    'INSERT INTO "Operator" (id, name, status) VALUES (%s, %s, %s)',
                    (operator_id, "Operador Teste", "ACTIVE")
                )
            else:
                operator_id = op_row[0]
                print(f"Usando Operator existente: {operator_id}")

            # 2. Verificar/Criar Driver
            cur.execute('SELECT id FROM "Driver" WHERE supabase_uid = %s', (uid,))
            drv_row = cur.fetchone()
            if drv_row:
                print("Motoboy de teste já está cadastrado na tabela Driver.")
            else:
                print("Inserindo motoboy na tabela Driver...")
                driver_id = str(uuid.uuid4())
                cur.execute(
                    '''
                    INSERT INTO "Driver" 
                    (id, operator_id, supabase_uid, name, phone, "pixKeyType", "pixKey", active, "createdAt", "updatedAt") 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ''',
                    (
                        driver_id, operator_id, uid, "Motoboy Teste", 
                        "11999999999", "CPF", "12345678900", True
                    )
                )
                print("Motoboy cadastrado com sucesso!")
            
            # ATUALIZA O RAW_APP_META_DATA NO SUPABASE AUTH
            cur.execute("SELECT raw_app_meta_data FROM auth.users WHERE id = %s", (uid,))
            meta_row = cur.fetchone()
            if meta_row:
                import json
                meta = meta_row[0] or {}
                if isinstance(meta, str):
                    meta = json.loads(meta)
                
                meta['role'] = 'driver'
                
                cur.execute("UPDATE auth.users SET raw_app_meta_data = %s WHERE id = %s", (json.dumps(meta), uid))
                print("Role 'driver' injetada no app_metadata do motoboy.")

            conn.commit()
            print("\nTudo pronto! Credenciais de teste do motoboy:")
            print("Email: motoboy@teste.com")
            print("Senha: senha123")
except Exception as e:
    print(f"Ocorreu um erro: {e}")
