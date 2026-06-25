from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from finance.models import (
    Contract,
    Wallet,
    OperatorInternalWallet,
    WalletTransaction,
    WeeklyInvoiceLineItem,
    WeeklyStoreInvoice,
)
from finance.services import SettlementEngine
from logistics.models import Order


class SettlementEngineTests(SimpleTestCase):
    def test_settle_order_uses_fare_value_cents(self):
        """
        Testa que SettlementEngine usa order.fareValueCents (CRIT-001 resolvido).
        """
        operator = SimpleNamespace(id="op-1")
        store = SimpleNamespace(id="store-1")
        driver = SimpleNamespace(id="driver-1")
        contract = SimpleNamespace(
            compensationMode=Contract.CompensationMode.PRODUCAO,
            rideFeePerDeliveryCents=500,
        )
        invoice = SimpleNamespace(id="invoice-1")
        order = SimpleNamespace(
            id="order-1",
            operator=operator,
            store=store,
            driver=driver,
            status=Order.OrderStatus.COMPLETED,
            fareValueCents=1500,
            businessDate=timezone.localdate(),
        )

        with patch("finance.services.transaction.atomic", return_value=nullcontext()), \
             patch.object(Contract.objects, "get", return_value=contract), \
             patch.object(OperatorInternalWallet.objects, "select_for_update") as operator_wallet_qs, \
             patch.object(Wallet.objects, "select_for_update") as wallet_qs, \
             patch.object(WalletTransaction.objects, "create") as wallet_tx_create, \
             patch.object(WeeklyStoreInvoice.objects, "filter") as invoice_filter, \
             patch.object(WeeklyInvoiceLineItem.objects, "create") as line_item_create:
            operator_wallet_qs.return_value.get_or_create.return_value = (SimpleNamespace(id="operator-wallet"), True)
            wallet_qs.return_value.get_or_create.return_value = (SimpleNamespace(id="driver-wallet"), True)
            invoice_filter.return_value.first.return_value = invoice

            SettlementEngine.settle_order(order)

        wallet_tx_create.assert_called_once()
        self.assertEqual(wallet_tx_create.call_args.kwargs["amountCents"], contract.rideFeePerDeliveryCents)

        line_item_create.assert_called_once()
        self.assertEqual(line_item_create.call_args.kwargs["amountCents"], 1500)

