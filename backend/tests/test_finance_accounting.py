import pytest
import uuid
from datetime import date
from django.db import connection
from accounts.models import Operator, StaffMember
from logistics.models import Client, Store, Driver, Order
from finance.models import ManualEntry, WeeklyStoreInvoice
from config.db_api import compute_store_balance

@pytest.fixture(autouse=True)
def setup_accounting_tables(db):
    if not hasattr(connection.ops, "select"):
        setattr(connection.ops, "select", "%s")
    if not hasattr(connection.ops, "get_geom_placeholder"):
        setattr(connection.ops, "get_geom_placeholder", lambda f, v, c: "%s")
    with connection.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Operator" (
                id CHAR(32) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                cnpj VARCHAR(14),
                status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "StaffMember" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                supabase_uid CHAR(32),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                "passwordHash" VARCHAR(255),
                role VARCHAR(20) NOT NULL DEFAULT 'OPERATOR_ROLE',
                active BOOLEAN NOT NULL DEFAULT 1,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Client" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                name VARCHAR(255) NOT NULL,
                document VARCHAR(20) NOT NULL,
                active BOOLEAN NOT NULL DEFAULT 1,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Store" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                client_id CHAR(32),
                name VARCHAR(255) NOT NULL,
                "averagePrepTimeMinutes" INT DEFAULT 15,
                operational BOOLEAN DEFAULT 0,
                geom TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Driver" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                document VARCHAR(20),
                supabase_uid CHAR(32),
                "passwordHash" VARCHAR(255),
                online BOOLEAN DEFAULT 0,
                geom TEXT,
                heading INT DEFAULT 0,
                "speedKmh" INT DEFAULT 0,
                "lastPingAt" TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                operational_status VARCHAR(30) DEFAULT 'OFFLINE',
                "maxActiveOrders" INT DEFAULT 1,
                onboarding_status VARCHAR(50) DEFAULT 'INVITED',
                tax_classification VARCHAR(50) DEFAULT 'PESSOA_FISICA_AUTONOMO',
                "pixKeyType" VARCHAR(20),
                "pixKey" VARCHAR(255),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Order" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                driver_id CHAR(32),
                manifest_id CHAR(32),
                status VARCHAR(30) DEFAULT 'COMPLETED',
                "fareValueCents" INT DEFAULT 0,
                "storeAuthorizedBonusCents" INT DEFAULT 0,
                "distanceMeters" INT DEFAULT 0,
                "businessDate" DATE,
                "allocationDifficulty" BOOLEAN DEFAULT 0,
                "requestedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "acceptedAt" TIMESTAMP,
                "startedAt" TIMESTAMP,
                "arrivedAt" TIMESTAMP,
                "completedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "canceledAt" TIMESTAMP,
                "external_order_id" VARCHAR(255),
                "external_source" VARCHAR(50),
                metadata TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "ManualEntry" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL,
                store_id CHAR(32),
                created_by_staff_id CHAR(32),
                created_by_client_id CHAR(32),
                "amountCents" BIGINT NOT NULL,
                description TEXT NOT NULL,
                "visibleToStore" BOOLEAN DEFAULT 1,
                "taxCategory" VARCHAR(50) DEFAULT 'TAXABLE_INCOME',
                status VARCHAR(30) DEFAULT 'APPROVED',
                "rejectReason" TEXT,
                "approvedById" CHAR(32),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WeeklyStoreInvoice" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                "startDate" DATE NOT NULL,
                "endDate" DATE NOT NULL,
                "totalNetProducaoCents" BIGINT DEFAULT 0,
                "totalNetGarantidaCents" BIGINT DEFAULT 0,
                "administrativeFeeCents" BIGINT DEFAULT 0,
                "supervisionFeeCents" BIGINT DEFAULT 0,
                "pendingDebitCarriedCents" BIGINT DEFAULT 0,
                "totalCents" BIGINT NOT NULL,
                status VARCHAR(20) DEFAULT 'DRAFT',
                "paymentGatewayId" VARCHAR(255),
                "pixCopyPaste" TEXT,
                barcode TEXT,
                "pdfUrl" VARCHAR(255),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    yield

@pytest.fixture
def accounting_setup(db):
    operator = Operator.objects.create(
        id=uuid.uuid4(),
        name="Expresso Neves",
        cnpj="35986980000128"
    )
    client = Client.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        name="1000ton Lanches",
        document="41275691000113",
        active=True
    )
    from django.contrib.gis.db.models.proxy import SpatialProxy
    setattr(SpatialProxy, "__set__", lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value))
    setattr(SpatialProxy, "__get__", lambda self, instance, cls=None: instance.__dict__.get(self.field.attname) if instance else self)

    store = Store.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        client=client,
        name="1000ton Loja Central",
        operational=True
    )
    driver = Driver.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        name="Carlos Motoboy",
        phone="61999990001",
        active=True
    )
    staff = StaffMember.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        name="Marcelo Gerente",
        email="marcelo.neves@gmail.com",
        role="ADMIN",
        active=True
    )
    return {
        "operator": operator,
        "client": client,
        "store": store,
        "driver": driver,
        "staff": staff
    }

