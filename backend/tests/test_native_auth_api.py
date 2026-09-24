import json
import uuid
import pytest
from django.test import Client
from django.db import connection
from accounts.models import Operator, PlatformAdmin, StaffMember
from accounts.security import hash_password, create_access_token, create_refresh_token

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
                supabase_uid CHAR(32) UNIQUE NOT NULL,
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
        name="Expresso Central Test",
        status=Operator.OperatorStatus.ACTIVE,
    )


@pytest.fixture
def platform_admin_fixture(db):
    admin = PlatformAdmin(
        id=uuid.uuid4(),
        name="Super Admin Master",
        email="master@expressoneves.com.br",
    )
    admin.set_password("MasterPassword123@#")
    admin.save()
    return admin


@pytest.fixture
def staff_member_fixture(db, operator_fixture):
    staff = StaffMember(
        id=uuid.uuid4(),
        operator=operator_fixture,
        name="Operador Despacho",
        email="staff@expressoneves.com.br",
        role=StaffMember.RoleType.OPERATOR_ROLE,
        active=True,
    )
    staff.set_password("StaffPassword123@#")
    staff.save()
    return staff


@pytest.mark.django_db
def test_login_as_platform_admin_success(client: Client, platform_admin_fixture):
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({
            "email": "master@expressoneves.com.br",
            "password": "MasterPassword123@#",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert resp.cookies["neves_refresh"]["httponly"] is True
    assert data["user"]["role"] in ("admin", "platform_admin", "superadmin")


@pytest.mark.django_db
def test_login_as_staff_member_success(client: Client, staff_member_fixture):
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({
            "email": "staff@expressoneves.com.br",
            "password": "StaffPassword123@#",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "staff@expressoneves.com.br"
    assert data["user"]["is_platform_admin"] is False
    assert data["user"]["operator_id"] == str(staff_member_fixture.operator_id)


@pytest.mark.django_db
def test_login_bad_credentials(client: Client, platform_admin_fixture):
    # Wrong password
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({
            "email": "master@expressoneves.com.br",
            "password": "WrongPassword!",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401

    # Non existent email
    resp = client.post(
        "/api/auth/login",
        data=json.dumps({
            "email": "ghost@expressoneves.com.br",
            "password": "AnyPassword",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_auth_me_platform_admin_with_companies_list(client: Client, platform_admin_fixture, operator_fixture):
    token = create_access_token({
        "sub": str(platform_admin_fixture.id),
        "email": platform_admin_fixture.email,
        "role": "platform_admin",
        "is_platform_admin": True,
        "operator_id": None,
    })

    resp = client.get(
        "/api/auth/me",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == platform_admin_fixture.email
    # PlatformAdmin must receive list of companies including 'global' and all operators for tenant switching
    assert "companies" in data["user"]
    companies = data["user"]["companies"]
    company_ids = [c["id"] for c in companies]
    assert "global" in company_ids
    assert str(operator_fixture.id) in company_ids


@pytest.mark.django_db
def test_superadmin_sovereignty_bypass(client: Client, platform_admin_fixture, operator_fixture):
    """
    Test that a PlatformAdmin token can access protected endpoints requiring specific roles
    due to sovereign bypass (is_platform_admin == True).
    """
    token = create_access_token({
        "sub": str(platform_admin_fixture.id),
        "email": platform_admin_fixture.email,
        "role": "platform_admin",
        "is_platform_admin": True,
        "operator_id": str(operator_fixture.id),
    })

    # Access an endpoint that requires specific staff roles
    resp = client.get(
        "/api/v1/operator/profile",
        HTTP_AUTHORIZATION=f"Bearer {token}",
        HTTP_X_OPERATOR_ID=str(operator_fixture.id),
    )
    # Shouldn't fail with 403 Forbidden!
    assert resp.status_code != 403


@pytest.mark.django_db
def test_refresh_token_cannot_authenticate_protected_endpoint(client: Client, platform_admin_fixture):
    refresh = create_refresh_token({"sub": str(platform_admin_fixture.id)})
    response = client.get(
        "/api/auth/me",
        HTTP_AUTHORIZATION=f"Bearer {refresh}",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_refresh_token_rotates_only_in_httponly_cookie(client: Client, platform_admin_fixture):
    login = client.post(
        "/api/auth/login",
        data=json.dumps({
            "email": platform_admin_fixture.email,
            "password": "MasterPassword123@#",
        }),
        content_type="application/json",
    )
    assert login.status_code == 200
    first_refresh = login.cookies["neves_refresh"].value

    refreshed = client.post(
        "/api/auth/refresh", data=json.dumps({}), content_type="application/json"
    )
    assert refreshed.status_code == 200, refreshed.content
    assert "access_token" in refreshed.json()
    assert "refresh_token" not in refreshed.json()
    assert refreshed.cookies["neves_refresh"]["httponly"] is True
    assert refreshed.cookies["neves_refresh"].value != first_refresh

    client.cookies["neves_refresh"] = first_refresh
    replay = client.post(
        "/api/auth/refresh", data=json.dumps({}), content_type="application/json"
    )
    assert replay.status_code == 401


@pytest.mark.django_db
def test_client_portal_refresh_is_supported_and_revocation_is_enforced(client: Client):
    from logistics.models import Client, ClientPortalUser

    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador Portal", status="ACTIVE")
    portal_client = Client.objects.create(
        id=uuid.uuid4(), operator=operator, name="Cliente Portal", document="11222333000144", active=True
    )
    portal_user = ClientPortalUser(
        id=uuid.uuid4(), supabase_uid=uuid.uuid4(), operator=operator,
        client=portal_client, name="Lojista", email="portal-refresh@example.com", active=True,
    )
    portal_user.set_password("StrongPortalPassword123!")
    portal_user.save()

    login = client.post(
        "/api/auth/login",
        data=json.dumps({"email": portal_user.email, "password": "StrongPortalPassword123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    refreshed = client.post(
        "/api/auth/refresh", data=json.dumps({}), content_type="application/json"
    )
    assert refreshed.status_code == 200

    portal_user.active = False
    portal_user.save(update_fields=["active"])
    denied = client.post(
        "/api/auth/refresh", data=json.dumps({}), content_type="application/json"
    )
    assert denied.status_code == 401


@pytest.mark.django_db
def test_create_platform_admin_command(db):
    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    call_command(
        "create_platform_admin",
        email="root@expressoneves.com.br",
        name="Root Sovereign",
        password="SuperRootSecurePassword123@#",
        stdout=out,
    )
    admin = PlatformAdmin.objects.filter(email="root@expressoneves.com.br").first()
    assert admin is not None
    assert admin.name == "Root Sovereign"
    assert admin.check_password("SuperRootSecurePassword123@#") is True
    assert "com soberania total" in out.getvalue()
