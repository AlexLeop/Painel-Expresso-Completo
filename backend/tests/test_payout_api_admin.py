import json
import uuid
import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from django.utils import timezone

from finance.models import WithdrawalRequest, PayoutPolicyConfig
from finance.api_admin import (
    list_withdrawals,
    approve_withdrawal,
    reject_withdrawal,
    get_payout_policy,
    update_payout_policy,
    get_baas_balance,
)
from finance.webhooks import efi_pix_webhook
from shared_schemas.finance import (
    WithdrawalRejectionPayload,
    PayoutPolicyConfigSchema,
)


@pytest.fixture
def rf():
    return RequestFactory()


def test_list_withdrawals(rf):
    """Valida listagem de saques formatada para o console administrativo."""
    req = rf.get("/api/v1/admin/finance/withdrawals")
    req.auth = {"operator_id": str(uuid.uuid4())}

    mock_driver = MagicMock()
    mock_driver.id = uuid.uuid4()
    mock_driver.name = "Joao Motoboy"
    mock_driver.phone = "11988887777"

    mock_w = MagicMock()
    mock_w.id = uuid.uuid4()
    mock_w.driver = mock_driver
    mock_w.amountCents = 10000
    mock_w.feeAmountCents = 100
    mock_w.netAmountCents = 9900
    mock_w.status = "PENDING"
    mock_w.pixKey = "12345678900"
    mock_w.pixKeyType = "CPF"
    mock_w.approvalMode = "AUTO_INSTANT"
    mock_w.baasProvider = "EFI_PAY"
    mock_w.baasTransactionId = None
    mock_w.failureReason = None
    mock_w.rejectionReason = None
    mock_w.approvedAt = None
    mock_w.processedAt = None
    mock_w.createdAt = timezone.now()

    with patch("finance.api_admin._resolve_operator", return_value=(MagicMock(), None)), \
         patch("finance.models.WithdrawalRequest.objects.filter") as mock_filter:

        mock_qs = MagicMock()
        mock_qs.select_related.return_value.order_by.return_value.__getitem__.return_value = [mock_w]
        mock_filter.return_value = mock_qs

        res = list_withdrawals(req)
        assert len(res) == 1
        assert res[0].driver_name == "Joao Motoboy"
        assert res[0].netAmountCents == 9900


def test_approve_withdrawal(rf):
    """Valida aprovação de saque pendente e agendamento de task Celery."""
    withdrawal_id = uuid.uuid4()
    req = rf.post(f"/api/v1/admin/finance/withdrawals/{withdrawal_id}/approve")
    req.auth = {"operator_id": str(uuid.uuid4())}

    mock_w = MagicMock()
    mock_w.id = withdrawal_id
    mock_w.status = WithdrawalRequest.WithdrawalStatus.PENDING

    with patch("finance.api_admin._resolve_operator", return_value=(MagicMock(), MagicMock())), \
         patch("django.db.transaction.atomic"), \
         patch("django.db.transaction.on_commit") as mock_on_commit, \
         patch("finance.models.WithdrawalRequest.objects.select_for_update") as mock_lock:

        mock_lock.return_value.get.return_value = mock_w

        res = approve_withdrawal(req, withdrawal_id)

        assert res["success"] is True
        assert res["status"] == "PROCESSING"
        assert mock_w.status == WithdrawalRequest.WithdrawalStatus.PROCESSING
        mock_on_commit.assert_called_once()


def test_reject_withdrawal(rf):
    """Valida recusa com justificativa e acionamento de estorno na carteira."""
    withdrawal_id = uuid.uuid4()
    payload = WithdrawalRejectionPayload(reason="Chave PIX divergente do titular cadastrado")
    req = rf.post(f"/api/v1/admin/finance/withdrawals/{withdrawal_id}/reject")
    req.auth = {"operator_id": str(uuid.uuid4())}

    mock_w = MagicMock()
    mock_w.id = withdrawal_id
    mock_w.status = WithdrawalRequest.WithdrawalStatus.PENDING

    with patch("finance.api_admin._resolve_operator", return_value=(MagicMock(), MagicMock())), \
         patch("finance.models.WithdrawalRequest.objects.get", return_value=mock_w), \
         patch("finance.services.AtomicRefundEngine.refund_failed_withdrawal") as mock_refund:

        mock_refund.return_value = mock_w

        res = reject_withdrawal(req, withdrawal_id, payload)

        assert res["success"] is True
        assert res["status"] == "FAILED"
        mock_refund.assert_called_once_with(withdrawal=mock_w, reason=payload.reason)


