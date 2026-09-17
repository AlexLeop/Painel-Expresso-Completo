import datetime
import logging
from dataclasses import dataclass
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from finance.models import (
    Contract,
    Wallet,
    OperatorInternalWallet,
    WalletTransaction,
    WeeklyInvoiceLineItem,
    WeeklyStoreInvoice,
    WithdrawalRequest,
    PayoutPolicyConfig,
)
from logistics.models import Order, Driver

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


@dataclass
class PayoutEvaluation:
    """Resultado da análise de alçada, política e tarifa para um pedido de saque."""

    approval_mode: str  # WithdrawalRequest.ApprovalMode.AUTO_INSTANT ou MANUAL_PENDING
    fee_amount_cents: int
    net_amount_cents: int
    policy_source: str  # "STORE_OVERRIDE", "GLOBAL_OPERATOR", "SYSTEM_DEFAULT"
    notify_push: bool
    notify_whatsapp: bool
    requires_manual_reason: str = ""


class PayoutPolicyEngine:
    """
    Motor de Análise de Políticas de Saque (BaaS Pix).
    Avalia a hierarquia de regras:
    1. Sobreposições contratuais da Loja/Cliente vinculada (se overridePayoutPolicy=True).
    2. Política Global do Operador (PayoutPolicyConfig).
    3. Padrões de segurança do sistema caso nenhuma política esteja gravada.
    """

    DEFAULT_AUTO_THRESHOLD_CENTS = 15000  # R$ 150,00
    DEFAULT_DAILY_LIMIT_CENTS = 50000     # R$ 500,00
    DEFAULT_MIN_WITHDRAWAL_CENTS = 1000   # R$ 10,00

    @classmethod
    def evaluate_payout(
        cls,
        operator,
        driver: Driver,
        amount_cents: int,
        store_id: str | None = None,
    ) -> PayoutEvaluation:
        """
        Avalia se o saque solicitado pelo motorista pode ser liberado imediatamente
        ou se deve aguardar aprovação humana do despachante/operador.
        """
        # 1. Carrega política global do operador
        global_policy = PayoutPolicyConfig.objects.filter(operator=operator).first()

        mode = (
            global_policy.mode
            if global_policy
            else PayoutPolicyConfig.PayoutMode.HYBRID_THRESHOLD
        )
        auto_threshold = (
            global_policy.autoThresholdCents
            if global_policy
            else cls.DEFAULT_AUTO_THRESHOLD_CENTS
        )
        daily_limit = (
            global_policy.dailyLimitPerDriverCents
            if global_policy
            else cls.DEFAULT_DAILY_LIMIT_CENTS
        )
        min_withdrawal = (
            global_policy.minWithdrawalCents
            if global_policy
            else cls.DEFAULT_MIN_WITHDRAWAL_CENTS
        )
        fee_mode = (
            global_policy.payoutFeeMode
            if global_policy
            else PayoutPolicyConfig.PayoutFeeMode.ABSORBED_BY_PLATFORM
        )
        fee_cents = global_policy.payoutFeeCents if global_policy else 0
        notify_push = global_policy.notifyPushEnabled if global_policy else True
        notify_whatsapp = global_policy.notifyWhatsappEnabled if global_policy else True
        policy_source = "GLOBAL_OPERATOR" if global_policy else "SYSTEM_DEFAULT"

        # 2. Verifica sobreposição contratual por Loja (se informada ou se motorista tiver pedidos recentes)
        contract = None
        if store_id:
            contract = Contract.objects.filter(
                store_id=store_id, operator=operator, overridePayoutPolicy=True
            ).first()

        if not contract and driver:
            recent_order = (
                Order.objects.filter(driver=driver, operator=operator)
                .order_by("-createdAt")
                .first()
            )
            if recent_order and recent_order.store_id:
                contract = Contract.objects.filter(
                    store_id=recent_order.store_id,
                    operator=operator,
                    overridePayoutPolicy=True,
                ).first()

        if contract and contract.overridePayoutPolicy:
            policy_source = "STORE_OVERRIDE"
            if contract.customPayoutMode:
                mode = contract.customPayoutMode
            if contract.customAutoThresholdCents is not None:
                auto_threshold = contract.customAutoThresholdCents
            if contract.customFeeMode:
                fee_mode = contract.customFeeMode
            if contract.customFeeCents is not None:
                fee_cents = contract.customFeeCents

        # 3. Validação do valor mínimo
        if amount_cents < min_withdrawal:
            raise ValueError(
                f"O valor mínimo para solicitação de saque é de R$ {min_withdrawal / 100:.2f}."
            )

        # 4. Cálculo da Tarifa de Saque
        if fee_mode == PayoutPolicyConfig.PayoutFeeMode.CHARGED_TO_DRIVER:
            fee_amount = max(0, fee_cents)
            net_amount = max(0, amount_cents - fee_amount)
        else:
            fee_amount = 0
            net_amount = amount_cents

        # 5. Verificação de teto acumulado diário (últimas 24 horas)
        past_24h = timezone.now() - datetime.timedelta(hours=24)
        recent_withdrawals_sum = (
            WithdrawalRequest.objects.filter(
                driver=driver,
                operator=operator,
                createdAt__gte=past_24h,
                status__in=[
                    WithdrawalRequest.WithdrawalStatus.PENDING,
                    WithdrawalRequest.WithdrawalStatus.PROCESSING,
                    WithdrawalRequest.WithdrawalStatus.PAID,
                ],
            ).aggregate(total=Sum("amountCents"))["total"]
            or 0
        )

        requires_manual_reason = ""
        exceeded_daily_limit = (recent_withdrawals_sum + amount_cents) > daily_limit

        # 6. Decisão de Alçada
        if mode == PayoutPolicyConfig.PayoutMode.MANUAL_ALL:
            approval_mode = WithdrawalRequest.ApprovalMode.MANUAL_PENDING
            requires_manual_reason = "Política configurada para aprovação manual obrigatória."
        elif exceeded_daily_limit:
            approval_mode = WithdrawalRequest.ApprovalMode.MANUAL_PENDING
            requires_manual_reason = (
                f"Limite diário de R$ {daily_limit / 100:.2f} excedido (acumulado 24h: "
                f"R$ {recent_withdrawals_sum / 100:.2f} + R$ {amount_cents / 100:.2f})."
            )
        elif amount_cents <= auto_threshold:
            approval_mode = WithdrawalRequest.ApprovalMode.AUTO_INSTANT
        else:
            approval_mode = WithdrawalRequest.ApprovalMode.MANUAL_PENDING
            requires_manual_reason = (
                f"Valor solicitado (R$ {amount_cents / 100:.2f}) excede o teto automático "
                f"(R$ {auto_threshold / 100:.2f})."
            )

        return PayoutEvaluation(
            approval_mode=approval_mode,
            fee_amount_cents=fee_amount,
            net_amount_cents=net_amount,
            policy_source=policy_source,
            notify_push=notify_push,
            notify_whatsapp=notify_whatsapp,
            requires_manual_reason=requires_manual_reason,
        )


