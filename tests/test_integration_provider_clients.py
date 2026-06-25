from types import SimpleNamespace
from unittest.mock import Mock, patch

from integration.provider_clients import (
    acknowledge_ifood_mercado_events,
    poll_ifood_mercado_events,
    resolve_base_url,
    resolve_webhook_url,
    send_open_delivery_order_status,
    should_skip_outbound_partner_status,
    uses_ifood_mercado_polling,
    uses_open_delivery_polling,
)


def make_integration(**overrides):
    defaults = {
        "id": "integration-1",
        "provider": "DELIVERY_DIRETO",
        "authMode": "POLLING_OPEN_DELIVERY",
        "baseUrl": "https://deliverydireto.com.br",
        "webhookUrl": "https://example.com/webhook",
        "clientId": "client-1",
        "get_client_secret": lambda: "secret-1",
        "get_api_key": lambda: "legacy-secret",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_resolve_base_url_uses_explicit_value():
    integration = make_integration(baseUrl="https://partner.example.com/")
    assert resolve_base_url(integration) == "https://partner.example.com"


def test_resolve_webhook_url_prefers_explicit_webhook():
    integration = make_integration(webhookUrl="https://hooks.example.com/order")
    assert resolve_webhook_url(integration) == "https://hooks.example.com/order"


def test_uses_open_delivery_polling_flag():
    assert uses_open_delivery_polling(make_integration(authMode="POLLING_OPEN_DELIVERY"))
    assert not uses_open_delivery_polling(make_integration(authMode="WEBHOOK"))


def test_uses_ifood_mercado_polling_flag():
    assert uses_ifood_mercado_polling(make_integration(authMode="POLLING_IFOOD_MERCADO"))
    assert not uses_ifood_mercado_polling(make_integration(authMode="WEBHOOK"))


@patch("integration.provider_clients.get_client_credentials_token", return_value="token-123")
@patch("integration.provider_clients.requests.post")
def test_send_open_delivery_order_status_delivered(mock_post: Mock, _mock_token: Mock):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    integration = make_integration()
    order = SimpleNamespace(external_order_id="external-order-1")

    response = send_open_delivery_order_status(integration, order, "ORDER_COMPLETED")

    assert response is mock_response
    called_url = mock_post.call_args[0][0]
    assert called_url.endswith("/open-delivery-api/v1/orders/external-order-1/delivered")


@patch("integration.provider_clients.get_client_credentials_token", return_value="token-123")
@patch("integration.provider_clients.requests.post")
def test_send_99food_open_delivery_order_status_uses_partner_root(mock_post: Mock, _mock_token: Mock):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    integration = make_integration(
        provider="99FOOD",
        authMode="POLLING_OPEN_DELIVERY",
        baseUrl="https://openapi.didi-food.com/v4/opendelivery",
    )
    order = SimpleNamespace(external_order_id="external-order-99")

    response = send_open_delivery_order_status(integration, order, "ORDER_STARTED")

    assert response is mock_response
    called_url = mock_post.call_args[0][0]
    assert called_url == "https://openapi.didi-food.com/v4/opendelivery/orders/external-order-99/pickedUp"


@patch("integration.provider_clients.requests.get")
def test_poll_ifood_mercado_events(mock_get: Mock):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [{"id": 1, "codigoPedido": "PED-1", "status": "PE0", "idLoja": 123}]
    mock_get.return_value = mock_response

    integration = make_integration(
        provider="IFOOD",
        authMode="POLLING_IFOOD_MERCADO",
        baseUrl="https://merchant.ifood.example",
        merchantId="123",
        get_api_key=lambda: "bearer-token",
    )

    events = poll_ifood_mercado_events(integration)

    assert events[0]["status"] == "PE0"
    called_url = mock_get.call_args[0][0]
    assert called_url.endswith("/pedido/eventos/123")


@patch("integration.provider_clients.requests.post")
def test_acknowledge_ifood_mercado_events(mock_post: Mock):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    integration = make_integration(
        provider="IFOOD",
        authMode="POLLING_IFOOD_MERCADO",
        baseUrl="https://merchant.ifood.example",
        get_api_key=lambda: "bearer-token",
    )
    acknowledge_ifood_mercado_events(integration, ["11", "12"])

    called_url = mock_post.call_args[0][0]
    called_json = mock_post.call_args.kwargs["json"]
    assert called_url.endswith("/pedido/eventos/verificado")
    assert called_json == [{"id": 11}, {"id": 12}]


def test_should_skip_outbound_partner_status_for_ifood_mercado():
    integration = make_integration(provider="IFOOD", authMode="POLLING_IFOOD_MERCADO")
    assert should_skip_outbound_partner_status(integration, "ORDER_COMPLETED")
    assert not should_skip_outbound_partner_status(integration, "ORDER_REASSIGNED")


def test_should_skip_outbound_partner_status_for_99food_delivery_confirmation():
    integration = make_integration(provider="99FOOD", authMode="POLLING_OPEN_DELIVERY")
    assert should_skip_outbound_partner_status(integration, "ORDER_COMPLETED")
    assert should_skip_outbound_partner_status(integration, "ORDER_ARRIVED")
    assert not should_skip_outbound_partner_status(integration, "ORDER_REASSIGNED")
