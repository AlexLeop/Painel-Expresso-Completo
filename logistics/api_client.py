import os
from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone as django_tz
from ninja import Router

from accounts.auth import client_portal_required
from integration.models import IntegrationOutbox
from finance.business_date import resolve_store_business_date
from .models import (
    Driver,
    DriverCommunicationMessage,
    DriverCommunicationThread,
    Order,
    OrderAssignmentAudit,
    Stop,
    Store,
    StoreDriver,
)
from .schemas import (
    ClientDispatchOrderPayload,
    CommunicationMessagePayload,
    CommunicationThreadCreatePayload,
    OrderReassignmentPayload,
    OrderSchema,
)
from .api_driver import _serialize_point, broadcast_disappearing_card, clear_order_runtime_state

router = Router(tags=["Client"])


def _client_stores(client_user):
    return Store.objects.filter(
        operator=client_user.operator,
        client=client_user.client,
    )


def _get_client_order(client_user, order_id: UUID) -> Optional[Order]:
    return Order.objects.filter(
        pk=order_id,
        operator=client_user.operator,
        store__client=client_user.client,
    ).select_related("store", "driver").first()


def _clear_order_runtime_state(order: Order, previous_driver_id: Optional[UUID]):
    clear_order_runtime_state(order, previous_driver_id)


def _serialize_thread(thread: DriverCommunicationThread) -> Dict:
    latest_message = DriverCommunicationMessage.objects.filter(
        thread=thread
    ).order_by("-createdAt").first()
    return {
        "thread_id": str(thread.id),
        "order_id": str(thread.order_id) if thread.order_id else None,
        "store_id": str(thread.store_id) if thread.store_id else None,
        "driver_id": str(thread.driver_id),
        "status": thread.status,
        "source_type": thread.sourceType,
        "subject": thread.subject,
        "created_at": thread.createdAt.isoformat() if thread.createdAt else None,
        "updated_at": thread.updatedAt.isoformat() if thread.updatedAt else None,
        "latest_message": {
            "message_id": str(latest_message.id),
            "sender_type": latest_message.senderType,
            "sender_name": latest_message.senderName,
            "message": latest_message.message,
            "created_at": latest_message.createdAt.isoformat() if latest_message.createdAt else None,
        } if latest_message else None,
    }


@router.get("/dashboard", response=Dict)
def get_client_dashboard(request):
    client_user = client_portal_required(request)
    stores = _client_stores(client_user)
    today = django_tz.localdate()
    orders = Order.objects.filter(
        operator=client_user.operator,
        store__in=stores,
        businessDate=today,
    )
    active_orders = orders.filter(
        status__in=[
            Order.OrderStatus.OFFERED,
            Order.OrderStatus.ACCEPTED,
            Order.OrderStatus.STARTED,
            Order.OrderStatus.ARRIVED,
        ]
    )
    live_drivers = Driver.objects.filter(
        operator=client_user.operator,
        order__store__in=stores,
        online=True,
    ).distinct().count()

    return {
        "client_id": str(client_user.client_id),
        "stores": stores.count(),
        "orders_today": orders.count(),
        "active_orders": active_orders.count(),
        "live_drivers": live_drivers,
    }


@router.get("/orders", response=List[OrderSchema])
def list_client_orders(request, status: Optional[str] = None, store_id: Optional[UUID] = None):
    client_user = client_portal_required(request)
    stores = _client_stores(client_user)
    orders = Order.objects.filter(
        operator=client_user.operator,
        store__in=stores,
    )
    if status:
        orders = orders.filter(status=status)
    if store_id:
        orders = orders.filter(store_id=store_id)
    return list(orders.select_related("store", "driver").order_by("-requestedAt")[:200])


@router.post("/orders/dispatch", response=OrderSchema)
def dispatch_client_order(request, payload: ClientDispatchOrderPayload):
    client_user = client_portal_required(request)
    store = _client_stores(client_user).filter(pk=payload.store_id).first()
    if not store:
        from ninja.errors import HttpError
        raise HttpError(404, "Loja não encontrada para este cliente.")

    driver = None
    if payload.driver_id:
        driver = Driver.objects.filter(
            pk=payload.driver_id,
            operator=client_user.operator,
        ).first()
        if not driver:
            from ninja.errors import HttpError
            raise HttpError(404, "Motorista não encontrado para este operador.")

    resolved_business_date = resolve_store_business_date(
        store,
        explicit_business_date=payload.businessDate,
    )
    order = Order.objects.create(
        operator=client_user.operator,
        store=store,
        driver=driver,
        status=Order.OrderStatus.OFFERED,
        fareValueCents=payload.fareValueCents,
        distanceMeters=payload.distanceMeters,
        businessDate=resolved_business_date,
    )
    broadcast_disappearing_card(client_user.operator_id, order.id)
    return order


@router.get("/drivers/live", response=List[dict])
def list_live_drivers(request):
    client_user = client_portal_required(request)
    drivers = Driver.objects.filter(
        operator=client_user.operator,
    ).filter(
        Q(storedriver__store__client=client_user.client) |
        Q(order__store__client=client_user.client)
    ).distinct().order_by("-online", "name")

    return [
        {
            "driver_id": str(driver.id),
            "name": driver.name,
            "online": driver.online,
            "active": driver.active,
            "status": getattr(driver, "operational_status", "OFFLINE"),
            "last_ping_at": driver.lastPingAt.isoformat() if driver.lastPingAt else None,
            "location": _serialize_point(driver.geom),
        }
        for driver in drivers
    ]


