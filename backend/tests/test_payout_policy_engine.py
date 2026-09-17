import pytest
from unittest.mock import MagicMock, patch
from finance.models import (
    WithdrawalRequest,
    PayoutPolicyConfig,
    Contract,
    WalletTransaction,
    OperatorInternalWallet,
    Wallet,
)
from finance.services import PayoutPolicyEngine, PayoutEvaluation, AtomicRefundEngine


def test_payout_evaluation_default_system_under_threshold():
    """Sem política configurada, usa padrões seguros (<= R$ 150 -> AUTO_INSTANT, sem taxa)."""
    mock_operator = MagicMock()
    mock_driver = MagicMock()

    with patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_policy_filter, \
         patch("finance.models.Contract.objects.filter") as mock_contract_filter, \
         patch("logistics.models.Order.objects.filter") as mock_order_filter, \
         patch("finance.models.WithdrawalRequest.objects.filter") as mock_withdraw_filter:

        mock_policy_filter.return_value.first.return_value = None
        mock_contract_filter.return_value.first.return_value = None
        mock_order_filter.return_value.order_by.return_value.first.return_value = None
        mock_withdraw_filter.return_value.aggregate.return_value = {"total": 0}

        eval_res = PayoutPolicyEngine.evaluate_payout(
            operator=mock_operator,
            driver=mock_driver,
            amount_cents=10000,  # R$ 100,00
        )

        assert isinstance(eval_res, PayoutEvaluation)
        assert eval_res.approval_mode == WithdrawalRequest.ApprovalMode.AUTO_INSTANT
        assert eval_res.fee_amount_cents == 0
        assert eval_res.net_amount_cents == 10000
        assert eval_res.policy_source == "SYSTEM_DEFAULT"
        assert eval_res.notify_push is True
        assert eval_res.notify_whatsapp is True


def test_payout_evaluation_above_threshold():
    """Saques acima do teto devem ser classificados como MANUAL_PENDING."""
    mock_operator = MagicMock()
    mock_driver = MagicMock()

    with patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_policy_filter, \
         patch("finance.models.Contract.objects.filter") as mock_contract_filter, \
         patch("logistics.models.Order.objects.filter") as mock_order_filter, \
         patch("finance.models.WithdrawalRequest.objects.filter") as mock_withdraw_filter:

        mock_policy_filter.return_value.first.return_value = None
        mock_contract_filter.return_value.first.return_value = None
        mock_order_filter.return_value.order_by.return_value.first.return_value = None
        mock_withdraw_filter.return_value.aggregate.return_value = {"total": 0}

        eval_res = PayoutPolicyEngine.evaluate_payout(
            operator=mock_operator,
            driver=mock_driver,
            amount_cents=20000,  # R$ 200,00 (> R$ 150 default)
        )

        assert eval_res.approval_mode == WithdrawalRequest.ApprovalMode.MANUAL_PENDING
        assert "excede o teto automático" in eval_res.requires_manual_reason


def test_payout_evaluation_below_minimum_raises_error():
    """Saques abaixo do mínimo (R$ 10 default) devem levantar ValueError."""
    mock_operator = MagicMock()
    mock_driver = MagicMock()

    with patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_policy_filter, \
         patch("finance.models.Contract.objects.filter") as mock_contract_filter, \
         patch("logistics.models.Order.objects.filter") as mock_order_filter:

        mock_policy_filter.return_value.first.return_value = None
        mock_contract_filter.return_value.first.return_value = None
        mock_order_filter.return_value.order_by.return_value.first.return_value = None

        with pytest.raises(ValueError, match="valor mínimo"):
            PayoutPolicyEngine.evaluate_payout(
                operator=mock_operator,
                driver=mock_driver,
                amount_cents=500,  # R$ 5,00
            )


def test_payout_evaluation_fee_charged_to_driver():
    """Quando configurado para CHARGED_TO_DRIVER, desconta a taxa do líquido."""
    mock_operator = MagicMock()
    mock_driver = MagicMock()

    mock_policy = MagicMock()
    mock_policy.mode = PayoutPolicyConfig.PayoutMode.HYBRID_THRESHOLD
    mock_policy.autoThresholdCents = 15000
    mock_policy.dailyLimitPerDriverCents = 50000
    mock_policy.minWithdrawalCents = 1000
    mock_policy.payoutFeeMode = PayoutPolicyConfig.PayoutFeeMode.CHARGED_TO_DRIVER
    mock_policy.payoutFeeCents = 150  # R$ 1,50
    mock_policy.notifyPushEnabled = False
    mock_policy.notifyWhatsappEnabled = True

    with patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_policy_filter, \
         patch("finance.models.Contract.objects.filter") as mock_contract_filter, \
         patch("logistics.models.Order.objects.filter") as mock_order_filter, \
         patch("finance.models.WithdrawalRequest.objects.filter") as mock_withdraw_filter:

        mock_policy_filter.return_value.first.return_value = mock_policy
        mock_contract_filter.return_value.first.return_value = None
        mock_order_filter.return_value.order_by.return_value.first.return_value = None
        mock_withdraw_filter.return_value.aggregate.return_value = {"total": 0}

        eval_res = PayoutPolicyEngine.evaluate_payout(
            operator=mock_operator,
            driver=mock_driver,
            amount_cents=10000,  # R$ 100,00
        )

        assert eval_res.fee_amount_cents == 150
        assert eval_res.net_amount_cents == 9850
        assert eval_res.notify_push is False
        assert eval_res.notify_whatsapp is True


