import json
import uuid
import pytest
from django.test import Client
from django.db import connection
from accounts.models import Operator, PlatformAdmin, StaffMember
from logistics.models import Client as LogisticsClient, ClientPortalUser, Driver
from accounts.security import create_access_token


@pytest.fixture(autouse=True)
def setup_test_tables(db, monkeypatch):
    from django.contrib.gis.db.models.proxy import SpatialProxy

    monkeypatch.setattr(
        SpatialProxy,
        "__set__",
        lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value),
    )
    monkeypatch.setattr(
        SpatialProxy,
        "__get__",
        lambda self, instance, cls=None: instance.__dict__.get(self.field.attname)
        if instance
        else self,
    )
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
            CREATE TABLE IF NOT EXISTS "ClientPortalUser" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                client_id CHAR(32) NOT NULL,
                supabase_uid CHAR(32),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                "passwordHash" VARCHAR(255),
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
            CREATE TABLE IF NOT EXISTS "SecurityDenylist" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                "targetId" CHAR(32) NOT NULL,
                "targetType" VARCHAR(50) NOT NULL,
                reason TEXT NOT NULL,
                "blockedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "expiresAt" TIMESTAMP
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
                metadata TEXT DEFAULT '{}',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "StoreDriver" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Vehicle" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                plate VARCHAR(10) UNIQUE NOT NULL,
                type VARCHAR(20) DEFAULT 'MOTORCYCLE',
                active BOOLEAN DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "OperatorAuditLog" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                "platformAdminId" CHAR(32) NOT NULL,
                action VARCHAR(100) NOT NULL,
                "previousStatus" VARCHAR(20),
                "newStatus" VARCHAR(20),
                reason TEXT NOT NULL,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    yield


