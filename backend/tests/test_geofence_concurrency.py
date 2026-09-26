import json
import uuid
import pytest
from unittest.mock import Mock, patch
from django.db import connection
from django.utils import timezone as django_tz
from accounts.models import Operator
from logistics.models import Order, Driver, Stop, Client, Store
from logistics.tasks import process_geofence_triggers


@pytest.fixture(autouse=True)
def setup_geofence_tables(db, monkeypatch):
    import django.contrib.gis.geos as geos
    monkeypatch.setattr(geos, "Point", lambda lng, lat, srid=4326: f"POINT ({lng} {lat})")
    from django.contrib.gis.db.models.proxy import SpatialProxy
    setattr(SpatialProxy, "__set__", lambda self, instance, value: instance.__dict__.__setitem__(self.field.attname, value))
    setattr(SpatialProxy, "__get__", lambda self, instance, cls=None: instance.__dict__.get(self.field.attname) if instance else self)
    if not hasattr(connection.ops, "select"):
        setattr(connection.ops, "select", "%s")
    if not hasattr(connection.ops, "get_geom_placeholder"):
        setattr(connection.ops, "get_geom_placeholder", lambda f, v, c: "%s")

    with connection.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Operator" (
                id CHAR(32) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(100),
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
            CREATE TABLE IF NOT EXISTS "Order" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                driver_id CHAR(32),
                manifest_id CHAR(32),
                status VARCHAR(30) DEFAULT 'STARTED',
                "fareValueCents" INT DEFAULT 0,
                "storeAuthorizedBonusCents" INT DEFAULT 0,
                "distanceMeters" INT DEFAULT 0,
                "businessDate" DATE,
                "allocationDifficulty" BOOLEAN DEFAULT 0,
                "requestedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "acceptedAt" TIMESTAMP,
                "startedAt" TIMESTAMP,
                "arrivedAt" TIMESTAMP,
                "completedAt" TIMESTAMP,
                "canceledAt" TIMESTAMP,
                "external_order_id" VARCHAR(255),
                "external_source" VARCHAR(50),
                metadata TEXT DEFAULT '{}',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Stop" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                order_id CHAR(32) NOT NULL,
                sequence INT NOT NULL,
                type VARCHAR(20) NOT NULL DEFAULT 'DROPOFF',
                geom TEXT,
                "requiresPin" BOOLEAN DEFAULT 0,
                "deliveryPinHash" TEXT,
                "completedAt" TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "IntegrationOutbox" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                aggregateType VARCHAR(100) NOT NULL,
                aggregateId CHAR(32) NOT NULL,
                sequenceNumber INTEGER,
                eventType VARCHAR(100) NOT NULL,
                payload TEXT,
                status VARCHAR(50) DEFAULT 'PENDING',
                attempts INT DEFAULT 0,
                lastAttemptAt TIMESTAMP,
                failReason TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def test_geofence_does_not_arrive_order_of_different_driver():
    """
    Anti-Geofence Hijacking:
    Garante que se o Driver B emitir um evento de proximidade de um Stop
    cuja Order pertence ao Driver A, a Order do Driver A NÃO deve mudar para ARRIVED.
    """
    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador Teste")
    client = Client.objects.create(id=uuid.uuid4(), operator=operator, name="Cliente Teste", document="123")
    store = Store.objects.create(id=uuid.uuid4(), operator=operator, client=client, name="Loja Teste")
    driver_a = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver A", phone="111")
    driver_b = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver B", phone="222")

    order = Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        driver=driver_a,
        status=Order.OrderStatus.STARTED,
    )
    stop = Stop.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        order=order,
        sequence=1,
    )

    # Evento emitido pelo Driver B (não atribuído a esta corrida)
    hijack_event = json.dumps({
        "driver_id": str(driver_b.id),
        "stop_id": str(stop.id),
        "action": "ENTER",
    })

    class FakeRedis:
        def __init__(self):
            self.queue = [hijack_event]
        def lrange(self, key, start, stop_idx):
            if not self.queue:
                return []
            return self.queue[start:stop_idx+1]
        def ltrim(self, key, start, stop_idx):
            if start < len(self.queue):
                self.queue = self.queue[start:]
            else:
                self.queue = []
        def srem(self, key, member):
            pass

    fake_redis = FakeRedis()

    with patch("logistics.tasks.r", fake_redis):
        process_geofence_triggers()

    order.refresh_from_db()
    # A Order DEVE permanecer STARTED, e não ARRIVED!
    assert order.status == Order.OrderStatus.STARTED, (
        f"Geofence Hijacking detectado: Order {order.id} mudou indevidamente para {order.status}!"
    )


