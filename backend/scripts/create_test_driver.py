import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
import psycopg

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("Falta variável de ambiente DATABASE_URL no .env")
    exit(1)

TEST_PHONE = os.environ.get("TEST_DRIVER_PHONE", "11999999999")
TEST_NAME = os.environ.get("TEST_DRIVER_NAME", "Motoboy Teste")
TEST_DOC = os.environ.get("TEST_DRIVER_DOC", "12345678901")

try:
    print("Conectando ao banco de dados PostgreSQL...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Verificar ou Criar Operator
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

            # 2. Criar ou Atualizar Driver
            cur.execute('SELECT id FROM "Driver" WHERE phone = %s', (TEST_PHONE,))
            driver_row = cur.fetchone()

            if driver_row:
                driver_id = driver_row[0]
                print(f"Driver já existe para o telefone {TEST_PHONE} com ID {driver_id}. Atualizando...")
                cur.execute(
                    'UPDATE "Driver" SET operator_id = %s, active = TRUE, online = TRUE WHERE id = %s',
                    (operator_id, driver_id)
                )
            else:
                driver_id = str(uuid.uuid4())
                print(f"Inserindo novo Driver com ID {driver_id}...")
                cur.execute(
                    '''
                    INSERT INTO "Driver" (
                        id, operator_id, name, phone, document,
                        "pixKeyType", "pixKey", active, online,
                        operational_status, onboarding_status, "createdAt", "updatedAt"
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        'CPF', %s, TRUE, TRUE,
                        'AVAILABLE', 'ACTIVE', NOW(), NOW()
                    )
                    ''',
                    (driver_id, operator_id, TEST_NAME, TEST_PHONE, TEST_DOC, TEST_DOC)
                )

            conn.commit()
            print(f"Driver provisionado com sucesso no PostgreSQL nativo! (ID: {driver_id})")

except Exception as e:
    print(f"Erro ao provisionar motorista: {e}")
    exit(1)
