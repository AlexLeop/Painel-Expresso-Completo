import json
import uuid
import pytest
from django.test import Client
from django.db import connection
from accounts.models import Operator, PlatformAdmin, StaffMember
from logistics.models import Client as LogisticsClient, ClientPortalUser, Driver
from accounts.security import create_access_token


@pytest.fixture(autouse=True)
def setup_test_tables(db):
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
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Driver" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                document VARCHAR(20),
                active BOOLEAN DEFAULT 1,
                "maxActiveOrders" INT DEFAULT 1,
                "pixKeyType" VARCHAR(20),
                "pixKey" VARCHAR(255),
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
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "email": "master@expressoneves.com.br",
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
def test_operator_saas_billing_crud_and_actions(client: Client):
    token = create_access_token({
        "sub": str(uuid.uuid4()),
        "email": "master@expressoneves.com.br",
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

