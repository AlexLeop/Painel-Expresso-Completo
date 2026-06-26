from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

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
        import uuid

        operator = SimpleNamespace(id=uuid.uuid4())
        store = SimpleNamespace(id=uuid.uuid4())
        driver = SimpleNamespace(id=uuid.uuid4())
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

        with (
            patch("finance.services.transaction.atomic", return_value=nullcontext()),
            patch.object(Contract.objects, "get", return_value=contract),
            patch.object(
                OperatorInternalWallet.objects, "get_or_create"
            ) as op_get_or_create,
            patch.object(
                OperatorInternalWallet.objects, "select_for_update"
            ) as operator_wallet_qs,
            patch.object(Wallet.objects, "get_or_create") as driver_get_or_create,
            patch.object(Wallet.objects, "select_for_update") as wallet_qs,
            patch.object(WalletTransaction.objects, "create") as wallet_tx_create,
            patch.object(WeeklyStoreInvoice.objects, "filter") as invoice_filter,
            patch.object(WeeklyInvoiceLineItem.objects, "create") as line_item_create,
        ):
            op_get_or_create.return_value = (
                SimpleNamespace(pk="operator-wallet", id="operator-wallet"),
                True,
            )
            driver_get_or_create.return_value = (
                SimpleNamespace(pk="driver-wallet", id="driver-wallet"),
                True,
            )
            operator_wallet_qs.return_value.get.return_value = SimpleNamespace(
                id="operator-wallet", pk="operator-wallet"
            )
            wallet_qs.return_value.get.return_value = SimpleNamespace(
                id="driver-wallet", pk="driver-wallet"
            )
            invoice_filter.return_value.first.return_value = invoice

            SettlementEngine.settle_order(order)  # type: ignore

        wallet_tx_create.assert_called_once()
        self.assertEqual(
            wallet_tx_create.call_args.kwargs["amountCents"],
            contract.rideFeePerDeliveryCents,
        )

        line_item_create.assert_called_once()
        self.assertEqual(line_item_create.call_args.kwargs["amountCents"], 1500)
