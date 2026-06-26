from celery import shared_task
from .models import IntegrationEventAudit, IntegrationOutbox, StoreIntegration
from logistics.models import Order, Proof
from accounts.models import Operator
from config.core_models import tenant_context
import requests
import redis
from config.redis_client import get_redis
from django.utils import timezone
import hashlib
import hmac

from .adapters import (
    build_outbound_event_payload,
    extract_external_order_id,
    extract_inbound_status,
    map_inbound_order_status,
    normalize_provider,
    parse_business_date,
    should_apply_inbound_status,
)
from finance.business_date import resolve_store_business_date
from .provider_clients import (
    acknowledge_ifood_mercado_events,
    acknowledge_open_delivery_events,
    poll_ifood_mercado_events,
    poll_open_delivery_events,
    resolve_webhook_url,
    send_open_delivery_order_status,
    should_skip_outbound_partner_status,
    uses_ifood_mercado_polling,
    uses_open_delivery_polling,
)

r = get_redis()


@shared_task(bind=True, max_retries=5)
def flush_outbox_events(self):
    """
    Varre a tabela IntegrationOutbox por eventos PENDING ou FAILED
    e dispara webhooks para os clientes (iFood, Hubster, etc).
    Implementa Exponential Backoff via Celery se o parceiro estiver offline.
    """
    operators = Operator.objects.values_list("id", flat=True)

    for operator_id in operators:
        # Deny-list de Operator (Nível B2B): Se o Operador está suspenso, nenhum evento sai.
        try:
            if r.get(f"deny_list:operator:{operator_id}"):
                continue
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            # Fail-Closed: Redis caiu, aborta este operador inteiro.
            continue

        # FASE 1: Coleta e Travamento Seguro (transação curta via tenant_context)
        processing_events = []
        with tenant_context(operator_id):
            events = list(
                IntegrationOutbox.objects.select_for_update(skip_locked=True).filter(
                    status__in=[
                        IntegrationOutbox.OutboxStatus.PENDING,
                        IntegrationOutbox.OutboxStatus.FAILED,
                    ]
                )[:50]
            )

            for event in events:
                event.status = IntegrationOutbox.OutboxStatus.PROCESSING
                processing_events.append(event)

            if processing_events:
                IntegrationOutbox.objects.bulk_update(processing_events, ["status"])

        if not processing_events:
            continue

        # FASE 2: I/O de Rede FORA de tenant_context (evita long-running transaction)
        # Cada evento abre e fecha seu próprio tenant_context para o save() final.
        for event in processing_events:
            order = None
            store = None
            integration = None
            provider = None
            outbound_payload = None
            latest_delivery_proof = None
            try:
                # Localiza a loja associada ao evento para pegar a credencial correta
                driver_id = None
                with tenant_context(operator_id):
                    if event.aggregateType == "ORDER":
                        order = Order.objects.get(id=event.aggregateId)
                        store = order.store
                        driver_id = order.driver_id
                        latest_delivery_proof = (
                            Proof.objects.filter(
                                operator_id=operator_id,
                                stop__order=order,
                                stage="DELIVERY",
                            )
                            .select_related("stop")
                            .order_by("-capturedAt")
                            .first()
                        )

                if not store:
                    raise Exception("Aggregate não suportado ou Loja não encontrada.")

                # Deny-list de Driver (Nível Individual): Manifesto IV.2
                if driver_id:
                    try:
                        if r.get(f"deny_list:driver:{driver_id}"):
                            with tenant_context(operator_id):
                                event.status = IntegrationOutbox.OutboxStatus.FAILED
                                event.failReason = (
                                    "BLOCKED_MID_FLIGHT: Driver na Deny-list."
                                )
                                event.lastAttemptAt = timezone.now()
                                event.save()
                            continue
                    except (
                        redis.exceptions.ConnectionError,
                        redis.exceptions.TimeoutError,
                    ):
                        # Fail-Closed (Manifesto IV.3)
                        with tenant_context(operator_id):
                            event.status = IntegrationOutbox.OutboxStatus.FAILED
                            event.failReason = "FAIL_CLOSED: Redis indisponível para checagem de Deny-list."
                            event.lastAttemptAt = timezone.now()
                            event.save()
                        continue

                # Tenta achar a integração ativa para despachar
                with tenant_context(operator_id):
                    integration = StoreIntegration.objects.filter(
                        store=store, active=True
                    ).first()
                    if not integration:
                        raise Exception("Loja não possui integração ativa.")
                    webhook_url = resolve_webhook_url(integration)
                    provider = normalize_provider(integration.provider)
                    outbound_payload = build_outbound_event_payload(
                        provider,
                        event.eventType,
                        event.payload,
                        order=order if event.aggregateType == "ORDER" else None,
                        integration=integration,
                        delivery_proof=latest_delivery_proof
                        if "latest_delivery_proof" in locals()
                        else None,
                        event_id=str(event.id),
                    )
                    headers = {"Content-Type": "application/json"}
                    if provider == "DELIVERY_DIRETO":
                        secret = integration.get_client_secret()
                        if not secret:
                            raise Exception(
                                "Segredo de integração ausente para DELIVERY_DIRETO."
                            )
                        body_bytes = requests.models.complexjson.dumps(
                            outbound_payload
                        ).encode("utf-8")
                        headers["X-DeliveryDireto-Signature"] = hmac.new(
                            secret.encode("utf-8"),
                            body_bytes,
                            hashlib.sha256,
                        ).hexdigest()
                        headers["X-DeliveryDireto-ID"] = integration.merchantId or ""

                if should_skip_outbound_partner_status(integration, event.eventType):
                    response = None
                elif uses_open_delivery_polling(integration) and provider in {
                    "DELIVERY_DIRETO",
                    "99FOOD",
                }:
                    response = send_open_delivery_order_status(
                        integration, order, event.eventType
                    )
                    if response is None:
                        raise Exception(
                            f"Evento {event.eventType} ainda não mapeado para Open Delivery."
                        )
                else:
                    if not webhook_url:
                        raise Exception(
                            "A URL do Webhook na StoreIntegration está vazia."
                        )
                    response = requests.post(
                        webhook_url, json=outbound_payload, headers=headers, timeout=5
                    )

                if response is None or response.status_code in [200, 201, 202, 204]:
                    with tenant_context(operator_id):
                        IntegrationEventAudit.objects.create(
                            operator_id=operator_id,
                            store=store,
                            order=order if event.aggregateType == "ORDER" else None,
                            provider=provider,
                            direction="OUTBOUND",
                            eventType=event.eventType,
                            externalEventId=str(event.id),
                            externalOrderId=order.external_order_id
                            if order and getattr(order, "external_order_id", None)
                            else None,
                            merchantReference=integration.merchantId,
                            deliveryStatus="NOT_REQUIRED"
                            if response is None
                            else "ACKNOWLEDGED",
                            httpStatusCode=None
                            if response is None
                            else response.status_code,
                            payload=outbound_payload,
                            responsePayload={
                                "text": None
                                if response is None
                                else response.text[:2000]
                            },
                            processedAt=timezone.now(),
                        )
                        event.status = IntegrationOutbox.OutboxStatus.SENT
                        event.lastAttemptAt = timezone.now()
                        event.save()
                else:
                    raise Exception(f"Webhook falhou com status {response.status_code}")

            except Exception as e:
                with tenant_context(operator_id):
                    if "store" in locals() and store:
                        IntegrationEventAudit.objects.create(
                            operator_id=operator_id,
                            store=store,
                            order=order
                            if "order" in locals() and event.aggregateType == "ORDER"
                            else None,
                            provider=provider if "provider" in locals() else "UNKNOWN",
                            direction="OUTBOUND",
                            eventType=event.eventType,
                            externalEventId=str(event.id),
                            externalOrderId=order.external_order_id
                            if "order" in locals()
                            and order
                            and getattr(order, "external_order_id", None)
                            else None,
                            merchantReference=integration.merchantId
                            if "integration" in locals() and integration
                            else None,
                            deliveryStatus="FAILED",
                            payload=outbound_payload
                            if "outbound_payload" in locals()
                            else event.payload,
                            failReason=str(e),
                            processedAt=timezone.now(),
                        )
                    event.status = IntegrationOutbox.OutboxStatus.FAILED
                    event.attempts += 1
                    event.failReason = str(e)
                    event.lastAttemptAt = timezone.now()
                    event.save()
                continue


