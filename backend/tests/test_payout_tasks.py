import pytest
from unittest.mock import MagicMock, patch
from finance.models import WithdrawalRequest, PayoutPolicyConfig
from finance.baas_client import BaasPayoutResult
from finance.tasks import execute_pix_payout_task, notify_payout_success_task


def test_execute_pix_payout_task_success():
    """Valida execução bem-sucedida do PIX BaaS na Celery task."""
    mock_self = MagicMock()
    mock_self.request.retries = 0
    mock_self.max_retries = 3

    mock_withdrawal = MagicMock(spec=WithdrawalRequest)
    mock_withdrawal.id = "w-123"
    mock_withdrawal.status = WithdrawalRequest.WithdrawalStatus.PENDING
    mock_withdrawal.netAmountCents = 15000
    mock_withdrawal.amountCents = 15000
    mock_withdrawal.pixKey = "12345678900"
    mock_withdrawal.pixKeyType = "CPF"

    mock_baas_result = BaasPayoutResult(
        success=True,
        tx_id="tx-efi-999",
        e2e_id="E0003816612345678",
        raw_response={"status": "REALIZADO", "e2eId": "E0003816612345678"},
    )

    with patch("django.db.transaction.atomic"), \
         patch("finance.models.WithdrawalRequest.objects.select_for_update") as mock_w_lock, \
         patch("finance.baas_client.EfiBaasClient.send_pix_to_key", return_value=mock_baas_result), \
         patch("finance.tasks.notify_payout_success_task.delay") as mock_notify:

        mock_w_lock.return_value.get.return_value = mock_withdrawal

        res = execute_pix_payout_task("w-123")

        assert res["status"] == "SUCCESS"
        assert res["tx_id"] == "tx-efi-999"
        assert mock_withdrawal.status == WithdrawalRequest.WithdrawalStatus.PAID
        assert mock_withdrawal.baasTransactionId == "tx-efi-999"
        mock_notify.assert_called_once_with("w-123")


def test_execute_pix_payout_task_permanent_failure_refunds():
    """Valida que falha permanente aciona estorno atômico e marca FAILED."""
    mock_withdrawal = MagicMock(spec=WithdrawalRequest)
    mock_withdrawal.id = "w-456"
    mock_withdrawal.status = WithdrawalRequest.WithdrawalStatus.PENDING
    mock_withdrawal.netAmountCents = 5000
    mock_withdrawal.amountCents = 5000
    mock_withdrawal.pixKey = "chave_invalida"
    mock_withdrawal.pixKeyType = "CPF"

    mock_baas_result = BaasPayoutResult(
        success=False,
        tx_id="tx-failed-123",
        error_message="Chave PIX não encontrada no DICT",
        is_transient_error=False,
    )

    with patch("django.db.transaction.atomic"), \
         patch("finance.models.WithdrawalRequest.objects.select_for_update") as mock_w_lock, \
         patch("finance.baas_client.EfiBaasClient.send_pix_to_key", return_value=mock_baas_result), \
         patch("finance.services.AtomicRefundEngine.refund_failed_withdrawal") as mock_refund:

        mock_w_lock.return_value.get.return_value = mock_withdrawal

        res = execute_pix_payout_task("w-456")

        assert res["status"] == "FAILED_REFUNDED"
        mock_refund.assert_called_once()


def test_notify_payout_success_task_channels():
    """Valida despacho de push e whatsapp respeitando a política configurada."""
    mock_withdrawal = MagicMock(spec=WithdrawalRequest)
    mock_withdrawal.id = "w-789"
    mock_withdrawal.netAmountCents = 12000
    mock_withdrawal.pixKey = "motoboy@email.com"
    mock_withdrawal.baasRawResponse = {"e2eId": "E123"}
    mock_withdrawal.driver.id = "driver-1"
    mock_withdrawal.driver.name = "Carlos Motoboy"
    mock_withdrawal.driver.phone = "+5511999998888"

    mock_policy = MagicMock(spec=PayoutPolicyConfig)
    mock_policy.notifyPushEnabled = True
    mock_policy.notifyWhatsappEnabled = True

    with patch("finance.models.WithdrawalRequest.objects.select_related") as mock_w_query, \
         patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_policy_query:

        mock_w_query.return_value.get.return_value = mock_withdrawal
        mock_policy_query.return_value.first.return_value = mock_policy

        res = notify_payout_success_task("w-789")

        assert res["push"] == "SENT"
        assert res["whatsapp"] == "SENT"