def test_payout_evaluation_store_contract_override():
    """Sobreposição contratual da Loja prevalece sobre a política global."""
    mock_operator = MagicMock()
    mock_driver = MagicMock()

    # Política global: R$ 150 de teto
    mock_global_policy = MagicMock()
    mock_global_policy.mode = PayoutPolicyConfig.PayoutMode.HYBRID_THRESHOLD
    mock_global_policy.autoThresholdCents = 15000
    mock_global_policy.dailyLimitPerDriverCents = 50000
    mock_global_policy.minWithdrawalCents = 1000
    mock_global_policy.payoutFeeMode = PayoutPolicyConfig.PayoutFeeMode.ABSORBED_BY_PLATFORM
    mock_global_policy.payoutFeeCents = 0

    # Contrato da loja com override: teto aumentado para R$ 300
    mock_contract = MagicMock()
    mock_contract.overridePayoutPolicy = True
    mock_contract.customPayoutMode = PayoutPolicyConfig.PayoutMode.HYBRID_THRESHOLD
    mock_contract.customAutoThresholdCents = 30000
    mock_contract.customFeeMode = PayoutPolicyConfig.PayoutFeeMode.CHARGED_TO_DRIVER
    mock_contract.customFeeCents = 200

    with patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_policy_filter, \
         patch("finance.models.Contract.objects.filter") as mock_contract_filter, \
         patch("finance.models.WithdrawalRequest.objects.filter") as mock_withdraw_filter:

        mock_policy_filter.return_value.first.return_value = mock_global_policy
        mock_contract_filter.return_value.first.return_value = mock_contract
        mock_withdraw_filter.return_value.aggregate.return_value = {"total": 0}

        eval_res = PayoutPolicyEngine.evaluate_payout(
            operator=mock_operator,
            driver=mock_driver,
            amount_cents=25000,  # R$ 250,00 (seria reprovado no global R$ 150, mas passa na loja R$ 300)
            store_id="store-uuid-123",
        )

        assert eval_res.policy_source == "STORE_OVERRIDE"
        assert eval_res.approval_mode == WithdrawalRequest.ApprovalMode.AUTO_INSTANT
        assert eval_res.fee_amount_cents == 200
        assert eval_res.net_amount_cents == 24800


def test_atomic_refund_engine_success():
    """Valida que o estorno cria a transação de contrapartida REFUND e atualiza o status."""
    mock_withdrawal = MagicMock(spec=WithdrawalRequest)
    mock_withdrawal.pk = "withdraw-uuid"
    mock_withdrawal.id = "withdraw-uuid"
    mock_withdrawal.status = WithdrawalRequest.WithdrawalStatus.PROCESSING
    mock_withdrawal.amountCents = 7500
    mock_withdrawal.operator = MagicMock()
    mock_withdrawal.driver = MagicMock()

    mock_op_wallet = MagicMock(spec=OperatorInternalWallet)
    mock_driver_wallet = MagicMock(spec=Wallet)

    with patch("django.db.transaction.atomic"), \
         patch("finance.models.WithdrawalRequest.objects.select_for_update") as mock_w_lock, \
         patch("finance.models.OperatorInternalWallet.objects.get_or_create", return_value=(mock_op_wallet, False)), \
         patch("finance.models.OperatorInternalWallet.objects.select_for_update") as mock_op_lock, \
         patch("finance.models.Wallet.objects.get_or_create", return_value=(mock_driver_wallet, False)), \
         patch("finance.models.Wallet.objects.select_for_update") as mock_d_lock, \
         patch("finance.models.WalletTransaction.objects.create") as mock_tx_create:

        mock_w_lock.return_value.get.return_value = mock_withdrawal
        mock_op_lock.return_value.get.return_value = mock_op_wallet
        mock_d_lock.return_value.get.return_value = mock_driver_wallet

        res = AtomicRefundEngine.refund_failed_withdrawal(
            withdrawal=mock_withdrawal,
            reason="Chave PIX incorreta",
        )

        # Verifica criação da transação de estorno
        mock_tx_create.assert_called_once()
        tx_kwargs = mock_tx_create.call_args[1]
        assert tx_kwargs["amountCents"] == 7500
        assert tx_kwargs["category"] == WalletTransaction.TransactionCategory.REFUND
        assert tx_kwargs["source_operator_wallet"] == mock_op_wallet
        assert tx_kwargs["destination_driver_wallet"] == mock_driver_wallet

        # Verifica atualização do status
        assert res.status == WithdrawalRequest.WithdrawalStatus.FAILED
        assert res.failureReason == "Chave PIX incorreta"
        assert res.rejectionReason == "Chave PIX incorreta"
