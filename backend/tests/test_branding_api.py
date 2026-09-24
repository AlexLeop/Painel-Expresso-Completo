import uuid
import pytest
from django.test import Client
from django.db import connection
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Operator, StaffMember
from accounts.models_branding import OperatorBranding
from accounts.security import create_access_token


@pytest.fixture(autouse=True)
def setup_branding_tables(db):
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
                slug VARCHAR(100) UNIQUE,
                "platformCostPerDeliveryCents" INTEGER DEFAULT 40,
                "platformMinMonthlyFloorCents" INTEGER DEFAULT 29900,
                "platformVolumeTiers" TEXT DEFAULT '[]',
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
            CREATE TABLE IF NOT EXISTS operator_branding (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL UNIQUE,
                brand_name VARCHAR(255) NOT NULL,
                logo_url VARCHAR(500),
                favicon_url VARCHAR(500),
                color_primary VARCHAR(7) NOT NULL DEFAULT '#6366f1',
                color_secondary VARCHAR(7) NOT NULL DEFAULT '#4f46e5',
                color_accent VARCHAR(7) NOT NULL DEFAULT '#f59e0b',
                color_background VARCHAR(7) NOT NULL DEFAULT '#ffffff',
                color_surface VARCHAR(7) NOT NULL DEFAULT '#f4f4f5',
                color_text VARCHAR(7) NOT NULL DEFAULT '#18181b',
                dark_color_background VARCHAR(7) NOT NULL DEFAULT '#0a0a0a',
                dark_color_surface VARCHAR(7) NOT NULL DEFAULT '#171717',
                dark_color_text VARCHAR(7) NOT NULL DEFAULT '#fafafa',
                theme_mode VARCHAR(10) NOT NULL DEFAULT 'light',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


@pytest.fixture
def op_a():
    op_id = uuid.uuid4()
    return Operator.objects.create(
        id=op_id,
        name="Logística Alpha",
        slug="logistica-alpha",
        status="ACTIVE",
    )


@pytest.fixture
def admin_token_a(op_a):
    user_id = uuid.uuid4()
    StaffMember.objects.create(
        id=user_id,
        operator=op_a,
        name="Admin Alpha",
        email="admin@alpha.com",
        role="ADMIN",
        active=True,
    )
    return create_access_token({
        "sub": str(user_id),
        "operator_id": str(op_a.id),
        "role": "ADMIN",
        "email": "admin@alpha.com",
    })


@pytest.fixture
def driver_token_a(op_a):
    user_id = str(uuid.uuid4())
    return create_access_token({
        "sub": user_id,
        "operator_id": str(op_a.id),
        "role": "DRIVER",
        "email": "driver@alpha.com",
    })


@pytest.fixture
def client():
    return Client()


def test_public_branding_by_slug(client, op_a):
    # Operator without branding record should return defaults based on operator.name
    res = client.get(f"/api/v1/branding/public/{op_a.slug}")
    assert res.status_code == 200
    data = res.json()
    assert data["brand_name"] == "Logística Alpha"
    assert data["color_primary"] == "#6366f1"
    assert data["theme_mode"] == "light"

    # Operator with custom branding
    OperatorBranding.objects.create(
        id=uuid.uuid4(),
        operator=op_a,
        brand_name="Alpha Express Brand",
        color_primary="#ff0055",
        theme_mode="dark",
    )
    res2 = client.get(f"/api/v1/branding/public/{op_a.slug}")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["brand_name"] == "Alpha Express Brand"
    assert data2["color_primary"] == "#ff0055"
    assert data2["theme_mode"] == "dark"


def test_public_branding_not_found(client):
    res = client.get("/api/v1/branding/public/non-existent-slug-12345")
    assert res.status_code == 404


def test_get_branding_authenticated(client, op_a, admin_token_a):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {admin_token_a}"}
    res = client.get("/api/v1/branding/", **headers)
    assert res.status_code == 200, f"Got {res.status_code}: {res.content}"
    data = res.json()
    assert data["operator_id"] == str(op_a.id)
    assert data["brand_name"] == "Logística Alpha"
    assert data["color_primary"] == "#6366f1"


def test_update_branding_admin_success(client, op_a, admin_token_a):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {admin_token_a}"}
    payload = {
        "brand_name": "Novo Alpha Express",
        "color_primary": "#123456",
        "color_secondary": "#abcdef",
        "color_accent": "#00ffaa",
        "theme_mode": "dark",
    }
    res = client.put("/api/v1/branding/", data=payload, content_type="application/json", **headers)
    assert res.status_code == 200, f"Got {res.status_code}: {res.content}"
    data = res.json()
    assert data["brand_name"] == "Novo Alpha Express"
    assert data["color_primary"] == "#123456"
    assert data["theme_mode"] == "dark"

    # Verify persistence
    branding = OperatorBranding.objects.get(operator_id=op_a.id)
    assert branding.brand_name == "Novo Alpha Express"
    assert branding.color_primary == "#123456"


def test_update_branding_invalid_hex_color(client, admin_token_a):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {admin_token_a}"}
    payload = {
        "color_primary": "red; background: url(xss)",
    }
    res = client.put("/api/v1/branding/", data=payload, content_type="application/json", **headers)
    assert res.status_code == 400
    assert "hex válido" in str(res.json())


def test_update_branding_non_admin_forbidden(client, driver_token_a):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {driver_token_a}"}
    payload = {
        "brand_name": "Tentativa Invasiva",
    }
    res = client.put("/api/v1/branding/", data=payload, content_type="application/json", **headers)
    assert res.status_code == 403


def test_operator_cannot_select_foreign_branding_with_header(client, op_a, admin_token_a):
    op_b = Operator.objects.create(
        id=uuid.uuid4(), name="Logística Beta", slug="logistica-beta", status="ACTIVE"
    )
    headers = {
        "HTTP_AUTHORIZATION": f"Bearer {admin_token_a}",
        "HTTP_X_OPERATOR_ID": str(op_b.id),
    }
    res = client.put(
        "/api/v1/branding/",
        data={"brand_name": "Marca Alpha Protegida"},
        content_type="application/json",
        **headers,
    )
    assert res.status_code == 200
    assert OperatorBranding.objects.get(operator=op_a).brand_name == "Marca Alpha Protegida"
    assert not OperatorBranding.objects.filter(operator=op_b).exists()


def test_upload_rejects_spoofed_or_scriptable_image(client, admin_token_a):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {admin_token_a}"}
    spoofed = SimpleUploadedFile("logo.png", b"not-a-real-png", content_type="image/png")
    response = client.post("/api/v1/branding/logo", {"file": spoofed}, **headers)
    assert response.status_code == 400

    svg = SimpleUploadedFile(
        "logo.svg", b'<svg onload="alert(1)"></svg>', content_type="image/svg+xml"
    )
    response = client.post("/api/v1/branding/logo", {"file": svg}, **headers)
    assert response.status_code == 400


def test_upload_logo_and_favicon(client, op_a, admin_token_a, settings):
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        settings.MEDIA_ROOT = temp_dir
        headers = {"HTTP_AUTHORIZATION": f"Bearer {admin_token_a}"}

        # Upload Logo
        fake_png = SimpleUploadedFile("logo.png", b"\x89PNG\r\n\x1a\nfakeimagecontent", content_type="image/png")
        res_logo = client.post("/api/v1/branding/logo", {"file": fake_png}, **headers)
        assert res_logo.status_code == 200, f"Got {res_logo.status_code}: {res_logo.content}"
        assert "logo_url" in res_logo.json()

        # Upload Favicon
        fake_ico = SimpleUploadedFile("favicon.ico", b"\x00\x00\x01\x00fakeicocontent", content_type="image/x-icon")
        res_fav = client.post("/api/v1/branding/favicon", {"file": fake_ico}, **headers)
        assert res_fav.status_code == 200, f"Got {res_fav.status_code}: {res_fav.content}"
        assert "favicon_url" in res_fav.json()

        # Verify branding record was updated
        branding = OperatorBranding.objects.get(operator_id=op_a.id)
        assert branding.logo_url is not None
        assert branding.favicon_url is not None
