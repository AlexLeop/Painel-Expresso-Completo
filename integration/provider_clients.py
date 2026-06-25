from typing import Dict, Iterable, List, Optional

import requests
from django.core.cache import cache


DEFAULT_BASE_URLS = {
    "DELIVERY_DIRETO": "https://deliverydireto.com.br",
    "IFOOD": "https://merchant-api.ifood.com.br",
    "99FOOD": "https://openapi.didi-food.com/v4/opendelivery",
}


def resolve_base_url(integration) -> str:
    base_url = integration.baseUrl or DEFAULT_BASE_URLS.get(integration.provider)
    if not base_url:
        raise ValueError("Base URL da integração não configurada.")
    return str(base_url).rstrip("/")


def resolve_webhook_url(integration) -> Optional[str]:
    return integration.webhookUrl or integration.get_api_key()


def uses_open_delivery_polling(integration) -> bool:
    return integration.authMode == "POLLING_OPEN_DELIVERY"


def uses_ifood_mercado_polling(integration) -> bool:
    return integration.authMode == "POLLING_IFOOD_MERCADO"


def _token_cache_key(integration) -> str:
    return f"integration:access-token:{integration.id}"


def _open_delivery_api_base(integration) -> str:
    base_url = resolve_base_url(integration)
    if integration.provider == "99FOOD":
        return base_url
    return f"{base_url}/open-delivery-api/v1"


def get_client_credentials_token(integration) -> str:
    if not integration.clientId or not integration.get_client_secret():
        raise ValueError("Credenciais OAuth não configuradas para a integração.")

    cache_key = _token_cache_key(integration)
    cached_token = cache.get(cache_key)
    if cached_token:
        return cached_token

    token_url = f"{_open_delivery_api_base(integration)}/oauth/token"
    response = requests.post(
        token_url,
        json={
            "client_id": integration.clientId,
            "client_secret": integration.get_client_secret(),
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload["access_token"]
    expires_in = max(int(payload.get("expires_in", 300)) - 60, 60)
    cache.set(cache_key, access_token, timeout=expires_in)
    return access_token


def _open_delivery_headers(integration) -> Dict[str, str]:
    token = get_client_credentials_token(integration)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _bearer_api_headers(integration) -> Dict[str, str]:
    token = integration.get_api_key()
    if not token:
        raise ValueError("Token Bearer não configurado para a integração.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def poll_open_delivery_events(integration, event_types: Optional[Iterable[str]] = None) -> List[dict]:
    response = requests.get(
        f"{_open_delivery_api_base(integration)}/events:polling",
        headers=_open_delivery_headers(integration),
        params={"eventType": list(event_types)} if event_types else None,
        timeout=15,
    )
    if response.status_code == 204:
        return []
    response.raise_for_status()
    return response.json()


def acknowledge_open_delivery_events(integration, event_ids: Iterable[str]) -> None:
    acknowledgments = [{"id": event_id} for event_id in event_ids if event_id]
    if not acknowledgments:
        return
    response = requests.post(
        f"{_open_delivery_api_base(integration)}/acknowledgment",
        headers=_open_delivery_headers(integration),
        json=acknowledgments,
        timeout=15,
    )
    response.raise_for_status()


def send_open_delivery_order_status(integration, order, event_type: str) -> Optional[requests.Response]:
    if not getattr(order, "external_order_id", None):
        raise ValueError("Pedido sem external_order_id para envio ao parceiro.")

    path_map = {
        "ORDER_STARTED": "pickedUp",
        "ORDER_COMPLETED": "delivered",
    }
    action = path_map.get(event_type)
    if not action:
        return None

    response = requests.post(
        f"{_open_delivery_api_base(integration)}/orders/{order.external_order_id}/{action}",
        headers=_open_delivery_headers(integration),
        timeout=15,
    )
    response.raise_for_status()
    return response


def poll_ifood_mercado_events(integration) -> List[dict]:
    merchant_id = integration.merchantId
    if not merchant_id:
        raise ValueError("merchantId/idLoja não configurado para iFood Mercado.")
    response = requests.get(
        f"{resolve_base_url(integration)}/pedido/eventos/{merchant_id}",
        headers=_bearer_api_headers(integration),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def acknowledge_ifood_mercado_events(integration, event_ids: Iterable[str]) -> None:
    acknowledgments = [{"id": int(event_id)} for event_id in event_ids if str(event_id).strip()]
    if not acknowledgments:
        return
    response = requests.post(
        f"{resolve_base_url(integration)}/pedido/eventos/verificado",
        headers=_bearer_api_headers(integration),
        json=acknowledgments,
        timeout=15,
    )
    response.raise_for_status()


def should_skip_outbound_partner_status(integration, event_type: str) -> bool:
    if uses_open_delivery_polling(integration) and integration.provider == "99FOOD":
        return event_type in {"ORDER_STARTED", "ORDER_COMPLETED", "ORDER_ARRIVED"}
    if uses_ifood_mercado_polling(integration) and integration.provider == "IFOOD":
        return event_type in {"ORDER_STARTED", "ORDER_COMPLETED", "ORDER_ARRIVED"}
    return False