@router.post("/orders/{order_id}/reassign", response={200: dict, 404: dict, 409: dict})
def reassign_client_order(request, order_id: UUID, payload: OrderReassignmentPayload):
    client_user = client_portal_required(request)
    order = _get_client_order(client_user, order_id)
    if not order:
        return 404, {"error": "Ordem não encontrada para este cliente."}

    if order.status not in {Order.OrderStatus.OFFERED, Order.OrderStatus.ACCEPTED}:
        return 409, {"error": "A ordem não está em estado seguro para redistribuição."}

    new_driver = None
    if payload.new_driver_id:
        new_driver = Driver.objects.filter(
            pk=payload.new_driver_id,
            operator=client_user.operator,
        ).first()
        if not new_driver:
            return 404, {"error": "Novo motorista não encontrado."}

    previous_driver = order.driver
    with transaction.atomic():
        order.driver = new_driver
        order.status = Order.OrderStatus.OFFERED
        order.acceptedAt = None
        order.save(update_fields=["driver", "status", "acceptedAt"])

        OrderAssignmentAudit.objects.create(
            operator=client_user.operator,
            order=order,
            previousDriver=previous_driver,
            newDriver=new_driver,
            changedByClient=client_user,
            reason=payload.reason,
        )

        IntegrationOutbox.objects.create(
            operator=client_user.operator,
            aggregateType="ORDER",
            aggregateId=order.id,
            eventType="ORDER_REASSIGNED",
            payload={
                "order_id": str(order.id),
                "store_id": str(order.store_id),
                "previous_driver_id": str(previous_driver.id) if previous_driver else None,
                "new_driver_id": str(new_driver.id) if new_driver else None,
                "reason": payload.reason,
                "changed_by_client_id": str(client_user.id),
                "occurred_at": django_tz.now().isoformat(),
            },
        )

    _clear_order_runtime_state(order, previous_driver.id if previous_driver else None)
    broadcast_disappearing_card(client_user.operator_id, order.id)

    return 200, {
        "order_id": str(order.id),
        "status": order.status,
        "driver_id": str(order.driver_id) if order.driver_id else None,
    }


@router.get("/communications/threads", response=List[dict])
def list_client_threads(request):
    client_user = client_portal_required(request)
    threads = DriverCommunicationThread.objects.filter(
        operator=client_user.operator,
    ).filter(
        Q(store__client=client_user.client) | Q(order__store__client=client_user.client)
    ).select_related("order", "store", "driver").order_by("-updatedAt")[:200]
    return [_serialize_thread(thread) for thread in threads]


@router.get("/communications/threads/{thread_id}/messages", response=List[dict])
def list_client_thread_messages(request, thread_id: UUID):
    client_user = client_portal_required(request)
    thread = DriverCommunicationThread.objects.filter(
        pk=thread_id,
        operator=client_user.operator,
    ).filter(
        Q(store__client=client_user.client) | Q(order__store__client=client_user.client)
    ).first()
    if not thread:
        from ninja.errors import HttpError
        raise HttpError(404, "Thread não encontrada para este cliente.")

    messages = DriverCommunicationMessage.objects.filter(thread=thread).order_by("createdAt")
    return [
        {
            "message_id": str(message.id),
            "sender_type": message.senderType,
            "sender_name": message.senderName,
            "message": message.message,
            "metadata": message.metadata,
            "created_at": message.createdAt.isoformat() if message.createdAt else None,
        }
        for message in messages
    ]


@router.post("/communications/threads", response={201: dict, 404: dict, 409: dict})
def create_client_thread(request, payload: CommunicationThreadCreatePayload):
    client_user = client_portal_required(request)
    order = _get_client_order(client_user, payload.order_id)
    if not order:
        return 404, {"error": "Ordem não encontrada para este cliente."}
    if not order.driver_id:
        return 409, {"error": "A ordem ainda não possui motorista vinculado."}

    thread = DriverCommunicationThread.objects.create(
        operator=client_user.operator,
        order=order,
        store=order.store,
        driver=order.driver,
        sourceType="STORE",
        status="OPEN",
        subject=payload.subject,
        metadata=payload.metadata,
    )
    first_message = DriverCommunicationMessage.objects.create(
        operator=client_user.operator,
        thread=thread,
        senderType="STORE",
        senderName=client_user.name,
        message=payload.message,
        metadata=payload.metadata,
    )
    return 201, {
        "thread_id": str(thread.id),
        "message_id": str(first_message.id),
        "status": thread.status,
    }


@router.post("/communications/threads/{thread_id}/messages", response={201: dict, 404: dict})
def send_client_thread_message(request, thread_id: UUID, payload: CommunicationMessagePayload):
    client_user = client_portal_required(request)
    thread = DriverCommunicationThread.objects.filter(
        pk=thread_id,
        operator=client_user.operator,
    ).filter(
        Q(store__client=client_user.client) | Q(order__store__client=client_user.client)
    ).first()
    if not thread:
        return 404, {"error": "Thread não encontrada para este cliente."}

    message = DriverCommunicationMessage.objects.create(
        operator=client_user.operator,
        thread=thread,
        senderType="STORE",
        senderName=client_user.name,
        message=payload.message,
        metadata=payload.metadata,
    )
    thread.updatedAt = django_tz.now()
    thread.save(update_fields=["updatedAt"])

    return 201, {
        "thread_id": str(thread.id),
        "message_id": str(message.id),
    }