@pytest.mark.django_db
def test_store_balance_zero_initial(accounting_setup):
    store = accounting_setup["store"]
    bal = compute_store_balance(store)
    assert bal["balance_cents"] == 0
    assert bal["status"] == "ZERADO"
    assert bal["total_credits_cents"] == 0
    assert bal["total_debits_cents"] == 0

@pytest.mark.django_db
def test_store_balance_with_recharge_and_orders(accounting_setup):
    setup = accounting_setup
    store = setup["store"]
    operator = setup["operator"]

    # 1. Store pays an invoice of R$ 100,00 (10000 cents)
    WeeklyStoreInvoice.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        startDate=date.today(),
        endDate=date.today(),
        totalNetProducaoCents=0,
        totalNetGarantidaCents=0,
        administrativeFeeCents=0,
        supervisionFeeCents=0,
        pendingDebitCarriedCents=0,
        totalCents=10000,
        status="PAID"
    )

    bal1 = compute_store_balance(store)
    assert bal1["balance_cents"] == 10000
    assert bal1["balance_reais"] == 100.00
    assert bal1["status"] == "DISPONIVEL"

    # 2. Store completes an order of R$ 18,50 (1850 cents)
    Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        fareValueCents=1850,
        distanceMeters=3500,
        businessDate=date.today(),
        status="COMPLETED"
    )

    bal2 = compute_store_balance(store)
    assert bal2["balance_cents"] == 8150
    assert bal2["balance_reais"] == 81.50
    assert bal2["status"] == "DISPONIVEL"

    # 3. Store completes another order of R$ 90,00 (9000 cents), going into debit
    Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        fareValueCents=9000,
        distanceMeters=15000,
        businessDate=date.today(),
        status="COMPLETED"
    )

    bal3 = compute_store_balance(store)
    assert bal3["balance_cents"] == -850
    assert bal3["balance_reais"] == -8.50
    assert bal3["status"] == "DEVEDOR"

@pytest.mark.django_db
def test_operator_adjust_store_balance(accounting_setup):
    setup = accounting_setup
    store = setup["store"]
    operator = setup["operator"]
    driver = setup["driver"]
    staff = setup["staff"]

    # Add R$ 50,00 credit bonus
    ManualEntry.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        driver=driver,
        store=store,
        created_by_staff=staff,
        amountCents=5000,
        description="Bonificação de adesão",
        visibleToStore=True,
        taxCategory="TAXABLE_INCOME",
        status="APPROVED",
        approvedBy=staff
    )

    bal = compute_store_balance(store)
    assert bal["balance_cents"] == 5000
    assert bal["status"] == "DISPONIVEL"


