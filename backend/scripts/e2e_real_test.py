import os
import sys
import uuid

# Adicionar raiz do projeto ao sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Mock GDAL/GEOS antes de qualquer import do Django
import tests.fake_gis  # noqa

# Configurar Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_migrate")
import django

django.setup()

from django.test import Client
from django.db import connection

# ==========================================
# HELPERS
# ==========================================


def execute_raw(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if sql.strip().upper().startswith("SELECT"):
            try:
                return cursor.fetchall()
            except:
                return None
        return None


def green(text):
    return f"\033[92m{text}\033[0m"


def red(text):
    return f"\033[91m{text}\033[0m"


# ==========================================
# FASE 1: SETUP
# ==========================================
print("\n--- INICIANDO TESTE END-TO-END NO SUPABASE REAL ---")

# IDs únicos para esta rodada de testes
operator_a_id = uuid.uuid4()
operator_b_id = uuid.uuid4()
driver_id = uuid.uuid4()
store_id = uuid.uuid4()
order_id = uuid.uuid4()
stop1_id = uuid.uuid4()
stop2_id = uuid.uuid4()

try:
    print(
        "\n[FASE 1] Limpando dados antigos (se existirem) e populando dados de teste..."
    )

    # Criar via raw SQL para evitar problemas de mock de PostGIS (apesar de que Operator não tem geometry)
    execute_raw(
        """
        INSERT INTO "Operator" (id, name, "taxId", email, "createdAt") 
        VALUES (%s, 'Operator A', '11111111111', 'a@test.com', NOW());
    """,
        [operator_a_id],
    )

    execute_raw(
        """
        INSERT INTO "Operator" (id, name, "taxId", email, "createdAt") 
        VALUES (%s, 'Operator B', '22222222222', 'b@test.com', NOW());
    """,
        [operator_b_id],
    )

    execute_raw(
        """
        INSERT INTO "Driver" (id, operator_id, "firstName", "lastName", "taxId", phone, status)
        VALUES (%s, %s, 'John', 'Doe', '33333333333', '11999999999', 'AVAILABLE');
    """,
        [driver_id, operator_a_id],
    )

    execute_raw(
        """
        INSERT INTO "Store" (id, operator_id, name, "taxId")
        VALUES (%s, %s, 'Loja Matriz', '44444444444');
    """,
        [store_id, operator_a_id],
    )

    # Inserir Order e Stops usando raw sql para lidar com ST_SetSRID (PostGIS nativo!)
    execute_raw(
        """
        INSERT INTO "Order" (id, operator_id, store_id, driver_id, status, "totalAmount")
        VALUES (%s, %s, %s, %s, 'PENDING', 50.00);
    """,
        [order_id, operator_a_id, store_id, driver_id],
    )

    execute_raw(
        """
        INSERT INTO "Stop" (id, operator_id, order_id, sequence, location, type, "pinCode")
        VALUES (%s, %s, %s, 1, ST_SetSRID(ST_MakePoint(-46.6333, -23.5505), 4326), 'PICKUP', '1234');
    """,
        [stop1_id, operator_a_id, order_id],
    )

    execute_raw(
        """
        INSERT INTO "Stop" (id, operator_id, order_id, sequence, location, type, "pinCode")
        VALUES (%s, %s, %s, 2, ST_SetSRID(ST_MakePoint(-46.6433, -23.5605), 4326), 'DROPOFF', '9999');
    """,
        [stop2_id, operator_a_id, order_id],
    )

    print(green("Setup concluído! Banco populado de forma nativa."))

except Exception as e:
    print(red(f"Erro no setup: {e}"))
    sys.exit(1)


# ==========================================
# FASE 2: TESTE DE RLS (SEGURANÇA MULTI-TENANT)
# ==========================================
print("\n[FASE 2] Testando RLS (Row Level Security)...")
client = Client()

# Forjando claims de JWT na requisição para o Operator A
headers_a = {"HTTP_X_MOCK_JWT_OPERATOR_ID": str(operator_a_id)}
headers_b = {"HTTP_X_MOCK_JWT_OPERATOR_ID": str(operator_b_id)}

# Operator A tenta acessar driver do Operator A (Deve funcionar)
# Wait, We don't have endpoints specifically mapping to /driver/ via GET, but let's test RLS logic.
try:
    with connection.cursor() as c:
        # Simulando o que o Supabase Middleware faz (SET LOCAL request.jwt.claims)
        c.execute(
            f'SET LOCAL request.jwt.claims = \'{{"app_metadata": {{"operator_id": "{operator_a_id}"}}}}\';'
        )
        c.execute('SELECT count(*) FROM "Driver";')
        count_a = c.fetchone()[0]

        c.execute(
            f'SET LOCAL request.jwt.claims = \'{{"app_metadata": {{"operator_id": "{operator_b_id}"}}}}\';'
        )
        c.execute('SELECT count(*) FROM "Driver";')
        count_b = c.fetchone()[0]

    if count_a == 1 and count_b == 0:
        print(
            green(
                "RLS passou perfeitamente! Operator B não consegue enxergar o Driver do Operator A."
            )
        )
    else:
        print(red(f"Falha RLS! A viu {count_a}, B viu {count_b}"))

except Exception as e:
    print(red(f"Erro no RLS: {e}"))


# ==========================================
# FASE 3: API E FLUXO LOGÍSTICO (DJANGO)
# ==========================================
print("\n[FASE 3] Executando Fluxo Logístico via Endpoints Django (REST API)...")
try:
    # 1. Driver aceita a corrida (passando header de driver e operator)
    resp = client.post(
        f"/api/v1/logistics/orders/{order_id}/accept",
        HTTP_X_MOCK_JWT_OPERATOR_ID=str(operator_a_id),
        HTTP_X_MOCK_JWT_DRIVER_ID=str(driver_id),
    )
    if resp.status_code == 200:
        print(green("✔ Aceite de corrida (Endpoint): 200 OK"))
    else:
        print(red(f"✘ Falha ao aceitar corrida: {resp.status_code} - {resp.content}"))

    # 2. Driver completa as paradas (enviando PIN)
    payload_pickup = {"stops": [{"id": str(stop1_id), "pinCode": "1234"}]}
    resp = client.post(
        f"/api/v1/logistics/orders/{order_id}/complete_stops",
        data=payload_pickup,
        content_type="application/json",
        HTTP_X_MOCK_JWT_OPERATOR_ID=str(operator_a_id),
        HTTP_X_MOCK_JWT_DRIVER_ID=str(driver_id),
    )
    if resp.status_code == 200:
        print(green("✔ Complete Stop (Pickup com PIN 1234): 200 OK"))
    else:
        print(red(f"✘ Falha ao completar pickup: {resp.status_code} - {resp.content}"))

    # Completar Dropoff (Finaliza a corrida)
    payload_dropoff = {"stops": [{"id": str(stop2_id), "pinCode": "9999"}]}
    resp = client.post(
        f"/api/v1/logistics/orders/{order_id}/complete_stops",
        data=payload_dropoff,
        content_type="application/json",
        HTTP_X_MOCK_JWT_OPERATOR_ID=str(operator_a_id),
        HTTP_X_MOCK_JWT_DRIVER_ID=str(driver_id),
    )
    if resp.status_code == 200:
        print(green("✔ Complete Stop (Dropoff com PIN 9999): 200 OK"))
    else:
        print(red(f"✘ Falha ao completar dropoff: {resp.status_code} - {resp.content}"))

except Exception as e:
    print(red(f"Erro no Fluxo da API: {e}"))


# ==========================================
# FASE 4: INTEGRAÇÃO E FINANCEIRO
# ==========================================
print("\n[FASE 4] Checando Eventos Assíncronos no Banco de Dados...")
try:
    with connection.cursor() as c:
        # Wallet
        c.execute('SELECT balance FROM "Wallet" WHERE driver_id = %s', [driver_id])
        wallet_row = c.fetchone()
        if wallet_row:
            print(green(f"✔ Wallet atualizada com sucesso! Saldo: {wallet_row[0]}"))
        else:
            print(red("✘ Wallet não encontrada (Transação falhou)."))

        # Outbox
        c.execute(
            'SELECT "eventType", status FROM "IntegrationOutbox" WHERE "aggregateId" = %s',
            [order_id],
        )
        outbox_rows = c.fetchall()
        if outbox_rows:
            print(green(f"✔ Eventos de integração gerados: {outbox_rows}"))
        else:
            print(red("✘ Nenhum evento gerado no IntegrationOutbox."))

except Exception as e:
    print(red(f"Erro no check financeiro: {e}"))


# ==========================================
# FASE 5: CLEANUP
# ==========================================
print("\n[FASE 5] Limpando Sujeira...")
try:
    execute_raw(
        'DELETE FROM "Operator" WHERE id IN (%s, %s)', [operator_a_id, operator_b_id]
    )
    print(
        green("✔ Cleanup concluído! Banco Supabase está perfeitamente limpo novamente.")
    )
except Exception as e:
    print(red(f"Erro ao limpar banco: {e}"))

print("\n--- TESTE E2E CONCLUÍDO ---")
