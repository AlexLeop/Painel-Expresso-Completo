import uuid
import pytest
from unittest.mock import Mock, patch
from django.db import connection
from django.utils import timezone as django_tz
from accounts.models import Operator
from logistics.models import Order, Driver, Store, Client
from finance.models import (
    Contract,
    Wallet,
    OperatorInternalWallet,
    WalletTransaction,
    WeeklyStoreInvoice,
    WeeklyInvoiceLineItem,
    WithdrawalRequest,
)
from finance.services import SettlementEngine
from finance.tasks import process_return_file_ret


@pytest.fixture(autouse=True)
def setup_finance_hardening_tables(db, monkeypatch):
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
            CREATE TABLE IF NOT EXISTS "Contract" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                "compensationMode" VARCHAR(30) DEFAULT 'PRODUCAO',
                "rideFeePerDeliveryCents" BIGINT DEFAULT 700,
                "minimumRidesFeeFloorCents" BIGINT DEFAULT 0,
                "minimumFloorBps" INT DEFAULT 0,
                "adminTaxThresholdCents" BIGINT DEFAULT 0,
                "adminTaxFixedAmountCents" BIGINT DEFAULT 0,
                "adminTaxBps" INT DEFAULT 0,
                "supervisionFeePerWeekCents" BIGINT DEFAULT 0,
                "dailyRateWeekdayCents" BIGINT DEFAULT 0,
                "dailyRateSaturdayCents" BIGINT DEFAULT 0,
                "dailyRateSundayCents" BIGINT DEFAULT 0,
                "dailyRateHolidayCents" BIGINT DEFAULT 0,
                "kmExcedenteValorCents" BIGINT DEFAULT 0,
                "allowAutomaticGrouping" BOOLEAN DEFAULT 1,
                "cloudOverflowAllowed" BOOLEAN DEFAULT 0,
                "maxStopsPerManifest" INT DEFAULT 3,
                "maxDetourPercent" INT DEFAULT 20,
                "billingMode" VARCHAR(30) DEFAULT 'POS_PAGO',
                "active" BOOLEAN DEFAULT 1,
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "Wallet" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL UNIQUE,
                "balanceCents" BIGINT NOT NULL DEFAULT 0,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "OperatorInternalWallet" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL UNIQUE,
                "balanceCents" BIGINT NOT NULL DEFAULT 0,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WalletTransaction" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                source_driver_wallet_id CHAR(32),
                destination_driver_wallet_id CHAR(32),
                source_operator_wallet_id CHAR(32),
                destination_operator_wallet_id CHAR(32),
                "amountCents" BIGINT NOT NULL,
                category VARCHAR(50) NOT NULL,
                "taxCategory" VARCHAR(50) NOT NULL,
                metadata TEXT DEFAULT '{}',
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WeeklyStoreInvoice" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                store_id CHAR(32) NOT NULL,
                "startDate" DATE NOT NULL,
                "endDate" DATE NOT NULL,
                "totalNetProducaoCents" BIGINT DEFAULT 0,
                "totalNetGarantidaCents" BIGINT DEFAULT 0,
                "administrativeFeeCents" BIGINT DEFAULT 0,
                "supervisionFeeCents" BIGINT DEFAULT 0,
                "pendingDebitCarriedCents" BIGINT DEFAULT 0,
                "totalCents" BIGINT NOT NULL DEFAULT 0,
                status VARCHAR(20) DEFAULT 'DRAFT',
                "paymentGatewayId" VARCHAR(255),
                "pixCopyPaste" TEXT,
                barcode TEXT,
                "pdfUrl" VARCHAR(255),
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "WeeklyInvoiceLineItem" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                invoice_id CHAR(32) NOT NULL,
                driver_id CHAR(32),
                order_id CHAR(32),
                manualEntryId CHAR(32),
                "businessDate" DATE,
                description TEXT,
                "amountCents" BIGINT NOT NULL,
                status VARCHAR(20) DEFAULT 'ACTIVE',
                "disputeReason" TEXT,
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
                "fareValueCents" INT DEFAULT 1200,
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
            CREATE TABLE IF NOT EXISTS "WithdrawalRequest" (
                id CHAR(32) PRIMARY KEY,
                operator_id CHAR(32) NOT NULL,
                driver_id CHAR(32) NOT NULL,
                "amountCents" BIGINT NOT NULL,
                status VARCHAR(30) DEFAULT 'PROCESSING',
                "pixKey" VARCHAR(255) DEFAULT '12345678900',
                "pixKeyType" VARCHAR(20) DEFAULT 'CPF',
                "approvalMode" VARCHAR(30) DEFAULT 'AUTO_INSTANT',
                "feeAmountCents" BIGINT DEFAULT 0,
                "netAmountCents" BIGINT DEFAULT 0,
                "approved_by_id" CHAR(32),
                "approvedAt" TIMESTAMP,
                "rejectionReason" TEXT,
                "baasProvider" VARCHAR(50) DEFAULT 'EFI_PAY',
                "baasTransactionId" VARCHAR(255),
                "baasRawResponse" TEXT DEFAULT '{}',
                "failureReason" TEXT,
                "processedAt" TIMESTAMP,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def test_settle_order_prevents_duplicate_transactions():
    """
    Idempotência Contábil:
    Garante que chamar settle_order mais de uma vez para a mesma ordem
    NÃO duplica o repasse ao motorista e NÃO duplica o item na fatura.
    """
    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador Ledger")
    client = Client.objects.create(id=uuid.uuid4(), operator=operator, name="Cliente Ledger", document="123")
    store = Store.objects.create(id=uuid.uuid4(), operator=operator, client=client, name="Loja Ledger")
    driver = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver Ledger", phone="555")

    contract = Contract.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        compensationMode=Contract.CompensationMode.PRODUCAO,
        rideFeePerDeliveryCents=700,
    )

    order = Order.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        store=store,
        driver=driver,
        status=Order.OrderStatus.COMPLETED,
        fareValueCents=1200,
    )

    # Primeira liquidação
    SettlementEngine.settle_order(order)

    tx_count_1 = WalletTransaction.objects.filter(operator=operator).count()
    items_count_1 = WeeklyInvoiceLineItem.objects.filter(order=order).count()

    assert tx_count_1 == 1, "Deveria ter gerado exatamente 1 transação de repasse."
    assert items_count_1 == 1, "Deveria ter gerado exatamente 1 item de fatura."

    # Segunda liquidação (ex: retry, duplicidade)
    SettlementEngine.settle_order(order)

    tx_count_2 = WalletTransaction.objects.filter(operator=operator).count()
    items_count_2 = WeeklyInvoiceLineItem.objects.filter(order=order).count()

    assert tx_count_2 == 1, (
        f"Duplicação detectada! Esperava 1 WalletTransaction, mas existem {tx_count_2}."
    )
    assert items_count_2 == 1, (
        f"Duplicação na fatura! Esperava 1 WeeklyInvoiceLineItem, mas existem {items_count_2}."
    )


