import pytest
from unittest.mock import patch, MagicMock
from finance.baas_client import EfiBaasClient, BaasPayoutResult, EfiBaasError


def test_sanitize_pix_keys():
    """Valida as regras de sanitização de chaves PIX de acordo com o Bacen."""
    # CPF
    assert EfiBaasClient.sanitize_pix_key("123.456.789-00", "CPF") == "12345678900"
    # CNPJ
    assert EfiBaasClient.sanitize_pix_key("12.345.678/0001-99", "CNPJ") == "12345678000199"
    # Telefone
    assert EfiBaasClient.sanitize_pix_key("(11) 98765-4321", "PHONE") == "+5511987654321"
    assert EfiBaasClient.sanitize_pix_key("+5511987654321", "PHONE") == "+5511987654321"
    # E-mail
    assert EfiBaasClient.sanitize_pix_key(" Motoboy@Email.Com ", "EMAIL") == "motoboy@email.com"
    # EVP
    assert EfiBaasClient.sanitize_pix_key(" 123e4567-e89b-12d3-a456-426614174000 ", "EVP") == "123e4567-e89b-12d3-a456-426614174000"


def test_mock_mode_send_pix():
    """Valida que o modo mock retorna resultado de sucesso simulado com e2e_id."""
    client = EfiBaasClient(mock_mode=True)
    result = client.send_pix_to_key(
        amount_cents=5000,
        destination_key="12345678900",
        destination_key_type="CPF",
    )
    assert isinstance(result, BaasPayoutResult)
    assert result.success is True
    assert result.tx_id is not None
    assert result.e2e_id is not None
    assert result.e2e_id.startswith("E00038166")
    assert result.raw_response.get("status") == "REALIZADO"


def test_mock_mode_get_balance():
    """Valida consulta de saldo em modo mock."""
    client = EfiBaasClient(mock_mode=True)
    balance = client.get_account_balance()
    assert balance["saldo_cents"] > 0
    assert balance["saldo"] == balance["saldo_cents"] / 100
    assert balance["mock"] is True


def test_send_pix_zero_or_negative():
    """Valida que valores <= 0 são rejeitados de imediato."""
    client = EfiBaasClient(mock_mode=True)
    res_zero = client.send_pix_to_key(0, "12345678900", "CPF")
    assert res_zero.success is False
    assert res_zero.error_message is not None
    assert "inválido" in res_zero.error_message


@patch("finance.baas_client.httpx.Client")
def test_real_http_send_pix_success(mock_client_class):
    """Valida envio PIX com resposta HTTP 201 da Efí."""
    mock_http = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_http

    # Mock de OAuth token
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "valid_token", "expires_in": 3600}

    # Mock de PUT Pix
    mock_pix_resp = MagicMock()
    mock_pix_resp.status_code = 201
    mock_pix_resp.json.return_value = {
        "idEnvio": "test_id_123",
        "e2eId": "E12345678901234567890",
        "status": "REALIZADO",
    }

    mock_http.post.return_value = mock_token_resp
    mock_http.put.return_value = mock_pix_resp

    client = EfiBaasClient(
        client_id="dummy_id",
        client_secret="dummy_secret",
        mock_mode=False,
    )

    result = client.send_pix_to_key(
        amount_cents=10000,
        destination_key="11999999999",
        destination_key_type="PHONE",
        correlation_id="test_id_123",
    )

    assert result.success is True
    assert result.tx_id == "test_id_123"
    assert result.e2e_id == "E12345678901234567890"


@patch("finance.baas_client.httpx.Client")
def test_real_http_send_pix_transient_error(mock_client_class):
    """Valida que erro HTTP 500 ou 429 da Efí marca is_transient_error=True para retry."""
    mock_http = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_http

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "valid_token", "expires_in": 3600}

    mock_pix_resp = MagicMock()
    mock_pix_resp.status_code = 503
    mock_pix_resp.json.return_value = {"mensagem": "Bacen SPI temporariamente indisponível"}

    mock_http.post.return_value = mock_token_resp
    mock_http.put.return_value = mock_pix_resp

    client = EfiBaasClient(
        client_id="dummy_id",
        client_secret="dummy_secret",
        mock_mode=False,
    )

    result = client.send_pix_to_key(
        amount_cents=2500,
        destination_key="12345678900",
        destination_key_type="CPF",
    )

    assert result.success is False
    assert result.is_transient_error is True
    assert result.error_message is not None
    assert "503" in result.error_message
