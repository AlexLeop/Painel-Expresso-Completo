import pytest
from finance.models import WithdrawalRequest, PayoutPolicyConfig, Contract


def test_payout_policy_config_model_fields():
    """Valida que o modelo PayoutPolicyConfig possui todos os campos e choices da especificação."""
    assert hasattr(PayoutPolicyConfig, "PayoutMode")
    assert PayoutPolicyConfig.PayoutMode.HYBRID_THRESHOLD == "HYBRID_THRESHOLD"
    assert PayoutPolicyConfig.PayoutMode.MANUAL_ALL == "MANUAL_ALL"

    assert hasattr(PayoutPolicyConfig, "PayoutFeeMode")
    assert PayoutPolicyConfig.PayoutFeeMode.ABSORBED_BY_PLATFORM == "ABSORBED_BY_PLATFORM"
    assert PayoutPolicyConfig.PayoutFeeMode.CHARGED_TO_DRIVER == "CHARGED_TO_DRIVER"

    fields = {f.name for f in PayoutPolicyConfig._meta.get_fields()}
    expected_fields = {
        "id",
        "operator",
        "mode",
        "autoThresholdCents",
        "dailyLimitPerDriverCents",
        "minWithdrawalCents",
        "payoutFeeMode",
        "payoutFeeCents",
        "notifyPushEnabled",
        "notifyWhatsappEnabled",
        "createdAt",
        "updatedAt",
    }
    assert expected_fields.issubset(fields), f"Campos faltantes: {expected_fields - fields}"
    assert PayoutPolicyConfig._meta.db_table == "PayoutPolicyConfig"
    assert PayoutPolicyConfig._meta.managed is False


def test_withdrawal_request_model_evolved_fields():
    """Valida que WithdrawalRequest possui os novos campos para BaaS PIX imediato."""
    assert hasattr(WithdrawalRequest, "PixKeyType")
    assert WithdrawalRequest.PixKeyType.CPF == "CPF"
    assert WithdrawalRequest.PixKeyType.CNPJ == "CNPJ"
    assert WithdrawalRequest.PixKeyType.EMAIL == "EMAIL"
    assert WithdrawalRequest.PixKeyType.PHONE == "PHONE"
    assert WithdrawalRequest.PixKeyType.EVP == "EVP"

    assert hasattr(WithdrawalRequest, "ApprovalMode")
    assert WithdrawalRequest.ApprovalMode.AUTO_INSTANT == "AUTO_INSTANT"
    assert WithdrawalRequest.ApprovalMode.MANUAL_PENDING == "MANUAL_PENDING"

    fields = {f.name for f in WithdrawalRequest._meta.get_fields()}
    expected_fields = {
        "pixKeyType",
        "approvalMode",
        "feeAmountCents",
        "netAmountCents",
        "approvedBy",
        "approvedAt",
        "rejectionReason",
        "baasProvider",
        "baasTransactionId",
        "baasRawResponse",
        "failureReason",
        "processedAt",
    }
    assert expected_fields.issubset(fields), f"Campos faltantes: {expected_fields - fields}"


def test_contract_model_payout_override_fields():
    """Valida que Contract possui os campos de sobreposição de política de saque da loja."""
    fields = {f.name for f in Contract._meta.get_fields()}
    expected_fields = {
        "overridePayoutPolicy",
        "customPayoutMode",
        "customAutoThresholdCents",
        "customFeeMode",
        "customFeeCents",
    }
    assert expected_fields.issubset(fields), f"Campos faltantes: {expected_fields - fields}"