@pytest.mark.django_db
def test_client_balance_api_endpoint(client, accounting_setup):
    from accounts.security import create_access_token
    store = accounting_setup["store"]
    client_obj = accounting_setup["client"]
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "email": "lojista@1000ton.com",
        "role": "lojista",
        "user_type": "client_portal_user",
        "client_id": str(client_obj.id),
        "is_platform_admin": False,
    })

    resp = client.get(f"/api/v1/client/balance?store_id={store.id}", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ZERADO"
    assert data["balance_cents"] == 0


@pytest.mark.django_db
def test_client_recharge_api_endpoint(client, accounting_setup):
    from accounts.security import create_access_token
    store = accounting_setup["store"]
    client_obj = accounting_setup["client"]
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "email": "lojista@1000ton.com",
        "role": "lojista",
        "user_type": "client_portal_user",
        "client_id": str(client_obj.id),
        "is_platform_admin": False,
    })

    resp = client.post(
        "/api/v1/client/recharge",
        data={"store_id": str(store.id), "amount_cents": 5000},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["amount_reais"] == 50.00
    assert "pix_copy_paste" in data


@pytest.mark.django_db
def test_operator_store_balances_api_endpoint(client, accounting_setup):
    from accounts.security import create_access_token
    operator = accounting_setup["operator"]
    staff = accounting_setup["staff"]
    token = create_access_token({
        "sub": str(staff.id),
        "email": staff.email,
        "role": "operador_admin",
        "user_type": "operator_staff",
        "operator_id": str(operator.id),
        "is_platform_admin": False,
    })

    resp = client.get("/api/v1/operator/store-balances", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert data["kpis"]["total_de_lojas"] >= 1
    assert "stores" in data
    assert len(data["stores"]) >= 1


@pytest.mark.django_db
def test_operator_cash_reconciliation_and_settle(client, accounting_setup):
    from accounts.security import create_access_token
    from logistics.models import Order
    from django.utils import timezone

    operator = accounting_setup["operator"]
    staff = accounting_setup["staff"]
    store = accounting_setup["store"]
    driver = accounting_setup["driver"]

    token = create_access_token({
        "sub": str(staff.id),
        "email": staff.email,
        "role": "operador_admin",
        "user_type": "operator_staff",
        "operator_id": str(operator.id),
        "is_platform_admin": False,
    })

    # Criar uma entrega paga em dinheiro
    now = timezone.now()
    order = Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        driver=driver,
        status="COMPLETED",
        fareValueCents=2500,
        distanceMeters=3500,
        businessDate=now.date(),
        requestedAt=now,
        completedAt=now,
        metadata={"forma_pagamento": "DINHEIRO", "valor_dinheiro_cents": 5000}
    )

    # 1. Consultar conferência de dinheiro
    resp = client.get(f"/api/v1/operator/cash-reconciliation?date={now.strftime('%Y-%m-%d')}", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert data["kpis"]["total_dinheiro_circulando_cents"] >= 5000
    assert len(data["drivers"]) >= 1
    drv_data = [d for d in data["drivers"] if d["driver_id"] == str(driver.id)][0]
    assert drv_data["total_dinheiro_cents"] == 5000
    assert drv_data["status_acerto"] == "PENDENTE"

    # 2. Realizar baixa / acerto do dinheiro
    settle_resp = client.post(
        "/api/v1/operator/settle-cash",
        data={"driver_id": str(driver.id), "amount_cents": 5000, "notes": "Baixa de acerto no balcão"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert settle_resp.status_code == 200
    settle_data = settle_resp.json()
    assert settle_data["success"] is True
    assert settle_data["status"] == "ACERTADO"


@pytest.mark.django_db
def test_operator_dispatch_store_ride_flow(client, accounting_setup):
    from accounts.security import create_access_token
    from finance.models import ManualEntry

    operator = accounting_setup["operator"]
    staff = accounting_setup["staff"]
    store = accounting_setup["store"]
    driver = accounting_setup["driver"]

    token = create_access_token({
        "sub": str(staff.id),
        "email": staff.email,
        "role": "operador_admin",
        "user_type": "operator_staff",
        "operator_id": str(operator.id),
        "is_platform_admin": False,
    })

    # 1. Tentativa com saldo insuficiente (loja tem 0 de saldo, pedido custa 1850)
    fail_resp = client.post(
        "/api/v1/operator/dispatch-store-ride",
        data={
            "store_id": str(store.id),
            "destinos": [{"endereco": "Rua das Flores, 100", "cliente": "João Silva", "telefone": "61999990000"}],
            "forma_pagamento": "DINHEIRO",
            "valor_estimado_cents": 1850,
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert fail_resp.status_code == 200
    fail_data = fail_resp.json()
    assert fail_data["success"] is False
    assert fail_data["insufficient_balance"] is True

    # 2. Adicionar saldo para a loja via ManualEntry
    ManualEntry.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        driver=driver,
        amountCents=5000,
        description="Recarga de teste para despacho",
        taxCategory="TAXABLE_INCOME",
        status=ManualEntry.EntryStatus.APPROVED,
    )

    # 3. Agora o despacho deve ter sucesso
    success_resp = client.post(
        "/api/v1/operator/dispatch-store-ride",
        data={
            "store_id": str(store.id),
            "driver_id": str(driver.id),
            "destinos": [{"endereco": "Rua das Flores, 100", "numero": "100", "cliente": "João Silva", "telefone": "61999990000"}],
            "forma_pagamento": "DINHEIRO",
            "valor_estimado_cents": 1850,
            "distancia_metros": 2500,
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert success_resp.status_code == 200
    success_data = success_resp.json()
    assert success_data["success"] is True
    assert "order_id" in success_data
    assert success_data["status"] == "ACCEPTED"
    assert success_data["store_name"] == store.name


@pytest.mark.django_db
def test_client_customers_api_endpoint(client, accounting_setup):
    from accounts.security import create_access_token
    setup = accounting_setup
    store = setup["store"]
    operator = setup["operator"]

    # Criar pedidos para gerar histórico de clientes finais
    Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        status="COMPLETED",
        fareValueCents=2500,
        metadata={
            "cliente_nome": "Carlos Cliente",
            "cliente_telefone": "11988887777",
            "entrega_endereco": "Av. Brasil, 500",
        },
    )
    Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        status="COMPLETED",
        fareValueCents=3500,
        metadata={
            "cliente_nome": "Carlos Cliente",
            "cliente_telefone": "11988887777",
            "entrega_endereco": "Av. Brasil, 500",
        },
    )

    token = create_access_token({
        "sub": "portal-test-1",
        "email": "cliente@loja.com",
        "role": "lojista",
        "operator_id": str(operator.id),
        "client_id": str(setup["client"].id),
    })

    # 1. List customers
    resp = client.get(
        "/api/v1/client/customers",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    carlos = next((c for c in data["customers"] if "Carlos" in c["name"]), None)
    assert carlos is not None
    assert carlos["orders_count"] == 2
    assert carlos["total_spent_reais"] == 60.00
    assert carlos["ticket_medio_reais"] == 30.00

    # 2. Create customer via POST
    create_resp = client.post(
        "/api/v1/client/customers",
        data={
            "name": "Ana Paula",
            "phone": "11977776666",
            "address": "Rua Augusta",
            "number": "1200",
            "neighborhood": "Consolação",
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["success"] is True
    assert create_data["customer"]["name"] == "Ana Paula"
    assert "Rua Augusta" in create_data["customer"]["address"]