class AtomicRefundEngine:
    """
    Motor Atômico de Estornos Financeiros.
    Restaura saldos da carteira de forma imutável com dupla-contrapartida
    quando uma transferência PIX é rejeitada pelo Bacen/Efí ou recusada pelo operador.
    """

    @classmethod
    def refund_failed_withdrawal(
        cls,
        withdrawal: WithdrawalRequest,
        reason: str,
    ) -> WithdrawalRequest:
        """
        Executa o estorno do valor debitado na carteira do motorista.
        Garante a ordem estrita de locks (OperatorInternalWallet -> Driver Wallet).
        """
        with transaction.atomic():
            w = (
                WithdrawalRequest.objects.select_for_update()
                .get(pk=withdrawal.pk)
            )

            # Idempotência: se já estiver FAILED, não estorna novamente
            if w.status == WithdrawalRequest.WithdrawalStatus.FAILED:
                logger.warning(
                    "WithdrawalRequest %s já está FAILED. Estorno redundante ignorado.",
                    w.id,
                )
                return w

            if w.status == WithdrawalRequest.WithdrawalStatus.PAID:
                raise ValueError(
                    f"Não é permitido estornar um saque com status PAID (ID: {w.id})."
                )

            # 1. Trava OperatorInternalWallet
            operator_wallet, _ = OperatorInternalWallet.objects.get_or_create(
                operator=w.operator
            )
            operator_wallet = (
                OperatorInternalWallet.objects.select_for_update().get(
                    pk=operator_wallet.pk
                )
            )

            # 2. Trava Driver Wallet
            driver_wallet, _ = Wallet.objects.get_or_create(
                driver=w.driver, operator=w.operator
            )
            driver_wallet = Wallet.objects.select_for_update().get(
                pk=driver_wallet.pk
            )

            # 3. Cria WalletTransaction de REFUND (Operator -> Driver)
            WalletTransaction.objects.create(
                operator=w.operator,
                source_operator_wallet=operator_wallet,
                destination_driver_wallet=driver_wallet,
                amountCents=w.amountCents,
                category=WalletTransaction.TransactionCategory.REFUND,
                taxCategory=WalletTransaction.TaxCategory.NON_TAXABLE_REIMBURSEMENT,
            )

            # 4. Atualiza o status do pedido de saque
            w.status = WithdrawalRequest.WithdrawalStatus.FAILED
            w.failureReason = reason
            w.rejectionReason = reason
            w.save(
                update_fields=[
                    "status",
                    "failureReason",
                    "rejectionReason",
                    "updatedAt",
                ]
            )

            logger.info(
                "Estorno concluído com sucesso para saque %s: R$ %s devolvidos ao motorista %s.",
                w.id,
                w.amountCents / 100,
                w.driver_id,
            )
            return w

