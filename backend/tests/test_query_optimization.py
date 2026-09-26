import uuid
import datetime
import pytest
from unittest.mock import Mock, patch
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import Client as DjangoClient
from django.utils import timezone as django_tz
from accounts.models import Operator
from logistics.models import Order, Driver, Store, Client
from finance.models import ManualEntry, WithdrawalRequest


@pytest.fixture(autouse=True)
def setup_tables(db, monkeypatch):
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
            CREATE TABLE IF NOT EXISTS "ManualEntry" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                company_id INT,
                driver_id CHAR(32),
                type VARCHAR(50),
                "amountCents" BIGINT DEFAULT 0,
                description TEXT,
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
                status VARCHAR(30) NOT NULL,
                "rejectionReason" TEXT,
                "failureReason" TEXT,
                "processedAt" TIMESTAMP,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def test_dashboard_stats_query_count_under_15():
    """
    Verifica que get_dashboard_stats para 90 dias agrega em lote via TruncDay
    e não executa mais de 15 queries no total (eliminando 180 queries N+1).
    """
    from config.db_api import get_dashboard_stats

    operator = Operator.objects.create(id=uuid.uuid4(), name="Op Performance")
    store = Store.objects.create(id=uuid.uuid4(), operator=operator, name="Loja 1")
    driver = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver 1", phone="111")

    now = django_tz.now()
    # Cria pedidos em 5 dias distintos
    for d in range(5):
        Order.objects.create(
            id=uuid.uuid4(),
            operator=operator,
            store=store,
            driver=driver,
            status=Order.OrderStatus.COMPLETED,
            fareValueCents=2500,
            requestedAt=now - datetime.timedelta(days=d),
            completedAt=now - datetime.timedelta(days=d),
        )

    req = Mock()
    req.headers = {"X-Operator-Id": str(operator.id)}
    req.GET = {}
    req.auth = None

    staff_mock = Mock(id=uuid.uuid4(), role="ADMIN", is_platform_admin=False, operator=operator, operator_id=operator.id)

    with patch("accounts.auth.get_staff_member", return_value=staff_mock):
        with CaptureQueriesContext(connection) as ctx:
            res = get_dashboard_stats(req, range="all")

    # Com a otimização de TruncDay, o número de queries deve ser <= 15 (idealmente ~10)
    assert len(ctx.captured_queries) <= 15, (
        f"Alerta N+1: get_dashboard_stats para 90 dias executou {len(ctx.captured_queries)} queries! "
        f"Deveria ser <= 15 queries com agregação em lote."
    )
    assert len(res["chart_data"]) == 90
    assert res["completed_orders"] == 5


def test_financial_dashboard_uses_datetime_range():
    """
    Verifica que get_operator_financial_dashboard filtra por range de datetime (gte/lte)
    em vez de __year e __month para permitir index scans no PostgreSQL.
    """
    from config.db_api import get_operator_financial_dashboard

    operator = Operator.objects.create(id=uuid.uuid4(), name="Op Finance Range")
    store = Store.objects.create(id=uuid.uuid4(), operator=operator, name="Loja Fin")
    now = django_tz.now()

    Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        status="COMPLETED",
        fareValueCents=3000,
        completedAt=now,
    )

    req = Mock()
    req.headers = {"X-Operator-Id": str(operator.id)}
    req.GET = {"operator_id": str(operator.id)}
    req.auth = None

    staff_mock = Mock(id=uuid.uuid4(), role="ADMIN", is_platform_admin=False, operator=operator, operator_id=operator.id)
    month_str = now.strftime("%Y-%m")

    with patch("accounts.auth.get_staff_member", return_value=staff_mock):
        with CaptureQueriesContext(connection) as ctx:
            res = get_operator_financial_dashboard(req, month=month_str)

    for q in ctx.captured_queries:
        sql_lower = q["sql"].lower()
        assert "extract" not in sql_lower, f"Query ainda contém EXTRACT: {q['sql']}"
        assert "django_date_extract" not in sql_lower, f"Query ainda contém django_date_extract: {q['sql']}"

    assert res["corridas_entregues"] == 1
    assert res["receita_bruta_cents"] == 3000


def test_catch_all_removed_returns_404():
    """
    Verifica que rotas inexistentes retornam 404 e não 200 {}.
    """
    client = DjangoClient()
    response = client.get("/api/v1/panel/non-existent-endpoint-test-12345")
    assert response.status_code == 404, (
        f"Esperava HTTP 404 para rota inexistente, mas recebeu HTTP {response.status_code}."
    )
