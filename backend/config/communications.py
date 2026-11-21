from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from accounts.auth import get_client_portal_user, require_role
from logistics.models import Order, DriverCommunicationThread, DriverCommunicationMessage

router = Router(tags=["Order communications"])


def order_for_actor(request, order_id):
    auth = getattr(request, "auth", None) or {}
    if auth.get("client_id"):
        actor = get_client_portal_user(request)
        if not actor:
            raise HttpError(401, "Conta de loja revogada.")
        query = Order.objects.filter(operator=actor.operator, store__client_id=actor.client_id)
        kind = "STORE"
    else:
        actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
        if not actor.operator_id:
            raise HttpError(422, "Selecione um operador.")
        query = Order.objects.filter(operator=actor.operator)
        kind = "OPERATOR"
    order = get_object_or_404(query, pk=order_id)
    return order, actor, kind


def serialize(message):
    return {
        "id": str(message.id), "text": message.message,
        "sender": "driver" if message.senderType == "DRIVER" else "admin",
        "time": message.createdAt.isoformat(),
        "status": "stored",
    }


@router.get("/orders/{order_id}/messages")
def messages(request, order_id: UUID):
    order, _, kind = order_for_actor(request, order_id)
    query = DriverCommunicationMessage.objects.filter(
        operator=order.operator, thread__order=order, thread__sourceType=kind,
    ).order_by("-createdAt")[:200]
    return [serialize(message) for message in reversed(list(query))]


class MessagePayload(Schema):
    id: UUID
    text: str


@router.post("/orders/{order_id}/messages")
@transaction.atomic
def send_message(request, order_id: UUID, payload: MessagePayload):
    order, actor, kind = order_for_actor(request, order_id)
    if kind == "OPERATOR" and actor.role == "VIEWER":
        raise HttpError(403, "Acesso somente leitura.")
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.driver_id:
        raise HttpError(409, "Aguarde a atribuição de um motoboy antes de enviar.")
    text = payload.text.strip()
    if not text or len(text) > 4000:
        raise HttpError(422, "A mensagem deve possuir de 1 a 4000 caracteres.")
    previous = DriverCommunicationMessage.objects.filter(pk=payload.id).first()
    if previous:
        if (
            previous.thread.order_id != order.id or previous.message != text
            or previous.metadata.get("actor_id") != str(actor.pk)
        ):
            raise HttpError(409, "Identificador de mensagem já utilizado.")
        return serialize(previous)
    thread = DriverCommunicationThread.objects.filter(
        operator=order.operator, order=order, driver=order.driver, status="OPEN", sourceType=kind,
    ).first()
    if not thread:
        thread = DriverCommunicationThread.objects.create(
            operator=order.operator, order=order, store=order.store,
            driver=order.driver, sourceType=kind, status="OPEN",
        )
    message = DriverCommunicationMessage.objects.create(
        id=payload.id, operator=order.operator, thread=thread,
        senderType=kind, senderName=actor.name, message=text,
        metadata={"actor_id": str(actor.pk)},
    )
    thread.save(update_fields=["updatedAt"])
    return serialize(message)