def test_payout_policy_get_and_update(rf):
    """Valida leitura e persistência das configurações de política de saque."""
    req_get = rf.get("/api/v1/admin/finance/payout-policy")
    req_get.auth = {"operator_id": str(uuid.uuid4())}

    mock_policy = MagicMock(spec=PayoutPolicyConfig)
    mock_policy.mode = "HYBRID_THRESHOLD"
    mock_policy.autoThresholdCents = 20000
    mock_policy.dailyLimitPerDriverCents = 60000
    mock_policy.minWithdrawalCents = 1500
    mock_policy.payoutFeeMode = "CHARGED_TO_DRIVER"
    mock_policy.payoutFeeCents = 100
    mock_policy.notifyPushEnabled = True
    mock_policy.notifyWhatsappEnabled = True

    with patch("finance.api_admin._resolve_operator", return_value=(MagicMock(), None)), \
         patch("finance.models.PayoutPolicyConfig.objects.filter") as mock_filter, \
         patch("finance.models.PayoutPolicyConfig.objects.get_or_create", return_value=(mock_policy, False)):

        mock_filter.return_value.first.return_value = mock_policy

        # 1. GET
        policy_res = get_payout_policy(req_get)
        assert policy_res.autoThresholdCents == 20000

        # 2. PUT
        new_payload = PayoutPolicyConfigSchema(
            mode="MANUAL_ALL",
            autoThresholdCents=10000,
            dailyLimitPerDriverCents=40000,
            minWithdrawalCents=1000,
            payoutFeeMode="ABSORBED_BY_PLATFORM",
            payoutFeeCents=0,
            notifyPushEnabled=False,
            notifyWhatsappEnabled=True,
        )
        req_put = rf.put("/api/v1/admin/finance/payout-policy")
        req_put.auth = {"operator_id": str(uuid.uuid4())}

        updated = update_payout_policy(req_put, new_payload)
        assert updated.mode == "MANUAL_ALL"
        assert updated.notifyPushEnabled is False


def test_baas_balance_endpoint(rf):
    """Valida endpoint de consulta de saldo da conta jurídica Efí."""
    req = rf.get("/api/v1/admin/finance/baas-balance")
    req.auth = {"operator_id": str(uuid.uuid4())}

    with patch("finance.baas_client.EfiBaasClient.get_account_balance", return_value={"saldo": 1500.0, "saldo_cents": 150000, "mock": True}):
        res = get_baas_balance(req)
        assert res.saldo == 1500.0
        assert res.saldo_cents == 150000


def test_efi_pix_webhook(rf):
    """Valida recebimento assíncrono de webhook de liquidação SPI da Efí."""
    webhook_payload = {
        "pix": [
            {
                "endToEndId": "E0003816620260917120001",
                "txid": "baas-tx-123456",
                "valor": "50.00",
                "horario": "2026-09-17T12:00:00Z",
            }
        ]
    }
    req = rf.post(
        "/api/v1/webhooks/efi/pix?hmac=test-efi-webhook-hmac",
        data=json.dumps(webhook_payload),
        content_type="application/json",
        HTTP_X_CLIENT_CERT_VERIFIED="SUCCESS",
    )

    mock_w = MagicMock()
    mock_w.id = uuid.uuid4()
    mock_w.status = WithdrawalRequest.WithdrawalStatus.PROCESSING
    mock_w.baasRawResponse = {}

    with patch("django.db.transaction.atomic"), \
         patch("django.db.transaction.on_commit", side_effect=lambda callback: callback()), \
         patch("finance.models.WithdrawalRequest.objects.select_for_update") as mock_lock, \
         patch("finance.tasks.notify_payout_success_task.delay") as mock_notify:

        mock_lock.return_value.filter.return_value.first.return_value = mock_w

        resp = efi_pix_webhook(req)
        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["processed"] == 1
        assert mock_w.status == WithdrawalRequest.WithdrawalStatus.PAID
        mock_notify.assert_called_once_with(str(mock_w.id))
