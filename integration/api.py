from ninja import Router
from django.http import HttpRequest
from typing import Dict, Any

from .models import IntegrationEventAudit, IntegrationOutbox, StoreIntegration
from .adapters import (
    build_outbound_event_payload,
    extract_external_order_id,
    extract_merchant_reference,
    normalize_provider,
    verify_inbound_signature,
)

router = Router()


@router.post(
    "/webhooks/{source}", auth=None, response={202: dict, 401: dict, 404: dict}
)
def receive_webhook(request: HttpRequest, source: str, payload: Dict[Any, Any]):
    """
    Gateway de Ingestão Externa (Multi-PDVs).
    Recebe webhooks de plataformas parceiras (iFood, Hubster, etc) sem travar.
    Retorna 202 Accepted imediatamente e enfileira no IntegrationOutbox.
    """
    provider = normalize_provider(source)
    raw_body = request.body
    request_headers = dict(request.headers.items())
    request_query = dict(request.GET.items())
    merchant_reference = extract_merchant_reference(provider, request_headers, payload)
    external_order_id = extract_external_order_id(payload)

    integration = StoreIntegration.objects.filter(
        provider=provider,
        active=True,
    )
    if merchant_reference:
        integration = integration.filter(merchantId=merchant_reference)
    integration = integration.select_related("operator", "store").first()

    if not integration:
        return 404, {
            "error": "Integração de loja não encontrada para o webhook recebido.",
            "provider": provider,
            "merchant_reference": merchant_reference,
        }

    integration_secret = integration.get_client_secret() or integration.get_api_key()
    if not verify_inbound_signature(
        provider, raw_body, request_headers, integration_secret, request_query
    ):
        return 401, {"error": "Assinatura do webhook inválida."}

    audit = IntegrationEventAudit.objects.create(
        operator=integration.operator,
        store=integration.store,
        provider=provider,
        direction="INBOUND",
        eventType=f"{provider}_WEBHOOK_RECEIVED",
        externalEventId=payload.get("id")
        or payload.get("eventId")
        or payload.get("event_id"),
        externalOrderId=external_order_id,
        merchantReference=merchant_reference,
        deliveryStatus="RECEIVED",
        payload=payload,
        responsePayload={"headers": request_headers},
    )

    IntegrationOutbox.objects.create(
        operator=integration.operator,
        aggregateType="WEBHOOK_IN",
        aggregateId=integration.store_id,
        eventType=f"{provider}_WEBHOOK_RECEIVED",
        payload=build_outbound_event_payload(
            provider,
            f"{provider}_WEBHOOK_RECEIVED",
            {
                "merchant_id": merchant_reference,
                "external_order_id": external_order_id,
                "occurred_at": payload.get("createdAt"),
                "body": payload,
            },
        )
        | {
            "audit_id": str(audit.id),
            "store_id": str(integration.store_id),
            "raw_payload": payload,
            "headers": request_headers,
        },
        status=IntegrationOutbox.OutboxStatus.PENDING,
    )

    return 202, {
        "status": "accepted",
        "provider": provider,
        "store_id": str(integration.store_id),
        "external_order_id": external_order_id,
    }
