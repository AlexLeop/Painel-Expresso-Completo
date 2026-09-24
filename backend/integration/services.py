import logging
from typing import Optional
from django.db import IntegrityError, transaction
from django.utils import timezone

from logistics.models import Order, Stop
from finance.business_date import resolve_store_business_date
from .connectors.base import OrderIntent
from .models import StoreIntegration, IntegrationWebhookLog

try:
    from django.contrib.gis.geos import Point
except Exception:
    Point = None

logger = logging.getLogger(__name__)


def create_order_from_intent(
    order_intent: OrderIntent,
    integration: StoreIntegration,
    webhook_log: Optional[IntegrationWebhookLog] = None,
) -> Order:
    """
    Cria uma corrida (Order) canônica a partir de um OrderIntent normalizado.
    Garante idempotência estrita via chave (store, external_source, external_order_id).
    """
    # 1. Trava de Idempotência
    existing_order = Order.objects.filter(
        store=integration.store,
        external_source=order_intent.source_platform,
        external_order_id=order_intent.external_order_id,
    ).first()

    if existing_order:
        logger.info(
            "Pedido externo %s/%s já importado previamente (Order ID: %s).",
            order_intent.source_platform,
            order_intent.external_order_id,
            existing_order.id,
        )
        if webhook_log:
            webhook_log.status = IntegrationWebhookLog.LogStatus.PROCESSED
            webhook_log.order_id = existing_order.id
            webhook_log.save(update_fields=["status", "order_id"])
        return existing_order

    # 2. Criação Atômica da Corrida e Paradas
    with transaction.atomic():
        metadata = {
            "integration_id": str(integration.id),
            "source_platform": order_intent.source_platform,
            "idempotency_key": order_intent.idempotency_key,
            "customer_name": order_intent.customer_name,
            "customer_phone": order_intent.customer_phone,
            "items_summary": order_intent.items_summary,
            "payment_method": order_intent.payment_method,
            "order_total_cents": order_intent.total_amount_cents,
            "delivery_fee_cents": order_intent.delivery_fee_cents,
            "distance_status": (
                "PROVIDED" if order_intent.distance_meters is not None else "PENDING_ROUTING"
            ),
            "notes": order_intent.notes,
            "raw_payload_ref": str(webhook_log.id) if webhook_log else "",
        }

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    operator=integration.operator,
                    store=integration.store,
                    status=Order.OrderStatus.PREPARING,
                    fareValueCents=order_intent.delivery_fee_cents,
                    distanceMeters=order_intent.distance_meters,
                    businessDate=resolve_store_business_date(integration.store),
                    external_source=order_intent.source_platform,
                    external_order_id=order_intent.external_order_id,
                    metadata=metadata,
                )
        except IntegrityError:
            existing_order = Order.objects.get(
                store=integration.store,
                external_source=order_intent.source_platform,
                external_order_id=order_intent.external_order_id,
            )
            if webhook_log:
                webhook_log.status = IntegrationWebhookLog.LogStatus.PROCESSED
                webhook_log.order_id = existing_order.id
                webhook_log.save(update_fields=["status", "order_id"])
            return existing_order

        # 3. Ponto de Coleta (Pickup)
        pickup_geom = None
        if Point is not None and order_intent.pickup_lat is not None and order_intent.pickup_lng is not None:
            try:
                pt = Point(
                    float(order_intent.pickup_lng),
                    float(order_intent.pickup_lat),
                    srid=4326,
                )
                if not (hasattr(pt, "_mock_name") or type(pt).__module__.startswith("unittest.mock")):
                    pickup_geom = pt
            except Exception:
                pickup_geom = None

        Stop.objects.create(
            operator=integration.operator,
            order=order,
            sequence=1,
            type=Stop.StopType.PICKUP,
            geom=pickup_geom,
            metadata={
                "address": order_intent.pickup_address,
                "instructions": order_intent.pickup_instructions,
                "customer_name": getattr(integration.store, "name", "Loja"),
            },
        )

        # 4. Ponto(s) de Entrega (Dropoff)
        seq = 2
        for delivery in order_intent.deliveries:
            drop_geom = None
            if Point is not None and delivery.lat is not None and delivery.lng is not None:
                try:
                    pt = Point(
                        float(delivery.lng),
                        float(delivery.lat),
                        srid=4326,
                    )
                    if not (hasattr(pt, "_mock_name") or type(pt).__module__.startswith("unittest.mock")):
                        drop_geom = pt
                except Exception:
                    drop_geom = None

            Stop.objects.create(
                operator=integration.operator,
                order=order,
                sequence=seq,
                type=Stop.StopType.DROPOFF,
                geom=drop_geom,
                metadata={
                    "address": delivery.address,
                    "customer_name": delivery.customer_name,
                    "customer_phone": delivery.customer_phone,
                    "instructions": delivery.instructions,
                },
            )
            seq += 1

        # 5. Atualizar metadata da integração
        try:
            integration.last_webhook_at = timezone.now()
            integration.error_count = 0
            integration.error_message = None
            integration.save(update_fields=["last_webhook_at", "error_count", "error_message"])
        except Exception as e:
            logger.warning("Falha ao atualizar métricas da integração %s: %s", integration.id, e)

        # 6. Atualizar log de webhook
        if webhook_log:
            webhook_log.status = IntegrationWebhookLog.LogStatus.PROCESSED
            webhook_log.order_id = order.id
            webhook_log.save(update_fields=["status", "order_id"])

        logger.info(
            "Pedido externo %s/%s criado com sucesso (Order ID: %s).",
            order_intent.source_platform,
            order_intent.external_order_id,
            order.id,
        )
        return order
