import hashlib
import hmac
import json
import uuid
import pytest
from django.db import connection
from django.test import Client

from accounts.models import Operator, StaffMember
from accounts.security import create_access_token
from logistics.models import Client as LogisticsClient, Store, Order, Stop
from integration.models import IntegrationConnector, StoreIntegration, IntegrationWebhookLog


@pytest.fixture(autouse=True)
def setup_integration_tables(db):
    if not hasattr(connection.ops, "select"):
        setattr(connection.ops, "select", "%s")
    if not hasattr(connection.ops, "get_geom_placeholder"):
        setattr(connection.ops, "get_geom_placeholder", lambda f, v, c: "%s")

    try:
        from django.contrib.gis.db.models.proxy import SpatialProxy
        setattr(SpatialProxy, "__set__", lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value))
        setattr(SpatialProxy, "__get__", lambda self, instance, cls=None: instance.__dict__.get(self.field.attname) if instance else self)
    except Exception:
        pass

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
                role VARCHAR(20) NOT NULL DEFAULT 'ADMIN',
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
                document VARCHAR(20),
                active BOOLEAN DEFAULT 1,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Store" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                client_id CHAR(32) NOT NULL,
                name VARCHAR(255) NOT NULL,
                "averagePrepTimeMinutes" INTEGER DEFAULT 15,
                operational BOOLEAN DEFAULT 1,
                geom TEXT,
                address VARCHAR(255),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS integration_connector (
                id CHAR(32) PRIMARY KEY,
                slug VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                icon_url VARCHAR(500),
                auth_type VARCHAR(30) NOT NULL DEFAULT 'webhook_signature',
                config_schema TEXT DEFAULT '{}',
                webhook_path_template VARCHAR(200) NOT NULL,
                capabilities TEXT DEFAULT '["receive_orders"]',
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                documentation_url VARCHAR(500),
                version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "StoreIntegration" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                connector_id CHAR(32),
                provider VARCHAR(50),
                "clientId" VARCHAR(255),
                "clientSecret" TEXT,
                "merchantId" VARCHAR(100),
                "authMode" VARCHAR(30) DEFAULT 'WEBHOOK',
                "baseUrl" TEXT,
                "webhookUrl" TEXT,
                "apiKey" TEXT,
                webhook_secret VARCHAR(255),
                config TEXT DEFAULT '{}',
                auto_create_order BOOLEAN NOT NULL DEFAULT 1,
                last_webhook_at TIMESTAMP,
                error_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                active BOOLEAN NOT NULL DEFAULT 1,
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
                status VARCHAR(30) NOT NULL DEFAULT 'PREPARING',
                "fareValueCents" INTEGER NOT NULL DEFAULT 0,
                "storeAuthorizedBonusCents" INTEGER DEFAULT 0,
                "distanceMeters" INTEGER DEFAULT 0,
                "businessDate" DATE,
                "allocationDifficulty" BOOLEAN DEFAULT 0,
                "requestedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "acceptedAt" TIMESTAMP,
                "startedAt" TIMESTAMP,
                "arrivedAt" TIMESTAMP,
                "completedAt" TIMESTAMP,
                "canceledAt" TIMESTAMP,
                external_order_id VARCHAR(255),
                external_source VARCHAR(50),
                metadata TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Stop" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                order_id CHAR(32) NOT NULL,
                sequence INTEGER NOT NULL,
                type VARCHAR(20) NOT NULL DEFAULT 'DROPOFF',
                geom TEXT,
                "requiresPin" BOOLEAN DEFAULT 0,
                "deliveryPinHash" TEXT,
                "completedAt" TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS integration_webhook_log (
                id CHAR(32) PRIMARY KEY,
                integration_id CHAR(32) NOT NULL,
                connector_slug VARCHAR(50) NOT NULL,
                raw_payload_hash VARCHAR(64) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'received',
                order_id CHAR(32),
                error_detail TEXT,
                processing_ms INTEGER,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def operator_and_store():
    op = Operator.objects.create(
        id=uuid.uuid4(),
        name="Logística Neves SP",
        slug="logistica-neves-sp",
        status=Operator.OperatorStatus.ACTIVE,
    )
    staff = StaffMember.objects.create(
        id=uuid.uuid4(),
        operator=op,
        name="Admin Neves",
        email="admin@logneves.com",
        role="ADMIN",
        active=True,
    )
    client_partner = LogisticsClient.objects.create(
        id=uuid.uuid4(),
        operator=op,
        name="Pizzaria Bella",
        document="12345678000100",
    )
    store = Store.objects.create(
        id=uuid.uuid4(),
        operator=op,
        client=client_partner,
        name="Pizzaria Bella - Matriz",
    )
    token = create_access_token({
        "sub": str(staff.id),
        "operator_id": str(op.id),
        "role": "ADMIN",
        "email": staff.email,
    })
    return {
        "operator": op,
        "staff": staff,
        "store": store,
        "token": token,
    }


@pytest.fixture
def connector_generic():
    return IntegrationConnector.objects.create(
        id=uuid.uuid4(),
        slug="generic-webhook",
        name="Webhook Genérico",
        description="Conecte seu PDV ou cardápio digital via webhook padronizado.",
        auth_type="webhook_signature",
        webhook_path_template="/api/v1/integration/webhooks/generic-webhook/{integration_id}",
        capabilities=["receive_orders"],
        status="active",
        version="1.0.0",
    )


def test_list_connectors(api_client, operator_and_store, connector_generic):
    token = operator_and_store["token"]
    res = api_client.get(
        "/api/v1/integration/connectors",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    slugs = [c["slug"] for c in data]
    assert "generic-webhook" in slugs


def test_create_and_list_store_integration(api_client, operator_and_store, connector_generic):
    token = operator_and_store["token"]
    store = operator_and_store["store"]

    # 1. Criar integração
    payload = {
        "store_id": str(store.id),
        "connector_slug": "generic-webhook",
        "config": {"notification_email": "pedidos@pizzariabella.com"},
        "auto_create_order": True,
    }
    res_create = api_client.post(
        "/api/v1/integration/",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert res_create.status_code == 201
    created_data = res_create.json()
    assert created_data["store_name"] == "Pizzaria Bella - Matriz"
    assert created_data["connector_slug"] == "generic-webhook"
    assert created_data["webhook_secret"].startswith("whsec_")
    assert f"/api/v1/integration/webhooks/generic-webhook/{created_data['id']}" == created_data["webhook_url"]

    # 2. Listar integrações (secret deve vir mascarado)
    res_list = api_client.get(
        "/api/v1/integration/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert len(list_data) == 1
    assert "..." in list_data[0]["webhook_secret"] or list_data[0]["webhook_secret"] == "***"


def test_update_and_delete_store_integration(api_client, operator_and_store, connector_generic):
    token = operator_and_store["token"]
    store = operator_and_store["store"]
    op = operator_and_store["operator"]

    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        connector=connector_generic,
        webhook_secret="whsec_initial1234567890abcdef",
        active=True,
    )

    # Valida Criptografia Fática (Manifesto IV.4): O banco NUNCA armazena texto puro
    integration.refresh_from_db()
    assert integration._is_fernet_token(integration.webhook_secret)
    assert integration.webhook_secret != "whsec_initial1234567890abcdef"
    assert integration.get_webhook_secret() == "whsec_initial1234567890abcdef"

    # 1. Pausar integração
    patch_res = api_client.patch(
        f"/api/v1/integration/{integration.id}",
        data=json.dumps({"active": False}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["active"] is False

    integration.refresh_from_db()
    assert integration.active is False

    # 2. Regenerar segredo
    patch_secret = api_client.patch(
        f"/api/v1/integration/{integration.id}",
        data=json.dumps({"regenerate_secret": True}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert patch_secret.status_code == 200
    new_sec = patch_secret.json()["webhook_secret"]
    assert new_sec.startswith("whsec_")
    assert new_sec != "whsec_initial1234567890abcdef"

    # 3. Desativar integração preservando trilha de auditoria
    del_res = api_client.delete(
        f"/api/v1/integration/{integration.id}",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert del_res.status_code == 200
    integration.refresh_from_db()
    assert integration.active is False


def test_generic_webhook_flow_valid_signature_creates_order(api_client, operator_and_store, connector_generic):
    store = operator_and_store["store"]
    op = operator_and_store["operator"]
    secret = "whsec_supersecretkey1234567890"

    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        connector=connector_generic,
        webhook_secret=secret,
        auto_create_order=True,
        active=True,
    )

    order_payload = {
        "order_id": "ORD-9988",
        "customer": {
            "name": "Maria Oliveira",
            "phone": "11988887777",
        },
        "delivery_address": {
            "street": "Rua das Acácias",
            "number": "450",
            "neighborhood": "Jardins",
            "city": "São Paulo",
            "state": "SP",
            "zip": "01400-000",
            "instructions": "Apartamento 12",
        },
        "items": [
            {"name": "Pizza Calabresa", "qty": 1, "price_cents": 4500},
            {"name": "Refrigerante Guaraná", "qty": 1, "price_cents": 1000},
        ],
        "total_cents": 5500,
        "delivery_fee_cents": 900,
        "distance_meters": 3200,
        "payment_method": "online",
        "notes": "Tocar a campainha duas vezes",
    }

    body_bytes = json.dumps(order_payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    # Envio do webhook
    res = api_client.post(
        f"/api/v1/integration/webhooks/generic-webhook/{integration.id}",
        data=body_bytes,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=f"sha256={signature}",
    )

    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "processed"
    assert "order_id" in res_data
    assert res_data["external_order_id"] == "ORD-9988"

    # Verificar que Order foi criada com paradas
    order = Order.objects.get(id=res_data["order_id"])
    assert order.external_order_id == "ORD-9988"
    assert order.external_source == "generic-webhook"
    assert order.fareValueCents == 900
    assert order.distanceMeters == 3200
    assert order.metadata["distance_status"] == "PROVIDED"
    assert order.metadata["order_total_cents"] == 5500
    assert order.status == Order.OrderStatus.PREPARING

    stops = list(Stop.objects.filter(order=order).order_by("sequence"))
    assert len(stops) == 2
    assert stops[0].type == Stop.StopType.PICKUP
    assert stops[1].type == Stop.StopType.DROPOFF

    # Verificar log
    log = IntegrationWebhookLog.objects.get(id=res_data["webhook_id"])
    assert log.status == IntegrationWebhookLog.LogStatus.PROCESSED
    assert str(log.order_id) == str(order.id)


def test_generic_webhook_invalid_signature_rejected(api_client, operator_and_store, connector_generic):
    store = operator_and_store["store"]
    op = operator_and_store["operator"]
    secret = "whsec_validsecret"

    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        connector=connector_generic,
        webhook_secret=secret,
        active=True,
    )

    body_bytes = json.dumps({"order_id": "ORD-001"}).encode("utf-8")

    res = api_client.post(
        f"/api/v1/integration/webhooks/generic-webhook/{integration.id}",
        data=body_bytes,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE="sha256=invalidhashvalue123456789",
    )
    assert res.status_code == 401
    assert "inválida" in res.json()["error"]


def test_generic_webhook_rejects_missing_delivery_fee(
    api_client, operator_and_store, connector_generic
):
    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=operator_and_store["operator"],
        store=operator_and_store["store"],
        connector=connector_generic,
        webhook_secret="whsec_fee_required",
        auto_create_order=True,
        active=True,
    )
    payload = {
        "order_id": "ORD-NO-FEE",
        "customer": {"name": "Cliente"},
        "delivery_address": "Rua Sem Taxa, 10",
        "total_cents": 3000,
    }
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(
        b"whsec_fee_required", body, hashlib.sha256
    ).hexdigest()

    response = api_client.post(
        f"/api/v1/integration/webhooks/generic-webhook/{integration.id}",
        data=body,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=f"sha256={signature}",
    )

    assert response.status_code == 400
    assert not Order.objects.filter(external_order_id="ORD-NO-FEE").exists()


def test_generic_webhook_deduplication(api_client, operator_and_store, connector_generic):
    store = operator_and_store["store"]
    op = operator_and_store["operator"]
    secret = "whsec_dedup_secret"

    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        connector=connector_generic,
        webhook_secret=secret,
        auto_create_order=True,
        active=True,
    )

    payload = {
        "order_id": "ORD-DEDUP-01",
        "customer": {"name": "Carlos"},
        "delivery_address": "Rua B, 20",
        "total_cents": 3000,
        "delivery_fee_cents": 500,
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    # 1. Primeiro envio -> processed
    res1 = api_client.post(
        f"/api/v1/integration/webhooks/generic-webhook/{integration.id}",
        data=body_bytes,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=f"sha256={sig}",
    )
    assert res1.status_code == 200
    order_id_1 = res1.json()["order_id"]

    # 2. Segundo envio com payload idêntico -> already_processed
    res2 = api_client.post(
        f"/api/v1/integration/webhooks/generic-webhook/{integration.id}",
        data=body_bytes,
        content_type="application/json",
        HTTP_X_WEBHOOK_SIGNATURE=f"sha256={sig}",
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "already_processed"
    assert res2.json()["order_id"] == order_id_1

    # Garante que apenas 1 Order foi criada
    imported_order = Order.objects.get(external_order_id="ORD-DEDUP-01")
    assert imported_order.distanceMeters is None
    assert imported_order.metadata["distance_status"] == "PENDING_ROUTING"


def test_generic_webhook_paused_integration(api_client, operator_and_store, connector_generic):
    store = operator_and_store["store"]
    op = operator_and_store["operator"]

    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        connector=connector_generic,
        webhook_secret="whsec_test",
        active=False,  # PAUSADA
    )

    res = api_client.post(
        f"/api/v1/integration/webhooks/generic-webhook/{integration.id}",
        data=b'{"order_id": "1"}',
        content_type="application/json",
    )
    assert res.status_code == 503
    assert "desativada" in res.json()["error"]


def test_webhook_logs_endpoint(api_client, operator_and_store, connector_generic):
    token = operator_and_store["token"]
    store = operator_and_store["store"]
    op = operator_and_store["operator"]

    integration = StoreIntegration.objects.create(
        id=uuid.uuid4(),
        operator=op,
        store=store,
        connector=connector_generic,
        webhook_secret="whsec_logs",
        active=True,
    )

    IntegrationWebhookLog.objects.create(
        id=uuid.uuid4(),
        integration=integration,
        connector_slug="generic-webhook",
        raw_payload_hash="hash1",
        status=IntegrationWebhookLog.LogStatus.PROCESSED,
        processing_ms=35,
    )
    IntegrationWebhookLog.objects.create(
        id=uuid.uuid4(),
        integration=integration,
        connector_slug="generic-webhook",
        raw_payload_hash="hash2",
        status=IntegrationWebhookLog.LogStatus.FAILED,
        error_detail="Invalid address",
        processing_ms=12,
    )

    res = api_client.get(
        f"/api/v1/integration/{integration.id}/logs",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["logs"]) == 2
    statuses = [l["status"] for l in data["logs"]]
    assert "processed" in statuses
    assert "failed" in statuses


def test_integration_management_rejects_tenant_header_and_non_admin(
    api_client, operator_and_store, connector_generic
):
    other = Operator.objects.create(
        id=uuid.uuid4(), name="Operador B", slug="operador-b", status="ACTIVE"
    )
    token = operator_and_store["token"]
    response = api_client.get(
        "/api/v1/integration/stores",
        HTTP_AUTHORIZATION=f"Bearer {token}",
        HTTP_X_OPERATOR_ID=str(other.id),
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(operator_and_store["store"].id)]

    viewer = StaffMember.objects.create(
        id=uuid.uuid4(), operator=operator_and_store["operator"], name="Viewer",
        email="viewer@example.com", role="VIEWER", active=True,
    )
    viewer_token = create_access_token({
        "sub": str(viewer.id), "operator_id": str(viewer.operator_id),
        "role": "VIEWER", "email": viewer.email,
    })
    response = api_client.post(
        "/api/v1/integration/",
        data=json.dumps({
            "store_id": str(operator_and_store["store"].id),
            "connector_slug": connector_generic.slug,
        }),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {viewer_token}",
    )
    assert response.status_code == 401


def test_integration_rejects_unimplemented_connector_and_secret_config(
    api_client, operator_and_store
):
    disabled = IntegrationConnector.objects.create(
        id=uuid.uuid4(), slug="ifood", name="iFood",
        auth_type="oauth2", webhook_path_template="/ifood/{integration_id}",
        status="disabled",
    )
    token = operator_and_store["token"]
    store_id = str(operator_and_store["store"].id)
    response = api_client.post(
        "/api/v1/integration/",
        data=json.dumps({"store_id": store_id, "connector_slug": disabled.slug}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 404

    generic = IntegrationConnector.objects.create(
        id=uuid.uuid4(), slug="generic-webhook", name="Genérico",
        auth_type="webhook_signature",
        webhook_path_template="/generic/{integration_id}", status="active",
    )
    response = api_client.post(
        "/api/v1/integration/",
        data=json.dumps({
            "store_id": store_id, "connector_slug": generic.slug,
            "config": {"api_token": "segredo-em-texto"},
        }),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 400