@shared_task(bind=True, max_retries=5)
def poll_partner_events(self):
    integrations = StoreIntegration.objects.filter(
        active=True,
        authMode__in=["POLLING_OPEN_DELIVERY", "POLLING_IFOOD_MERCADO"],
        provider__in=["DELIVERY_DIRETO", "IFOOD", "99FOOD"],
    ).select_related("operator", "store")

    for integration in integrations:
        operator_id = integration.operator_id
        with tenant_context(operator_id):
            try:
                if uses_open_delivery_polling(integration) and integration.provider in {
                    "DELIVERY_DIRETO",
                    "99FOOD",
                }:
                    events = poll_open_delivery_events(integration)
                elif (
                    uses_ifood_mercado_polling(integration)
                    and integration.provider == "IFOOD"
                ):
                    events = poll_ifood_mercado_events(integration)
                else:
                    continue
                ack_ids = []
                for polled_event in events:
                    external_event_id = (
                        str(
                            polled_event.get("id")
                            or polled_event.get("eventId")
                            or polled_event.get("event_id")
                            or ""
                        )
                        or None
                    )
                    external_order_id = (
                        str(
                            polled_event.get("orderId")
                            or polled_event.get("order_id")
                            or ""
                        )
                        or None
                    )
                    audit = IntegrationEventAudit.objects.create(
                        operator=integration.operator,
                        store=integration.store,
                        provider=integration.provider,
                        direction="INBOUND",
                        eventType=polled_event.get("code")
                        or polled_event.get("eventType")
                        or "POLLING_EVENT",
                        externalEventId=external_event_id,
                        externalOrderId=external_order_id,
                        merchantReference=integration.merchantId,
                        deliveryStatus="RECEIVED",
                        payload=polled_event,
                    )
                    IntegrationOutbox.objects.create(
                        operator=integration.operator,
                        aggregateType="WEBHOOK_IN",
                        aggregateId=integration.store_id,
                        eventType=f"{integration.provider}_WEBHOOK_RECEIVED",
                        payload={
                            "audit_id": str(audit.id),
                            "store_id": str(integration.store_id),
                            "raw_payload": polled_event,
                            "headers": {},
                        },
                        status=IntegrationOutbox.OutboxStatus.PENDING,
                    )
                    if external_event_id:
                        ack_ids.append(external_event_id)

                if ack_ids:
                    if uses_open_delivery_polling(integration):
                        acknowledge_open_delivery_events(integration, ack_ids[:100])
                    elif uses_ifood_mercado_polling(integration):
                        acknowledge_ifood_mercado_events(integration, ack_ids[:100])
            except Exception as exc:
                IntegrationEventAudit.objects.create(
                    operator=integration.operator,
                    store=integration.store,
                    provider=integration.provider,
                    direction="INBOUND",
                    eventType="POLLING_FAILED",
                    merchantReference=integration.merchantId,
                    deliveryStatus="FAILED",
                    failReason=str(exc),
                    processedAt=timezone.now(),
                )


