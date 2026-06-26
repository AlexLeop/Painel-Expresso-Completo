import pytest
import asyncio
from asgiref.sync import sync_to_async
from django.db import connection

from logistics.models import Driver, Store, Client, Order
from accounts.models import Operator
from finance.models import Wallet, Contract
from finance.services import SettlementEngine


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Modelos são managed=False, requer banco real PostgreSQL para teste de concorrência real."
)
async def test_race_condition_settlement():
    """
    Simula múltiplas requisições simultâneas para liquidar a mesma ordem
    para atestar que os saldos não sofrem double-spending e as travas ACID funcionam.
    """
    operator = await Operator.objects.acreate(name="Test Operator")
    client = await Client.objects.acreate(
        name="Test Client", document="12345678900", operator=operator
    )
    driver = await Driver.objects.acreate(
        operator=operator, name="Test Driver", active=True, phone="123"
    )
    store = await Store.objects.acreate(
        operator=operator, client=client, name="Store", active=True
    )

    await Contract.objects.acreate(
        operator=operator,
        store=store,
        compensationMode=Contract.CompensationMode.PRODUCAO,
        rideFeePerDeliveryCents=500,
        returnFeeBps=5000,
        supervisionFeePerWeekCents=1000,
        adminTaxFixedAmountCents=0,
        adminTaxThresholdCents=0,
        adminTaxBps=1000,
        dailyRateWeekdayCents=0,
        dailyRateSaturdayCents=0,
        dailyRateSundayCents=0,
    )

    order = await Order.objects.acreate(
        operator=operator,
        store=store,
        driver=driver,
        status=Order.OrderStatus.COMPLETED,
        fareValueCents=1000,
    )

    @sync_to_async
    def attempt_settle():
        connection.close()
        try:
            SettlementEngine.settle_order(order)
            return True
        except Exception:
            return False

    await asyncio.gather(*(attempt_settle() for _ in range(5)))

    wallet = await Wallet.objects.aget(driver=driver, operator=operator)
    assert wallet.balanceCents == 500, f"Expected 500, got {wallet.balanceCents}"
