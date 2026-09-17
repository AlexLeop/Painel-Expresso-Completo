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
