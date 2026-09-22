import pytest
import uuid
from django.db import connection
from django.test import Client as DjangoClient
from accounts.models import Operator, StaffMember
from logistics.models import Driver
from finance.models import Wallet, OperatorInternalWallet, WalletTransaction
from accounts.security import create_access_token


@pytest.fixture(autouse=True)
def setup_driver_wallet_tables(db):
    if not hasattr(connection.ops, "select"):
        setattr(connection.ops, "select", "%s")
    if not hasattr(connection.ops, "get_geom_placeholder"):
        setattr(connection.ops, "get_geom_placeholder", lambda f, v, c: "%s")

    from django.contrib.gis.db.models.proxy import SpatialProxy
    setattr(SpatialProxy, "__set__", lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value))
    setattr(SpatialProxy, "__get__", lambda self, instance, cls=None: instance.__dict__.get(self.field.attname) if instance else self)


    with connection.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Operator" (
                id CHAR(32) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                cnpj VARCHAR(14),
                phone VARCHAR(50),
                city VARCHAR(100),
                state VARCHAR(10),
                "billingPlanType" VARCHAR(50) DEFAULT 'PERCENT_PER_DELIVERY',
                "billingRateValue" NUMERIC(10,2) DEFAULT 0.00,
                "billingCycle" VARCHAR(30) DEFAULT 'MENSAL',
                "dueDay" INTEGER DEFAULT 10,
                "trialDays" INTEGER DEFAULT 14,
                "gracePeriodDays" INTEGER DEFAULT 5,
                notes TEXT,
                "platformCostPerDeliveryCents" INTEGER DEFAULT 40,
                "platformMinMonthlyFloorCents" INTEGER DEFAULT 29900,
                "platformVolumeTiers" TEXT DEFAULT '[]',
                status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
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
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Vehicle" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                plate VARCHAR(20) NOT NULL,
                type VARCHAR(50) DEFAULT 'MOTORCYCLE',
                model VARCHAR(100),
                year INTEGER,
                active BOOLEAN DEFAULT 1
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Wallet" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL UNIQUE,
                "balanceCents" BIGINT NOT NULL DEFAULT 0,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "OperatorInternalWallet" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL UNIQUE,
                "balanceCents" BIGINT NOT NULL DEFAULT 0,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WalletTransaction" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                source_driver_wallet_id CHAR(32),
                destination_driver_wallet_id CHAR(32),
                source_operator_wallet_id CHAR(32),
                destination_operator_wallet_id CHAR(32),
                "amountCents" BIGINT NOT NULL,
                category VARCHAR(50) NOT NULL,
                "taxCategory" VARCHAR(50) NOT NULL,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
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
                description TEXT,
                notes TEXT,
                "visibleToStore" BOOLEAN DEFAULT 1,
                "taxCategory" VARCHAR(50) DEFAULT 'TAXABLE_INCOME',
                status VARCHAR(30) DEFAULT 'APPROVED',
                "rejectReason" TEXT,
                "approvedById" CHAR(32),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # SQLite Trigger to simulate PostgreSQL process_wallet_transaction()
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_test_wallet_tx AFTER INSERT ON "WalletTransaction"
            BEGIN
                UPDATE "Wallet"
                SET "balanceCents" = "balanceCents" - NEW."amountCents"
                WHERE id = NEW.source_driver_wallet_id;

                UPDATE "Wallet"
                SET "balanceCents" = "balanceCents" + NEW."amountCents"
                WHERE id = NEW.destination_driver_wallet_id;

                UPDATE "OperatorInternalWallet"
                SET "balanceCents" = "balanceCents" - NEW."amountCents"
                WHERE id = NEW.source_operator_wallet_id;

                UPDATE "OperatorInternalWallet"
                SET "balanceCents" = "balanceCents" + NEW."amountCents"
                WHERE id = NEW.destination_operator_wallet_id;
            END;
        """)
    yield


@pytest.fixture
def wallet_test_data(db):
    op = Operator.objects.create(id=uuid.uuid4(), name="Operador Teste")
    driver1 = Driver.objects.create(
        id=uuid.uuid4(),
        operator=op,
        name="Carlos Motoboy",
        phone="61999990001",
        pixKey="61999990001",
        pixKeyType="TELEFONE",
        active=True,
    )
    driver2 = Driver.objects.create(
        id=uuid.uuid4(),
        operator=op,
        name="Bruno Entregador",
        phone="61999990002",
        active=True,
    )

    token_operator = create_access_token({
        "sub": str(uuid.uuid4()),
        "role": "operador_admin",
        "is_platform_admin": False,
        "operator_id": str(op.id),
    })

    token_admin = create_access_token({
        "sub": str(uuid.uuid4()),
        "role": "superadmin",
        "is_platform_admin": True,
        "operator_id": None,
    })

    return {
        "operator": op,
        "driver1": driver1,
        "driver2": driver2,
        "token_operator": token_operator,
        "token_admin": token_admin,
    }


def test_get_operator_driver_wallets(wallet_test_data):
    client = DjangoClient()
    token = wallet_test_data["token_operator"]
    resp = client.get("/api/v1/operator/driver-wallets", HTTP_AUTHORIZATION=f"Bearer {token}")

    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data
    assert "drivers" in data
    assert len(data["drivers"]) == 2
    assert data["kpis"]["total_motoboys"] == 2


def test_adjust_driver_wallet_credit_and_debit(wallet_test_data):
    client = DjangoClient()
    token = wallet_test_data["token_operator"]
    driver1 = wallet_test_data["driver1"]

    # 1. Lançar Bônus de R$ 50,00 (CREDIT)
    credit_payload = {
        "driver_id": str(driver1.id),
        "amount_cents": 5000,
        "direction": "CREDIT",
        "category": "BONUS",
        "reason": "Bônus por produtividade domingo à noite",
    }
    resp1 = client.post(
        "/api/v1/operator/driver-wallet/adjust",
        data=credit_payload,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["success"] is True
    assert data1["new_balance_cents"] == 5000
    assert data1["new_balance_reais"] == 50.0

    # 2. Lançar Adiantamento / Vale de R$ 20,00 (DEBIT)
    debit_payload = {
        "driver_id": str(driver1.id),
        "amount_cents": 2000,
        "direction": "DEBIT",
        "category": "ADVANCE",
        "reason": "Adiantamento para combustível",
    }
    resp2 = client.post(
        "/api/v1/operator/driver-wallet/adjust",
        data=debit_payload,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    # Saldo deve ser 50 - 20 = 30
    assert data2["new_balance_cents"] == 3000
    assert data2["new_balance_reais"] == 30.0

    # 3. Consultar Extrato (Transactions)
    resp3 = client.get(
        f"/api/v1/operator/driver-wallet/transactions?driver_id={driver1.id}",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert len(data3["transactions"]) == 2
    # Transação mais recente é o DEBIT de R$ 20
    tx_recent = data3["transactions"][0]
    assert tx_recent["direction"] == "DEBIT"
    assert tx_recent["amount_cents"] == 2000
    assert tx_recent["category"] == "ADVANCE"


def test_adjust_driver_wallet_validations(wallet_test_data):
    client = DjangoClient()
    token = wallet_test_data["token_operator"]
    driver1 = wallet_test_data["driver1"]

    # Valor zero ou negativo deve falhar com 400
    resp = client.post(
        "/api/v1/operator/driver-wallet/adjust",
        data={
            "driver_id": str(driver1.id),
            "amount_cents": -500,
            "direction": "CREDIT",
            "reason": "Teste inválido",
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp.status_code == 400

    # Sem justificativa deve falhar com 400
    resp2 = client.post(
        "/api/v1/operator/driver-wallet/adjust",
        data={
            "driver_id": str(driver1.id),
            "amount_cents": 1000,
            "direction": "CREDIT",
            "reason": "",
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp2.status_code == 400
