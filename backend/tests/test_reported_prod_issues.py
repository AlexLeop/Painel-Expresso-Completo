import json
import uuid
import pytest
from django.test import Client
from django.db import connection
from accounts.models import Operator, PlatformAdmin, StaffMember, OperatorBranding
from logistics.models import Store, Driver, Client as StoreClient, ClientPortalUser
from accounts.security import create_access_token


import importlib
from django.contrib.gis.db.models.proxy import SpatialProxy
setattr(SpatialProxy, "__set__", lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value))
setattr(SpatialProxy, "__get__", lambda self, instance, cls=None: instance.__dict__.get(self.field.attname) if instance else self)


@pytest.fixture(autouse=True)
def setup_tables(db, monkeypatch):
    import django.contrib.gis.geos as geos
    from django.contrib.gis.db.models.fields import PointField
    PointField.get_prep_value = lambda self, value: str(value) if value is not None else None
    PointField.get_db_prep_save = lambda self, value, connection: str(value) if value is not None else None
    PointField.get_db_prep_value = lambda self, value, connection, *args, **kwargs: str(value) if value is not None else None
    monkeypatch.setattr(geos, "Point", lambda lng, lat, srid=4326: f"POINT ({lng} {lat})")
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
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "PlatformAdmin" (
                id CHAR(32) PRIMARY KEY,
                supabase_uid CHAR(32),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                "passwordHash" VARCHAR(255),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                operational BOOLEAN DEFAULT 1,
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
            CREATE TABLE IF NOT EXISTS "ManualEntry" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32),
                store_id CHAR(32),
                created_by_staff_id CHAR(32),
                created_by_client_id CHAR(32),
                "amountCents" BIGINT NOT NULL,
                description TEXT NOT NULL,
                "visibleToStore" BOOLEAN NOT NULL DEFAULT 1,
                "taxCategory" VARCHAR(50) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'APPROVED',
                "rejectReason" TEXT,
                "approvedById" CHAR(32),
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
                external_order_id VARCHAR(255),
                external_source VARCHAR(50),
                metadata TEXT DEFAULT '{}',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WithdrawalRequest" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL,
                "amountCents" BIGINT NOT NULL,
                status VARCHAR(20) DEFAULT 'PAID',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "DailyCreditCalculation" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                "productionValueCents" BIGINT DEFAULT 0,
                "extrasCents" BIGINT DEFAULT 0,
                "dailyRateOrGuaranteedCents" BIGINT DEFAULT 0,
                "advancesCents" BIGINT DEFAULT 0,
                "netAmountCents" BIGINT DEFAULT 0,
                "failReason" TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WeeklyStoreInvoice" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                "totalCents" BIGINT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'PAID',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operator_branding (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL UNIQUE,
                brand_name VARCHAR(255) NOT NULL,
                logo_url TEXT,
                favicon_url TEXT,
                color_primary VARCHAR(7) DEFAULT '#6366f1',
                color_secondary VARCHAR(7) DEFAULT '#4f46e5',
                color_accent VARCHAR(7) DEFAULT '#f59e0b',
                color_background VARCHAR(7) DEFAULT '#ffffff',
                color_surface VARCHAR(7) DEFAULT '#f8fafc',
                color_text VARCHAR(7) DEFAULT '#0f172a',
                dark_color_background VARCHAR(7) DEFAULT '#090d16',
                dark_color_surface VARCHAR(7) DEFAULT '#111827',
                dark_color_text VARCHAR(7) DEFAULT '#f8fafc',
                theme_mode VARCHAR(10) DEFAULT 'light',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "ClientPortalUser" (
                id CHAR(32) PRIMARY KEY,
                supabase_uid CHAR(32),
                operator_id CHAR(32) NOT NULL,
                client_id CHAR(32) NOT NULL,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                "passwordHash" VARCHAR(255),
                role VARCHAR(50) NOT NULL DEFAULT 'lojista',
                active BOOLEAN NOT NULL DEFAULT 1,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Contract" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                "compensationMode" VARCHAR(20) DEFAULT 'GARANTIDA',
                "rideFeePerDeliveryCents" INT DEFAULT 160,
                "minimumRidesFeeFloorCents" INT DEFAULT 35000,
                "minimumFloorBps" INT DEFAULT 0,
                "adminTaxThresholdCents" INT DEFAULT 0,
                "adminTaxFixedAmountCents" INT DEFAULT 0,
                "adminTaxBps" INT DEFAULT 0,
                "supervisionFeePerWeekCents" INT DEFAULT 0,
                "dailyRateWeekdayCents" INT DEFAULT 6000,
                "dailyRateSaturdayCents" INT DEFAULT 0,
                "dailyRateSundayCents" INT DEFAULT 0,
                "dailyRateHolidayCents" INT DEFAULT 0,
                "kmExcedenteValorCents" INT DEFAULT 0,
                "allowAutomaticGrouping" BOOLEAN DEFAULT 1,
                "cloudOverflowAllowed" BOOLEAN DEFAULT 0,
                "maxStopsPerManifest" INT DEFAULT 3,
                "maxDetourPercent" INT DEFAULT 20,
                "cutoffHour" INT DEFAULT 2,
                "cutoffMinute" INT DEFAULT 0,
                "returnFeeBps" INT DEFAULT 5000,
                "overridePayoutPolicy" BOOLEAN DEFAULT 0,
                "customPayoutMode" VARCHAR(30),
                "customAutoThresholdCents" BIGINT,
                "customFeeMode" VARCHAR(30),
                "customFeeCents" BIGINT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    yield


@pytest.fixture
def sample_data(db):
    op = Operator.objects.create(id=uuid.uuid4(), name="Alpha Express", status="ACTIVE")
    store = Store.objects.create(id=uuid.uuid4(), operator=op, name="Loja 1", operational=True)
    driver = Driver.objects.create(id=uuid.uuid4(), operator=op, name="Driver 1", phone="11999999999", active=True)
    staff = StaffMember.objects.create(
        id=uuid.uuid4(), operator=op, name="Op Manager", email="manager@alpha.com", role="ADMIN", active=True
    )
    admin = PlatformAdmin.objects.create(
        id=uuid.uuid4(), name="Platform Master", email="master@platform.com"
    )
    admin_token = create_access_token({
        "sub": str(admin.id),
        "email": admin.email,
        "is_platform_admin": True,
        "role": "SUPERADMIN",
    })
    return {
        "operator": op,
        "store": store,
        "driver": driver,
        "staff": staff,
        "admin": admin,
        "admin_token": admin_token,
    }


@pytest.mark.django_db
def test_db_configs_company_id_nan(client: Client, sample_data):
    token = sample_data["admin_token"]
    resp = client.get("/api/v1/db/configs?company_id=NaN", HTTP_AUTHORIZATION=f"Bearer {token}")
    # Should NOT be 500!
    assert resp.status_code != 500


@pytest.mark.django_db
def test_db_configs_company_id_global(client: Client, sample_data):
    token = sample_data["admin_token"]
    resp = client.get("/api/v1/db/configs?company_id=global", HTTP_AUTHORIZATION=f"Bearer {token}")
    # Should NOT be 500!
    assert resp.status_code != 500


@pytest.mark.django_db
def test_branding_platform_admin_global_and_multi_tenant_isolation(client: Client, sample_data):
    from accounts.models_branding import OperatorBranding

    op = sample_data["operator"]
    admin_token = sample_data["admin_token"]
    staff_token = create_access_token({
        "sub": str(sample_data["staff"].id),
        "operator_id": str(op.id),
        "role": "ADMIN",
        "email": sample_data["staff"].email,
    })

    # 1. Operador logístico customiza o nome da sua empresa (White-Label)
    OperatorBranding.objects.create(
        id=uuid.uuid4(),
        operator=op,
        brand_name="Transportadora Silva Exclusiva",
        color_primary="#123456",
    )

    # 2. Operador autenticado busca seu próprio branding
    resp_op = client.get("/api/v1/branding/", HTTP_AUTHORIZATION=f"Bearer {staff_token}")
    assert resp_op.status_code == 200
    assert resp_op.json()["brand_name"] == "Transportadora Silva Exclusiva"
    assert resp_op.json()["operator_id"] == str(op.id)

    # 3. Proprietário do sistema (PlatformAdmin) no painel global NÃO pode receber a marca do operador!
    # Deve receber estritamente a identidade oficial da plataforma ("Expresso Neves").
    resp_admin = client.get("/api/v1/branding/", HTTP_AUTHORIZATION=f"Bearer {admin_token}")
    assert resp_admin.status_code == 200
    assert resp_admin.json()["brand_name"] == "Expresso Neves"
    assert resp_admin.json()["brand_name"] != "Transportadora Silva Exclusiva"
    assert resp_admin.json()["operator_id"] == "global"

    # 4. PlatformAdmin inspecionando especificamente o operador (via header X-Operator-Id)
    resp_admin_scoped = client.get(
        "/api/v1/branding/",
        HTTP_AUTHORIZATION=f"Bearer {admin_token}",
        HTTP_X_OPERATOR_ID=str(op.id),
    )
    assert resp_admin_scoped.status_code == 200
    assert resp_admin_scoped.json()["brand_name"] == "Transportadora Silva Exclusiva"



@pytest.mark.django_db
def test_integration_platform_admin(client: Client, sample_data):
    token = sample_data["admin_token"]
    resp = client.get("/api/v1/integration/", HTTP_AUTHORIZATION=f"Bearer {token}")
    # MUST NOT be 401 Unauthorized for authenticated platform admin!
    assert resp.status_code != 401
    assert resp.status_code == 200


@pytest.mark.django_db
def test_adjust_store_balance_platform_admin(client: Client, sample_data):
    token = sample_data["admin_token"]
    store = sample_data["store"]
    payload = {
        "store_id": str(store.id),
        "amount_cents": 5000,
        "direction": "CREDIT",
        "category": "ADJUSTMENT",
        "reason": "Crédito manual pelo Admin Global",
    }
    resp = client.post(
        "/api/v1/operator/adjust-store-balance",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    # Should NOT be 500!
    assert resp.status_code == 200


@pytest.mark.django_db
def test_financial_dashboard_platform_admin_global(client: Client, sample_data):
    token = sample_data["admin_token"]
    resp = client.get("/api/v1/operator/financial-dashboard?month=2026-09", HTTP_AUTHORIZATION=f"Bearer {token}")
    # MUST NOT be 422 Unprocessable Content for PlatformAdmin!
    assert resp.status_code == 200
    data = resp.json()
    assert "month_label" in data
    assert "receita_bruta_reais" in data
    assert "plataforma_billing" in data


@pytest.mark.django_db
def test_cash_reconciliation_platform_admin_global(client: Client, sample_data):
    token = sample_data["admin_token"]
    resp = client.get("/api/v1/operator/cash-reconciliation", HTTP_AUTHORIZATION=f"Bearer {token}")
    # MUST NOT be 422 Unprocessable Content for PlatformAdmin!
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "drivers" in data


@pytest.mark.django_db
def test_credit_queue_with_processing_status_and_global(client: Client, sample_data):
    token = sample_data["admin_token"]
    # Passing status with 'processing' which is not directly in daily_credit_status enum
    resp = client.get(
        "/api/v1/db/credit-queue?company_id=global&status=pending%2Cprocessing%2Cfailed",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    # MUST NOT be 500 Internal Server Error!
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.django_db
def test_credit_queue_with_nan_company_id(client: Client, sample_data):
    token = sample_data["admin_token"]
    resp = client.get(
        "/api/v1/db/credit-queue?company_id=NaN&status=pending%2Cprocessing%2Cfailed",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    # MUST NOT be 500 Internal Server Error!
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.django_db
def test_store_creation_with_manager_and_store_operator_flow(client: Client, sample_data, monkeypatch):
    """
    Testa a hierarquia completa de 4 níveis:
    1. PlatformAdmin (Proprietário Global)
    2. Operador Logístico (B2B Tenant)
    3. Lojista (Gestor da Loja Parceira)
    4. Operador da Loja (Funcionário da loja que opera o delivery)

    Garante também que o branding do Operador é herdado pelo Lojista e Operador da Loja (White-label).
    """
    import sys
    import importlib
    geos = importlib.import_module("django.contrib.gis.geos")
    monkeypatch.setattr(geos, "Point", lambda lng, lat, srid=4326: f"POINT ({lng} {lat})")
    if not hasattr(connection.ops, "select"):
        setattr(connection.ops, "select", "%s")
    if not hasattr(connection.ops, "get_geom_placeholder"):
        setattr(connection.ops, "get_geom_placeholder", lambda f, v, c: "%s")

    op = sample_data["operator"]
    staff = sample_data["staff"]
    staff_token = create_access_token({
        "sub": str(staff.id),
        "operator_id": str(op.id),
        "email": staff.email,
        "role": "ADMIN",
    })

    # 1. Operador logístico cadastra uma Loja Parceira definindo o Gestor da Loja
    payload_store = {
        "name": "Pizzaria Napoli",
        "documento": "12.345.678/0001-90",
        "endereco": "Rua das Pizzas, 100, Centro",
        "telefone": "31999998888",
        "lat": -19.9200,
        "lng": -43.9400,
        "averagePrepTimeMinutes": 20,
        "managerName": "Carlos Napoli",
        "managerEmail": "carlos@napoli.com",
        "managerPassword": "SenhaSegura123",
        "managerPhone": "31999998888",
    }
    resp_store = client.post(
        "/api/v1/db/companies",
        data=json.dumps(payload_store),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {staff_token}",
    )
    assert resp_store.status_code == 200, f"Error: {resp_store.json()}"
    store_data = resp_store.json()
    assert store_data["success"] is True
    assert "storeId" in store_data
    assert "managerId" in store_data

    # Verifica que o Gestor da Loja foi criado com papel 'lojista'
    manager = ClientPortalUser.objects.get(id=store_data["managerId"])
    assert manager.role == "lojista"
    assert manager.email == "carlos@napoli.com"
    assert manager.name == "Carlos Napoli"
    assert manager.check_password("SenhaSegura123") is True

    # Token de autenticação do Lojista (Gestor da Loja)
    lojista_token = create_access_token({
        "sub": str(manager.id),
        "user_type": "client_portal_user",
        "client_id": str(manager.client_id),
        "operator_id": str(op.id),
        "email": manager.email,
        "role": manager.role,
    })

    # 2. Lojista consulta a equipe da sua loja (GET /api/v1/db/users)
    resp_users = client.get(
        "/api/v1/db/users",
        HTTP_AUTHORIZATION=f"Bearer {lojista_token}",
    )
    assert resp_users.status_code == 200
    team = resp_users.json()
    assert len(team) == 1
    assert team[0]["email"] == "carlos@napoli.com"
    assert team[0]["role"] == "lojista"

    # 3. Lojista cadastra um Operador da Loja (funcionário da loja)
    payload_operator = {
        "fullName": "Mariana Operadora",
        "email": "mariana@napoli.com",
        "password": "SenhaOperador123",
        "role": "operador_loja",
    }
    resp_create_op = client.post(
        "/api/v1/db/users",
        data=json.dumps(payload_operator),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {lojista_token}",
    )
    assert resp_create_op.status_code == 200
    create_op_data = resp_create_op.json()
    assert create_op_data["success"] is True

    operador = ClientPortalUser.objects.get(email="mariana@napoli.com")
    assert operador.role == "operador_loja"
    assert operador.client_id == manager.client_id
    assert operador.operator_id == op.id

    # Lista de equipe agora contém 2 membros para o Gestor da Loja
    resp_team_updated = client.get(
        "/api/v1/db/users",
        HTTP_AUTHORIZATION=f"Bearer {lojista_token}",
    )
    assert resp_team_updated.status_code == 200
    team_updated = resp_team_updated.json()
    assert len(team_updated) == 2

    # Token do Operador da Loja (funcionário)
    operador_token = create_access_token({
        "sub": str(operador.id),
        "user_type": "client_portal_user",
        "client_id": str(operador.client_id),
        "operator_id": str(op.id),
        "email": operador.email,
        "role": operador.role,
    })

    # 4. Operador da Loja NÃO tem permissão de gerenciar usuários da loja
    resp_op_list = client.get(
        "/api/v1/db/users",
        HTTP_AUTHORIZATION=f"Bearer {operador_token}",
    )
    assert resp_op_list.status_code == 200
    assert resp_op_list.json() == []

    resp_op_create = client.post(
        "/api/v1/db/users",
        data=json.dumps({"fullName": "Invasor", "email": "inv@napoli.com", "password": "123456", "role": "operador_loja"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {operador_token}",
    )
    assert resp_op_create.status_code == 403

    # 5. White-label: Tanto o Lojista quanto o Operador da Loja recebem o branding do Operador Logístico
    OperatorBranding.objects.create(
        id=uuid.uuid4(),
        operator=op,
        brand_name="Neves Express Logística",
    )
    resp_branding_lojista = client.get(
        "/api/v1/branding/",
        HTTP_AUTHORIZATION=f"Bearer {lojista_token}",
    )
    assert resp_branding_lojista.status_code == 200
    assert resp_branding_lojista.json()["brand_name"] == "Neves Express Logística"

    resp_branding_operador = client.get(
        "/api/v1/branding/",
        HTTP_AUTHORIZATION=f"Bearer {operador_token}",
    )
    assert resp_branding_operador.status_code == 200
    assert resp_branding_operador.json()["brand_name"] == "Neves Express Logística"


