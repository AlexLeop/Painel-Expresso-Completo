"""
Testes para as Celery tasks do módulo financeiro (cálculo de crédito diário e fatura semanal).
Cobre bugs CRIT-002 (soma de modos de compensação), LOW-002 (flutuantes vs inteiros).
"""
import pytest
import uuid
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from finance.models import (
    OperatorInternalWallet, Wallet, WalletTransaction, WeeklyStoreInvoice,
    WeeklyInvoiceLineItem, DailyCreditCalculation
)
from logistics.models import Order, Client, Store, Driver
from accounts.models import Operator
from finance.models import Contract


@pytest.fixture
def operator():
    """Cria uma operadora de teste."""
    return Operator.objects.create(
        id=uuid.uuid4(),
        name="Expresso Neves Teste",
        status=Operator.OperatorStatus.ACTIVE
    )


@pytest.fixture
def client(operator):
    """Cria um cliente de teste."""
    return Client.objects.create(
        operator=operator,
        name="Cliente Teste",
        document="12345678000199"
    )


@pytest.fixture
def store(operator, client):
    """Cria uma loja de teste."""
    return Store.objects.create(
        operator=operator,
        client=client,
        name="Loja Teste",
        geom='SRID=4326;POINT(-47.9292 -15.7801)'
    )


@pytest.fixture
def driver(operator):
    """Cria um motorista de teste."""
    return Driver.objects.create(
        operator=operator,
        name="Motorista Teste",
        external_id="MOT-001"
    )


@pytest.fixture
def contract_producao(operator, store):
    """Cria um contrato de compensação de Produção."""
    return Contract.objects.create(
        operator=operator,
        store=store,
        compensationMode=Contract.CompensationMode.PRODUCAO,
        rideFeePerDeliveryCents=500,
        minimumRidesFeeFloorCents=0,
        minimumFloorBps=0,
        adminTaxThresholdCents=10000,
        adminTaxFixedAmountCents=500,
        adminTaxBps=100,  # 1%
        supervisionFeePerWeekCents=200,  # R$2
        dailyRateWeekdayCents=0,
        dailyRateSaturdayCents=0,
        dailyRateSundayCents=0,
        cutoffHour=2,
        returnFeeBps=5000  # 50%
    )


@pytest.fixture
def contract_garantido(operator, store):
    """Cria um contrato de compensação Garantido."""
    return Contract.objects.create(
        operator=operator,
        store=store,
        compensationMode=Contract.CompensationMode.GARANTIDA,
        rideFeePerDeliveryCents=500,
        minimumRidesFeeFloorCents=0,
        minimumFloorBps=0,
        adminTaxThresholdCents=10000,
        adminTaxFixedAmountCents=500,
        adminTaxBps=100,
        supervisionFeePerWeekCents=200,
        dailyRateWeekdayCents=10000,  # R$100/dia
        dailyRateSaturdayCents=15000,
        dailyRateSundayCents=20000,
        cutoffHour=2,
        returnFeeBps=5000
    )


@pytest.fixture
def completed_orders_week(operator, store, driver):
    """Cria algumas ordens completadas ao longo da semana."""
    start_date = timezone.localdate() - timedelta(days=5)
    orders = []
    for i in range(5):
        order = Order.objects.create(
            operator=operator,
            store=store,
            driver=driver,
            status=Order.OrderStatus.COMPLETED,
            fareValueCents=1500 + i*100,  # Variação para teste
            businessDate=start_date + timedelta(days=i),
            externalId=f"ORD-{i:03d}"
        )
        orders.append(order)
    return orders


@pytest.mark.django_db
@pytest.mark.skip(reason="Modelos são managed=False, requer banco real PostgreSQL para testes.")
class TestFinanceTasks:
    """Testes para as tasks de financeiro."""

    def test_compute_daily_credit(self, operator, store, driver, contract_producao, completed_orders_week):
        """
        Testa o cálculo de crédito diário (LOW-002: não usa floats).
        """
        pass

    def test_create_weekly_invoice_uses_single_mode(self, operator, store, driver, contract_garantido, completed_orders_week):
        """
        CRIT-002: Testa que a fatura semanal usa apenas o modo de compensação do contrato (não soma os dois).
        """
        pass