def test_geofence_arrives_order_of_correct_driver():
    """
    Garante que o Driver correto (atribuído) consegue auto-chegar via Geofence.
    """
    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador Teste 2")
    client = Client.objects.create(id=uuid.uuid4(), operator=operator, name="Cliente Teste 2", document="456")
    store = Store.objects.create(id=uuid.uuid4(), operator=operator, client=client, name="Loja Teste 2")
    driver_a = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver A 2", phone="333")

    order = Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        driver=driver_a,
        status=Order.OrderStatus.STARTED,
    )
    stop = Stop.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        order=order,
        sequence=1,
    )

    valid_event = json.dumps({
        "driver_id": str(driver_a.id),
        "stop_id": str(stop.id),
        "action": "ENTER",
    })

    class FakeRedis:
        def __init__(self):
            self.queue = [valid_event]
        def lrange(self, key, start, stop_idx):
            if not self.queue:
                return []
            return self.queue[start:stop_idx+1]
        def ltrim(self, key, start, stop_idx):
            if start < len(self.queue):
                self.queue = self.queue[start:]
            else:
                self.queue = []
        def srem(self, key, member):
            pass

    fake_redis = FakeRedis()

    with patch("logistics.tasks.r", fake_redis):
        process_geofence_triggers()

    order.refresh_from_db()
    assert order.status == Order.OrderStatus.ARRIVED, (
        f"Order {order.id} deveria ter mudado para ARRIVED para o motorista atribuído!"
    )


def test_positions_endpoint_reads_from_redis():
    """Garante que /positions lê as posições geoespaciais em tempo real do Redis."""
    from config import db_api

    request = Mock()
    staff_mock = Mock()
    staff_mock.operator_id = "op-live-1"

    class FakeGeoRedis:
        def zrange(self, key, start, stop):
            if key == "driver_positions:op-live-1":
                return ["driver-abc", "driver-xyz"]
            return []
        def geopos(self, key, member):
            if member == "driver-abc":
                return [(-47.9292, -15.7801)]
            if member == "driver-xyz":
                return [(-47.9100, -15.7900)]
            return [None]

    with patch("accounts.auth.get_staff_member", return_value=staff_mock):
        with patch("config.redis_client.get_redis", return_value=FakeGeoRedis()):
            result = db_api.get_positions(request)

    assert result["source"] == "redis_live"
    assert len(result["positions"]) == 2
    assert result["positions"][0]["machine_condutor_id"] == "driver-abc"
    assert result["positions"][0]["latitude"] == -15.7801
    assert result["positions"][0]["longitude"] == -47.9292


def test_clear_order_runtime_state_removes_geofence_keys():
    """Garante que clear_order_runtime_state remove paradas do geofence no Redis (anti-vazamento)."""
    from logistics.api_driver import clear_order_runtime_state

    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador Teste Cleanup")
    client = Client.objects.create(id=uuid.uuid4(), operator=operator, name="Cliente Cleanup", document="789")
    store = Store.objects.create(id=uuid.uuid4(), operator=operator, client=client, name="Loja Cleanup")
    driver = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver Cleanup", phone="999")

    order = Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        driver=driver,
        status=Order.OrderStatus.COMPLETED,
    )
    stop = Stop.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        order=order,
        sequence=1,
    )

    piped_commands = []
    class MockPipeline:
        def srem(self, key, member):
            piped_commands.append(("srem", key, member))
            return self
        def delete(self, key):
            piped_commands.append(("delete", key))
            return self
        def zrem(self, key, member):
            piped_commands.append(("zrem", key, member))
            return self
        def execute(self):
            return []

    class MockRedisClient:
        def pipeline(self):
            return MockPipeline()

    with patch("logistics.api_driver.r", MockRedisClient()):
        clear_order_runtime_state(order, driver.id)

    # Verifica se zrem foi chamado para a chave geofence do operador
    geo_key = f"geofence:stops:{order.operator_id}"
    stop_member = f"stop:{stop.id}:point"
    assert ("zrem", geo_key, stop_member) in piped_commands, (
        f"A parada não foi removida do índice geoespacial via zrem! Comandos: {piped_commands}"
    )
    assert ("delete", f"stop:{stop.id}:radius") in piped_commands

