import json
import uuid
import pytest
from django.test import Client
from django.db import connection
from accounts.models import Operator, PlatformAdmin, StaffMember
from logistics.models import Client as LogisticsClient, ClientPortalUser, Store
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
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    yield


@pytest.fixture
def operator_fixture(db):
    return Operator.objects.create(
        id=uuid.uuid4(),
        name="Expresso Central Hub",
        status=Operator.OperatorStatus.ACTIVE,
    )


@pytest.fixture
def platform_admin_fixture(db):
    admin = PlatformAdmin(
        id=uuid.uuid4(),
        name="Super Admin Master",
        email="master@expressoneves.com.br",
    )
    admin.set_password("Master123@#")
    admin.save()
    return admin


@pytest.fixture
def operator_admin_staff_fixture(db, operator_fixture):
    staff = StaffMember(
        id=uuid.uuid4(),
        operator=operator_fixture,
        name="Gerente Admin da Central",
        email="gerente@central.com.br",
        role=StaffMember.RoleType.ADMIN,
        active=True,
    )
    staff.set_password("Gerente123@#")
    staff.save()
    return staff


@pytest.fixture
def client_lojista_fixture(db, operator_fixture):
    client_obj = LogisticsClient.objects.create(
        id=uuid.uuid4(),
        operator=operator_fixture,
        name="Restaurante Bom Sabor",
        document="12345678000199",
        active=True,
    )
    store_id = uuid.uuid4()
    with connection.cursor() as cur:
        cur.execute(
            'INSERT INTO "Store" (id, operator_id, client_id, name, "averagePrepTimeMinutes", operational) VALUES (%s, %s, %s, %s, 15, 1)',
            [str(store_id).replace("-", ""), str(operator_fixture.id).replace("-", ""), str(client_obj.id).replace("-", ""), "Bom Sabor - Matriz"]
        )
    user = ClientPortalUser(
        id=uuid.uuid4(),
        operator=operator_fixture,
        client=client_obj,
        name="João Lojista",
        email="lojista@bomsabor.com.br",
    )
    user.set_password("Lojista123@#")
    user.save()
    return user, client_obj, store_id


@pytest.mark.django_db
def test_login_superadmin_tier(client: Client, platform_admin_fixture):
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({"email": "master@expressoneves.com.br", "password": "Master123@#"}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["user"]["is_platform_admin"] is True
    assert data["user"]["role"] == "superadmin"
    assert data["user"]["user_type"] == "platform_admin"


@pytest.mark.django_db
def test_login_operator_admin_tier(client: Client, operator_admin_staff_fixture):
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({"email": "gerente@central.com.br", "password": "Gerente123@#"}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["user"]["is_platform_admin"] is False
    assert data["user"]["role"] == "operador_admin"
    assert data["user"]["user_type"] == "operator_staff"


@pytest.mark.django_db
def test_login_client_portal_user_tier(client: Client, client_lojista_fixture):
    user, client_obj, store_id = client_lojista_fixture
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({"email": "lojista@bomsabor.com.br", "password": "Lojista123@#"}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["user"]["is_platform_admin"] is False
    assert data["user"]["role"] == "lojista"
    assert data["user"]["user_type"] == "client_portal_user"
    assert data["user"]["client_id"] == str(client_obj.id)
    assert len(data["user"]["companies"]) == 1
    assert data["user"]["companies"][0]["id"] in (str(store_id), str(store_id).replace("-", ""))


@pytest.mark.django_db
def test_auth_me_client_portal_user(client: Client, client_lojista_fixture):
    user, client_obj, store_id = client_lojista_fixture
    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": "lojista",
        "user_type": "client_portal_user",
        "is_platform_admin": False,
        "operator_id": str(user.operator_id),
        "client_id": str(client_obj.id),
    })
    resp = client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["authenticated"] is True
    assert data["user"]["role"] == "lojista"
    assert data["user"]["user_type"] == "client_portal_user"
    assert data["user"]["client_id"] == str(client_obj.id)


@pytest.mark.django_db
def test_auth_me_operator_admin(client: Client, operator_admin_staff_fixture):
    staff = operator_admin_staff_fixture
    token = create_access_token({
        "sub": str(staff.id),
        "email": staff.email,
        "role": "operador_admin",
        "user_type": "operator_staff",
        "is_platform_admin": False,
        "operator_id": str(staff.operator_id),
    })
    resp = client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["authenticated"] is True
    assert data["user"]["role"] == "operador_admin"
    assert data["user"]["user_type"] == "operator_staff"
    assert data["user"]["operator_id"] == str(staff.operator_id)
