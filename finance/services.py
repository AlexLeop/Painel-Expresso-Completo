import logging
from django.db import transaction
from django.utils import timezone

from finance.models import (
    Contract,
    Wallet,
    OperatorInternalWallet,
    WalletTransaction,
    WeeklyInvoiceLineItem,
    WeeklyStoreInvoice,
)
from logistics.models import Order

logger = logging.getLogger(__name__)


class SettlementEngine:
    @staticmethod
    def settle_order(order: Order):
        """
        Garante a liquidação financeira de uma Order.
        Calcula os repasses para o Motorista baseados no Contrato da Loja,
        efetua a transferência imutável no banco e credita o Driver.
        """
        if order.status != Order.OrderStatus.COMPLETED:
            raise ValueError("Apenas ordens concluídas podem ser liquidadas.")

        with transaction.atomic():
            # 1. Recuperar Contrato
            try:
                contract = Contract.objects.get(
                    store=order.store, operator=order.operator
                )
            except Contract.DoesNotExist:
                logger.error(
                    f"FATAL: Contrato não encontrado para a loja {order.store.id}"
                )
                raise ValueError(
                    "Loja sem contrato ativo. Não é possível liquidar a corrida."
                )

            if contract.compensationMode != Contract.CompensationMode.PRODUCAO:
                # Contratos Garantidos não geram transação imediata por corrida,
                # e sim um fechamento noturno (DailyCreditCalculation).
                logger.info(
                    "Order %s não gera repasse imediato (Modo Garantida).", order.id
                )
                return

            # 2. Resgatar as carteiras (Locks para concorrência)
            operator_wallet, _ = OperatorInternalWallet.objects.get_or_create(
                operator=order.operator
            )
            operator_wallet = OperatorInternalWallet.objects.select_for_update().get(
                pk=operator_wallet.pk
            )

            # Valor cobrado da loja (CRIT-001: usar fareValueCents em vez de deliveryFeeCents)
            store_cost = (
                order.fareValueCents
                if getattr(order, "fareValueCents", None)
                else contract.rideFeePerDeliveryCents
            )

            if order.driver:
                driver_wallet, _ = Wallet.objects.get_or_create(
                    driver=order.driver, operator=order.operator
                )
                driver_wallet = Wallet.objects.select_for_update().get(
                    pk=driver_wallet.pk
                )

                # O motorista recebe a taxa da corrida configurada no contrato
                driver_fee = contract.rideFeePerDeliveryCents

                # 3. Transação Imutável de Pagamento do Motorista
                WalletTransaction.objects.create(
                    operator=order.operator,
                    source_operator_wallet=operator_wallet,
                    destination_driver_wallet=driver_wallet,
                    amountCents=driver_fee,
                    category=WalletTransaction.TransactionCategory.PAYOUT,
                    taxCategory=WalletTransaction.TaxCategory.NON_TAXABLE_REIMBURSEMENT,
                )
                logger.info(
                    f"Creditados {driver_fee} cents na wallet do motorista {order.driver.id}."
                )

                # A taxa administrativa que fica pro operador é o que sobrou (store_cost - driver_fee)
                # Mais a taxa percentual se houver adminTaxBps, etc. Aqui abstraímos que a diferença
                # do que o lojista pagou e o motorista recebeu já é a receita bruta do Operador.

            # 4. Registrar a fatura da loja (WeeklyInvoiceLineItem)
            # Para simplificar, assumimos que a Ordem tem businessDate hoje se nulo
            b_date = order.businessDate or timezone.localdate()

            # Procurar uma fatura aberta (DRAFT) para a Loja nesta semana
            invoice = WeeklyStoreInvoice.objects.filter(
                store=order.store,
                operator=order.operator,
                status=WeeklyStoreInvoice.InvoiceStatus.DRAFT,
            ).first()

            if not invoice:
                # Se não tem, cria uma nova cobrindo os próximos 7 dias
                import datetime

                # Sempre alinhar com segunda-feira
                weekday = b_date.weekday()  # 0=Mon, 6=Sun
                start_date = b_date - datetime.timedelta(days=weekday)
                end_date = start_date + datetime.timedelta(days=6)
                invoice = WeeklyStoreInvoice.objects.create(
                    operator=order.operator,
                    store=order.store,
                    startDate=start_date,
                    endDate=end_date,
                    status=WeeklyStoreInvoice.InvoiceStatus.DRAFT,
                )

            # Valor que a loja paga pela entrega (CRIT-001: usar fareValueCents em vez de deliveryFeeCents)
            # Supondo que a loja paga a taxa total da corrida:
            store_cost = (
                order.fareValueCents
                if order.fareValueCents
                else contract.rideFeePerDeliveryCents
            )

            WeeklyInvoiceLineItem.objects.create(
                operator=order.operator,
                invoice=invoice,
                order=order,
                driver=order.driver,
                businessDate=b_date,
                description=f"Corrida {order.id}",
                amountCents=store_cost,
                status=WeeklyInvoiceLineItem.ItemStatus.ACTIVE,
            )
            logger.info(
                f"Adicionado {store_cost} cents na fatura da loja {order.store.id}."
            )
