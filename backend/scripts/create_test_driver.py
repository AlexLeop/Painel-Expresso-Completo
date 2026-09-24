import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
import psycopg

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
TEST_OPERATOR_ID = os.environ.get("TEST_OPERATOR_ID")
ALLOW_TEST_DATA = os.environ.get("ALLOW_TEST_DATA", "").lower() == "true"

if not DATABASE_URL or not TEST_OPERATOR_ID or not ALLOW_TEST_DATA:
    print("Defina DATABASE_URL, TEST_OPERATOR_ID e ALLOW_TEST_DATA=true explicitamente.")
    exit(1)

TEST_PHONE = os.environ.get("TEST_DRIVER_PHONE")
TEST_NAME = os.environ.get("TEST_DRIVER_NAME")
TEST_DOC = os.environ.get("TEST_DRIVER_DOC")
if not all((TEST_PHONE, TEST_NAME, TEST_DOC)):
    print("Defina TEST_DRIVER_PHONE, TEST_DRIVER_NAME e TEST_DRIVER_DOC explicitamente.")
    exit(1)

try:
    print("Conectando ao banco de dados PostgreSQL...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # O tenant é sempre explícito; nunca selecionamos o primeiro operador.
            cur.execute('SELECT id FROM "Operator" WHERE id = %s', (TEST_OPERATOR_ID,))
            op_row = cur.fetchone()
            if not op_row:
                raise RuntimeError("TEST_OPERATOR_ID não corresponde a um operador existente.")
            operator_id = op_row[0]
            print(f"Usando Operator explicitamente selecionado: {operator_id}")

            # 2. Criar ou Atualizar Driver
            cur.execute('SELECT id, operator_id FROM "Driver" WHERE phone = %s', (TEST_PHONE,))
            driver_row = cur.fetchone()

            if driver_row:
                driver_id = driver_row[0]
                if str(driver_row[1]) != str(operator_id):
                    raise RuntimeError("O telefone já pertence a um motoboy de outro operador.")
                print(f"Driver já existe para o telefone {TEST_PHONE} com ID {driver_id}. Atualizando...")
                cur.execute(
                    'UPDATE "Driver" SET active = TRUE, online = TRUE WHERE id = %s AND operator_id = %s',
                    (driver_id, operator_id)
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