@shared_task(bind=True, max_retries=5)
def process_inbound_webhooks(self):
    """
    Consome os payloads de webhooks (iFood, Hubster, etc) armazenados no
    IntegrationOutbox e processa-os (Adapter Pattern) criando as Orders de
    forma idempotente usando external_order_id.
    """
    operators = Operator.objects.values_list("id", flat=True)

    for operator_id in operators:
        processing_events = []
        with tenant_context(operator_id):
            events = list(
                IntegrationOutbox.objects.select_for_update(skip_locked=True).filter(
                    aggregateType="WEBHOOK_IN",
                    status__in=[
                        IntegrationOutbox.OutboxStatus.PENDING,
                        IntegrationOutbox.OutboxStatus.FAILED,
                    ],
                )[:50]
            )

            for event in events:
                event.status = IntegrationOutbox.OutboxStatus.PROCESSING
                processing_events.append(event)

            if processing_events:
                IntegrationOutbox.objects.bulk_update(processing_events, ["status"])

        if not processing_events:
            continue

        for event in processing_events:
            try:
                envelope = event.payload
                payload = (
                    envelope.get("raw_payload") or envelope.get("body") or envelope
                )
                # Aqui entra o Adapter Pattern de cada PDV.
                source = normalize_provider(
                    event.eventType.replace("_WEBHOOK_RECEIVED", "")
                )
                store_id = envelope.get("store_id")
                external_id = extract_external_order_id(payload)

                if not store_id or not external_id:
                    raise ValueError("Payload missing store_id or id")

                with tenant_context(operator_id):
                    # get_or_create garante idempotência (UNIQUE INDEX no banco)
                    business_dt = parse_business_date(payload)
                    external_status = extract_inbound_status(source, payload)
                    mapped_status = map_inbound_order_status(source, payload)
                    store = (
                        StoreIntegration.objects.select_related("store")
                        .get(store_id=store_id)
                        .store
                    )
                    resolved_business_date = resolve_store_business_date(
                        store,
                        explicit_business_date=business_dt.date()
                        if business_dt
                        else None,
                        reference_dt=business_dt,
                    )
                    order, created = Order.objects.get_or_create(
                        store_id=store_id,
                        external_source=source,
                        external_order_id=external_id,
                        defaults={
                            "fareValueCents": payload.get("fareValueCents", 500),
                            "distanceMeters": payload.get("distanceMeters", 1500),
                            "businessDate": resolved_business_date,
                            "status": Order.OrderStatus.PREPARING,
                        },
                    )
                    if not created and should_apply_inbound_status(
                        order.status, mapped_status
                    ):
                        try:
                            order.status = mapped_status
                            order.save(update_fields=["status"])
                        except Exception:
                            pass

                    audit_id = envelope.get("audit_id")
                    if audit_id:
                        IntegrationEventAudit.objects.filter(
                            pk=audit_id,
                            operator_id=operator_id,
                        ).update(
                            order=order,
                            deliveryStatus="PROCESSED",
                            processedAt=timezone.now(),
                            responsePayload={
                                "order_id": str(order.id),
                                "created": created,
                                "external_status": external_status,
                                "mapped_status": mapped_status,
                                "business_date": order.businessDate.isoformat()
                                if order.businessDate
                                else None,
                            },
                        )

                    event.status = IntegrationOutbox.OutboxStatus.SENT  # Tratado
                    event.lastAttemptAt = timezone.now()
                    event.save()

            except Exception as e:
                with tenant_context(operator_id):
                    event.status = IntegrationOutbox.OutboxStatus.FAILED
                    event.attempts += 1
                    event.failReason = str(e)
                    event.lastAttemptAt = timezone.now()
                    event.save()
                continue