def test_cnab_return_file_rejects_and_refunds_on_error():
    """
    Garante que código de rejeição no retorno CNAB altera o status do saque para FAILED
    e aciona o estorno automático na carteira do motorista.
    """
    operator = Operator.objects.create(id=uuid.uuid4(), name="Operador CNAB")
    driver = Driver.objects.create(id=uuid.uuid4(), operator=operator, name="Driver CNAB", phone="777")
    wallet = Wallet.objects.create(id=uuid.uuid4(), operator=operator, driver=driver, balanceCents=0)
    op_wallet = OperatorInternalWallet.objects.create(id=uuid.uuid4(), operator=operator, balanceCents=10000)

    withdrawal = WithdrawalRequest.objects.create(
        id=uuid.uuid4(),
        operator=operator,
        driver=driver,
        amountCents=5000,
        status=WithdrawalRequest.WithdrawalStatus.PROCESSING,
    )

    # Monta uma linha simulada de Segmento A (240 posições) com código de rejeição
    # Posições 75 a 95: withdrawal id (hex sem traços ou uuid)
    # Posições 230 a 240: código de retorno/ocorrência ("RJ" = Rejeitado)
    # Posição 7 = '3' (Detalhe), Posição 13 = 'A' (Segmento A)
    # 001-003: Banco (341), 004-007: Lote (0001), 008: Tipo (3), 009-013: Seq (00001) -> 13 chars
    prefix = "3410001300001"
    w_id_formatted = withdrawal.id.hex[:20].ljust(20)
    line = prefix + "A" + "0" * 61 + w_id_formatted + "0" * 135 + "RJ" + " " * 8
    assert len(line) == 240

    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(line + "\n")
        f_path = f.name

    with patch("finance.services.AtomicRefundEngine.refund_failed_withdrawal") as mock_refund:
        process_return_file_ret(f_path)

    withdrawal.refresh_from_db()
    assert withdrawal.status == WithdrawalRequest.WithdrawalStatus.FAILED, (
        f"Saque com código de rejeição deveria ter mudado para FAILED, mas está {withdrawal.status}!"
    )
    mock_refund.assert_called_once()