@pytest.mark.django_db
def test_operator_staff_cannot_access_operators_list(client: Client):
    operator = Operator.objects.create(id=uuid.uuid4(), name="Op Test", status="ACTIVE")
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "email": "gerente@op.com",
        "role": "operador_admin",
        "user_type": "operator_staff",
        "is_platform_admin": False,
        "operator_id": str(operator.id),
    })

    resp = client.get("/api/admin/operators", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_superadmin_can_access_operators_list(client: Client):
    admin = PlatformAdmin.objects.create(
        id=uuid.uuid4(), name="Master", email="master@expressoneves.com.br"
    )
    token = create_access_token({
        "sub": str(admin.id),
        "email": admin.email,
        "role": "superadmin",
        "user_type": "platform_admin",
        "is_platform_admin": True,
        "operator_id": None,
    })

    resp = client.get("/api/admin/operators", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_operator_staff_only_sees_own_users(client: Client):
    op1 = Operator.objects.create(id=uuid.uuid4(), name="Op 1", status="ACTIVE")
    op2 = Operator.objects.create(id=uuid.uuid4(), name="Op 2", status="ACTIVE")

    s1 = StaffMember.objects.create(id=uuid.uuid4(), operator=op1, name="Staff 1", email="s1@op1.com", role="ADMIN")
    s2 = StaffMember.objects.create(id=uuid.uuid4(), operator=op2, name="Staff 2", email="s2@op2.com", role="ADMIN")

    token = create_access_token({
        "sub": str(s1.id),
        "email": s1.email,
        "role": "operador_admin",
        "user_type": "operator_staff",
        "is_platform_admin": False,
        "operator_id": str(op1.id),
    })

    resp = client.get("/api/v1/db/users", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    emails = [u["email"] for u in data]
    assert "s1@op1.com" in emails
    assert "s2@op2.com" not in emails


@pytest.mark.django_db
def test_operator_admin_cannot_update_or_revoke_foreign_tenant_user(client: Client):
    op1 = Operator.objects.create(id=uuid.uuid4(), name="Operador A", status="ACTIVE")
    op2 = Operator.objects.create(id=uuid.uuid4(), name="Operador B", status="ACTIVE")
    actor = StaffMember.objects.create(
        id=uuid.uuid4(), operator=op1, name="Admin A", email="admin-a@example.com",
        role="ADMIN", active=True,
    )
    foreign = StaffMember.objects.create(
        id=uuid.uuid4(), operator=op2, name="Admin B", email="admin-b@example.com",
        role="ADMIN", active=True,
    )
    token = create_access_token({
        "sub": str(actor.id), "email": actor.email, "role": "ADMIN",
        "user_type": "operator_staff", "is_platform_admin": False,
        "operator_id": str(op1.id),
    })
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    response = client.put(
        "/api/v1/db/users",
        data=json.dumps({"id": str(foreign.id), "fullName": "Invadido"}),
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 404

    response = client.delete(f"/api/v1/db/users?id={foreign.id}", **headers)
    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.name == "Admin B"
    assert foreign.active is True


@pytest.mark.django_db
def test_user_creation_requires_explicit_strong_password(client: Client):
    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador Seguro", status="ACTIVE")
    actor = StaffMember.objects.create(
        id=uuid.uuid4(), operator=operator, name="Admin", email="admin@example.com",
        role="ADMIN", active=True,
    )
    token = create_access_token({
        "sub": str(actor.id), "email": actor.email, "role": "ADMIN",
        "user_type": "operator_staff", "is_platform_admin": False,
        "operator_id": str(operator.id),
    })

    response = client.post(
        "/api/v1/db/users",
        data=json.dumps({
            "fullName": "Novo usuário", "email": "novo@example.com",
            "role": "operator", "password": "123456",
        }),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 422
    assert not StaffMember.objects.filter(email="novo@example.com").exists()


@pytest.mark.django_db
def test_client_portal_user_gets_empty_user_list(client: Client):
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "email": "lojista@loja.com",
        "role": "lojista",
        "user_type": "client_portal_user",
        "is_platform_admin": False,
        "client_id": str(uuid.uuid4()),
        "operator_id": str(uuid.uuid4()),
    })
    resp = client.get("/api/v1/db/users", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_operator_cannot_list_or_patch_driver_from_another_tenant(client: Client):
    op1 = Operator.objects.create(id=uuid.uuid4(), name="Op Isolada 1", status="ACTIVE")
    op2 = Operator.objects.create(id=uuid.uuid4(), name="Op Isolada 2", status="ACTIVE")
    staff = StaffMember.objects.create(
        id=uuid.uuid4(), operator=op1, name="Admin Op 1",
        email="admin-isolado@op1.com", role="ADMIN", active=True,
    )
    own_driver = Driver.objects.create(
        id=uuid.uuid4(), operator=op1, name="Motoboy Próprio", phone="11911111111",
        pixKeyType="TELEFONE", pixKey="11911111111", active=True,
    )
    foreign_driver = Driver.objects.create(
        id=uuid.uuid4(), operator=op2, name="Motoboy Externo", phone="11922222222",
        pixKeyType="TELEFONE", pixKey="11922222222", active=True,
    )
    token = create_access_token({
        "sub": str(staff.id), "email": staff.email, "role": "operador_admin",
        "user_type": "operator_staff", "is_platform_admin": False,
        "operator_id": str(op1.id),
    })
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    response = client.get(
        f"/api/v1/db/company-drivers?company_id={op2.id}", **headers
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(own_driver.id)]

    response = client.patch(
        "/api/v1/db/company-drivers",
        data=json.dumps({"driverId": str(foreign_driver.id), "active": False}),
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 404
    foreign_driver.refresh_from_db()
    assert foreign_driver.active is True


@pytest.mark.django_db
def test_operator_created_driver_is_forced_to_authenticated_tenant(client: Client):
    op1 = Operator.objects.create(id=uuid.uuid4(), name="Op Cadastro 1", status="ACTIVE")
    op2 = Operator.objects.create(id=uuid.uuid4(), name="Op Cadastro 2", status="ACTIVE")
    staff = StaffMember.objects.create(
        id=uuid.uuid4(), operator=op1, name="Admin Cadastro",
        email="cadastro@op1.com", role="ADMIN", active=True,
    )
    token = create_access_token({
        "sub": str(staff.id), "email": staff.email, "role": "operador_admin",
        "is_platform_admin": False, "operator_id": str(op1.id),
    })

    response = client.post(
        "/api/v1/db/company-drivers",
        data=json.dumps({
            "companyId": str(op2.id), "nome": "Novo Motoboy",
            "phone": "(11) 93333-4444", "email": "driver@example.com",
            "password": "senha-segura", "document": "123.456.789-01",
        }),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200, response.content
    driver = Driver.objects.get(id=response.json()["driverId"])
    assert driver.operator_id == op1.id
    assert driver.phone == "11933334444"
    assert driver.document == "12345678901"


@pytest.mark.django_db
def test_only_platform_owner_can_transfer_driver_and_transfer_is_audited(client: Client):
    op1 = Operator.objects.create(id=uuid.uuid4(), name="Origem", status="ACTIVE")
    op2 = Operator.objects.create(id=uuid.uuid4(), name="Destino", status="ACTIVE")
    staff = StaffMember.objects.create(
        id=uuid.uuid4(), operator=op1, name="Admin Origem",
        email="origem@example.com", role="ADMIN", active=True,
    )
    driver = Driver.objects.create(
        id=uuid.uuid4(), operator=op1, supabase_uid=uuid.uuid4(),
        name="Motoboy Transferível", phone="11955556666", document="98765432100",
        pixKeyType="TELEFONE", pixKey="11955556666", active=True,
    )
    staff_token = create_access_token({
        "sub": str(staff.id), "email": staff.email, "role": "operador_admin",
        "is_platform_admin": False, "operator_id": str(op1.id),
    })
    payload = {"targetCompanyId": str(op2.id), "reason": "Mudança contratual autorizada"}
    response = client.post(
        f"/api/v1/db/company-drivers/{driver.id}/transfer",
        data=json.dumps(payload), content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {staff_token}",
    )
    assert response.status_code == 403

    owner = PlatformAdmin.objects.create(
        id=uuid.uuid4(), supabase_uid=uuid.uuid4(), name="Proprietário",
        email="owner@example.com",
    )
    owner_token = create_access_token({
        "sub": str(owner.id), "email": owner.email, "role": "SUPERADMIN",
        "is_platform_admin": True, "operator_id": None,
    })
    response = client.post(
        f"/api/v1/db/company-drivers/{driver.id}/transfer",
        data=json.dumps(payload), content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {owner_token}",
    )
    assert response.status_code == 200, response.content
    driver.refresh_from_db()
    assert driver.active is False
    transferred = Driver.objects.get(id=response.json()["driverId"])
    assert transferred.operator_id == op2.id
    assert transferred.active is True
    from accounts.models import OperatorAuditLog
    audit = OperatorAuditLog.objects.get(action="DRIVER_OPERATOR_TRANSFER")
    assert str(driver.id) in audit.reason
    assert str(transferred.id) in audit.reason


@pytest.mark.django_db
def test_operator_saas_billing_crud_and_actions(client: Client):
    platform_admin = PlatformAdmin.objects.create(
        id=uuid.uuid4(), name="Master SaaS", email="master-saas@expressoneves.com.br"
    )
    token = create_access_token({
        "sub": str(platform_admin.id),
        "email": platform_admin.email,
        "role": "superadmin",
        "user_type": "platform_admin",
        "is_platform_admin": True,
        "operator_id": None,
    })

    # 1. Create operator with SaaS billing model
    create_payload = {
        "name": "Expresso Belo Horizonte",
        "cnpj": "12345678000199",
        "phone": "31999998888",
        "city": "Belo Horizonte",
        "state": "MG",
        "billingPlanType": "FIXED_MONTHLY",
        "billingRateValue": 890.0,
        "billingCycle": "MENSAL",
        "dueDay": 10,
        "trialDays": 14,
        "gracePeriodDays": 5,
        "notes": "Franquia Regional BH - Plano Fixo",
        "managerName": "Carlos Gerente",
        "managerEmail": "carlos@bhlog.com",
        "managerPassword": "initial_password_123"
    }
    resp = client.post(
        "/api/admin/operators",
        data=json.dumps(create_payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200, resp.content
    op_id = resp.json()["operatorId"]

    # 2. List operators and check enriched data
    resp = client.get("/api/admin/operators", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    operators = resp.json()
    created_op = next((o for o in operators if o["id"] == op_id), None)
    assert created_op is not None
    assert created_op["name"] == "Expresso Belo Horizonte"
    assert created_op["billingPlanType"] == "FIXED_MONTHLY"
    assert created_op["billingRateValue"] == 890.0
    assert created_op["managerEmail"] == "carlos@bhlog.com"
    assert created_op["status"] == "TRIAL"

    # 3. Get operator detail
    resp = client.get(f"/api/admin/operators/{op_id}", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == op_id
    assert detail["city"] == "Belo Horizonte"
    assert detail["notes"] == "Franquia Regional BH - Plano Fixo"

    # 4. Update operator billing plan to PERCENT_PER_DELIVERY
    update_payload = {
        "billingPlanType": "PERCENT_PER_DELIVERY",
        "billingRateValue": 3.5,
        "notes": "Alterado para 3.5% por corrida concluida"
    }
    resp = client.put(
        f"/api/admin/operators/{op_id}",
        data=json.dumps(update_payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 5. Patch status to ACTIVE
    resp = client.patch(
        f"/api/admin/operators/{op_id}/status",
        data=json.dumps({"status": "ACTIVE"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["newStatus"] == "ACTIVE"

    # 6. Reset manager password
    resp = client.post(
        f"/api/admin/operators/{op_id}/reset-password",
        data=json.dumps({"newPassword": "new_secure_pwd_2026"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.django_db
def test_dashboard_stats_endpoint_metrics(client):
    from accounts.models import Operator
    from logistics.models import Store, Driver, Order
    from accounts.security import create_access_token
    from django.contrib.gis.db.models.proxy import SpatialProxy

    setattr(SpatialProxy, "__set__", lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value))
    setattr(SpatialProxy, "__get__", lambda self, instance, cls=None: instance.__dict__.get(self.field.attname) if instance else self)

    op = Operator.objects.create(id=uuid.uuid4(), name="Dashboard Operator", cnpj="99888777000199", status="ACTIVE")
    store = Store.objects.create(id=uuid.uuid4(), operator=op, name="Pizzaria Central", operational=True)
    driver = Driver.objects.create(id=uuid.uuid4(), operator=op, name="Carlos Motoboy", active=True)
    
    Order.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        driver=driver,
        status=Order.OrderStatus.COMPLETED,
        fareValueCents=2500,
    )
    Order.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        driver=driver,
        status=Order.OrderStatus.STARTED,
        fareValueCents=1800,
    )

    admin = PlatformAdmin.objects.create(
        id=uuid.uuid4(), name="Master Dashboard", email="master-dashboard@expressoneves.com.br"
    )
    token = create_access_token({
        "sub": str(admin.id),
        "email": admin.email,
        "is_platform_admin": True,
        "role": "SUPERADMIN",
    })

    resp = client.get(
        "/api/v1/db/dashboard-stats?range=last7",
        HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["faturamento_total"] >= 25.0
    assert data["completed_orders"] >= 1
    assert data["active_orders"] >= 1
    assert data["active_stores"] >= 1
    assert data["active_drivers"] >= 1
    assert len(data["chart_data"]) == 7
    assert len(data["top_stores"]) >= 1
    assert data["top_stores"][0]["nome"] == "Pizzaria Central"
