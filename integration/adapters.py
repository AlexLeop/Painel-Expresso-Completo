import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, Optional


PROVIDER_ALIASES = {
    "IFOOD": "IFOOD",
    "I_FOOD": "IFOOD",
    "99FOOD": "99FOOD",
    "99_FOOD": "99FOOD",
    "DELIVERY_DIRETO": "DELIVERY_DIRETO",
    "DELIVERYDIRETO": "DELIVERY_DIRETO",
    "ANOTA_AI": "ANOTA_AI",
    "ANOTA": "ANOTA_AI",
}

OUTBOUND_STATUS_MAP = {
    "PREPARING": "PREPARING",
    "READY_FOR_DISPATCH": "READY_FOR_DISPATCH",
    "OFFERED": "DISPATCHED",
    "ACCEPTED": "DRIVER_ASSIGNED",
    "STARTED": "PICKED_UP",
    "ARRIVED": "AT_DESTINATION",
    "COMPLETED": "DELIVERED",
    "CANCELED": "CANCELED",
    "CANCELED_IN_TRANSIT": "CANCELED_IN_TRANSIT",
    "RETURNING_TO_STORE": "RETURNING_TO_STORE",
    "RETURNED": "RETURNED",
}

PROVIDER_PROFILES = {
    "IFOOD": {
        "ack_mode": "POLL_AND_ACK",
        "status_field": "code",
        "event_prefix": "order.",
    },
    "99FOOD": {
        "ack_mode": "WEBHOOK_ACK",
        "status_field": "status",
        "event_prefix": "order.",
    },
    "DELIVERY_DIRETO": {
        "ack_mode": "WEBHOOK_ACK",
        "status_field": "status",
        "event_prefix": "order.",
    },
    "ANOTA_AI": {
        "ack_mode": "WEBHOOK_ACK",
        "status_field": "event",
        "event_prefix": "order.",
    },
}

INBOUND_ORDER_STATUS_MAP = {
    "PLACED": "PREPARING",
    "REQUESTED": "PREPARING",
    "CREATED": "PREPARING",
    "NEW": "PREPARING",
    "CONFIRMED": "PREPARING",
    "PROCESSING": "PREPARING",
    "IN_PREPARATION": "PREPARING",
    "PREPARING": "PREPARING",
    "READY_FOR_DISPATCH": "READY_FOR_DISPATCH",
    "READY_TO_PICKUP": "READY_FOR_DISPATCH",
    "READY_TO_SHIP": "READY_FOR_DISPATCH",
    "READY_FOR_DRIVER": "READY_FOR_DISPATCH",
    "DISPATCH_READY": "READY_FOR_DISPATCH",
    "CANCELED": "CANCELED",
    "CANCELLED": "CANCELED",
    "EMI": "PREPARING",
    "APA": "PREPARING",
    "AMP": "PREPARING",
    "SEP": "READY_FOR_DISPATCH",
    "PE0": "READY_FOR_DISPATCH",
    "ENT": "READY_FOR_DISPATCH",
    "ENP": "READY_FOR_DISPATCH",
    "FIN": "COMPLETED",
    "CAN": "CANCELED",
    "PENDING": "PREPARING",
    "IN_PRODUCTION": "PREPARING",
    "READY": "READY_FOR_DISPATCH",
    "OUT_FOR_DELIVERY": "STARTED",
    "DELIVERED": "COMPLETED",
    "CANCELLED_BY_STORE": "CANCELED",
}

ORDER_STATUS_PRECEDENCE = {
    "PREPARING": 10,
    "READY_FOR_DISPATCH": 20,
    "OFFERED": 30,
    "ACCEPTED": 40,
    "STARTED": 50,
    "ARRIVED": 60,
    "RETURNING_TO_STORE": 65,
    "COMPLETED": 70,
    "RETURNED": 75,
    "CANCELED_IN_TRANSIT": 80,
    "CANCELED": 90,
}


def normalize_provider(provider: str) -> str:
    normalized = (provider or "").strip().upper().replace("-", "_").replace(" ", "_")
    return PROVIDER_ALIASES.get(normalized, normalized)


def get_header(headers: Dict[str, Any], key: str) -> Optional[str]:
    target = key.lower()
    for current_key, value in (headers or {}).items():
        if str(current_key).lower() == target:
            return value
    return None


def extract_external_order_id(payload: Dict[str, Any]) -> Optional[str]:
    candidates = [
        payload.get("id"),
        payload.get("_id"),
        payload.get("orderId"),
        payload.get("ordersId"),
        payload.get("codigoPedido"),
        payload.get("codigo"),
        payload.get("externalCode"),
    ]
    order = payload.get("order") or {}
    candidates.extend(
        [
            order.get("id"),
            order.get("_id"),
            order.get("orderId"),
            order.get("ordersId"),
            order.get("codigo"),
            order.get("externalCode"),
        ]
    )
    for candidate in candidates:
        if candidate not in (None, ""):
            return str(candidate)
    return None


def extract_merchant_reference(
    source: str, headers: Dict[str, Any], payload: Dict[str, Any]
) -> Optional[str]:
    provider = normalize_provider(source)
    order = payload.get("order") or {}
    header_candidates = [
        get_header(headers, "x-deliverydireto-id"),
        get_header(headers, "x-merchant-id"),
        get_header(headers, "merchantid"),
    ]
    payload_candidates = [
        payload.get("merchantId"),
        payload.get("merchant_id"),
        payload.get("store_id"),
        payload.get("storeId"),
        payload.get("storesId"),
        payload.get("idLoja"),
        payload.get("codigoLoja"),
        payload.get("pageId"),
        payload.get("idpage"),
        payload.get("idPage"),
        order.get("merchantId"),
        order.get("store_id"),
        order.get("storeId"),
        order.get("storesId"),
        order.get("idLoja"),
        order.get("codigoLoja"),
        order.get("pageId"),
        order.get("idpage"),
        order.get("idPage"),
    ]

    if provider == "99FOOD":
        payload_candidates.extend(
            [
                payload.get("appShopId"),
                order.get("appShopId"),
            ]
        )

    for candidate in header_candidates + payload_candidates:
        if candidate not in (None, ""):
            return str(candidate)
    return None


def _extract_bearer_token(headers: Dict[str, Any]) -> Optional[str]:
    authorization = get_header(headers, "authorization")
    if not authorization:
        return None
    parts = str(authorization).split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def verify_inbound_signature(
    provider: str,
    raw_body: bytes,
    headers: Dict[str, Any],
    secret: Optional[str],
    query_params: Optional[Dict[str, Any]] = None,
) -> bool:
    provider_name = normalize_provider(provider)
    if provider_name != "DELIVERY_DIRETO":
        if provider_name != "ANOTA_AI":
            return True
        if not secret:
            return False
        query_token = (query_params or {}).get("token")
        header_token = (
            get_header(headers, "x-integration-token")
            or get_header(headers, "x-anota-token")
            or _extract_bearer_token(headers)
        )
        received_token = query_token or header_token
        if not received_token:
            return False
        return hmac.compare_digest(str(received_token), str(secret))
    if not secret:
        return False

    received_signature = get_header(headers, "x-deliverydireto-signature")
    if not received_signature:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)


def parse_business_date(payload: Dict[str, Any]) -> Optional[datetime]:
    order = payload.get("order") or {}
    value = (
        payload.get("businessDate")
        or payload.get("createdAt")
        or payload.get("dataHora")
        or payload.get("data")
        or order.get("businessDate")
        or order.get("createdAt")
        or order.get("dataHora")
        or order.get("data")
    )
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def provider_profile(provider: str) -> Dict[str, Any]:
    return PROVIDER_PROFILES.get(
        normalize_provider(provider),
        {
            "ack_mode": "WEBHOOK_ACK",
            "status_field": "status",
            "event_prefix": "order.",
        },
    )


def normalize_external_status(raw_status: Optional[str]) -> Optional[str]:
    if raw_status in (None, ""):
        return None
    return str(raw_status).strip().upper().replace("-", "_").replace(" ", "_")


def extract_inbound_status(provider: str, payload: Dict[str, Any]) -> Optional[str]:
    profile = provider_profile(provider)
    order = payload.get("order") or {}
    candidates = [
        payload.get(profile["status_field"]),
        payload.get("status"),
        payload.get("event"),
        payload.get("eventType"),
        payload.get("code"),
        payload.get("fullCode"),
        payload.get("event_type"),
        order.get(profile["status_field"]),
        order.get("status"),
        order.get("event"),
        order.get("eventType"),
        order.get("code"),
        order.get("fullCode"),
    ]
    for candidate in candidates:
        normalized = normalize_external_status(candidate)
        if normalized:
            return normalized
    return None


def map_inbound_order_status(provider: str, payload: Dict[str, Any]) -> Optional[str]:
    external_status = extract_inbound_status(provider, payload)
    if not external_status:
        return None
    return INBOUND_ORDER_STATUS_MAP.get(external_status)


def should_apply_inbound_status(
    current_status: str, desired_status: Optional[str]
) -> bool:
    if not desired_status or desired_status == current_status:
        return False
    current_rank = ORDER_STATUS_PRECEDENCE.get(current_status, 0)
    desired_rank = ORDER_STATUS_PRECEDENCE.get(desired_status, 0)
    return desired_rank >= current_rank


def serialize_delivery_proof(proof) -> Optional[Dict[str, Any]]:
    if not proof:
        return None
    geom = None
    if getattr(proof, "geom", None):
        geom = {
            "lat": proof.geom.y,
            "lng": proof.geom.x,
        }
    confirmation_mode = "PHOTO"
    if proof.confirmationCode:
        confirmation_mode = "CODE"
    elif proof.qrCode:
        confirmation_mode = "QR_CODE"
    elif proof.barcode:
        confirmation_mode = "BARCODE"
    return {
        "stage": proof.stage,
        "type": proof.type,
        "confirmationMode": confirmation_mode,
        "confirmationCode": proof.confirmationCode,
        "qrCode": proof.qrCode,
        "barcode": proof.barcode,
        "fileUrl": proof.fileUrl,
        "capturedAt": proof.capturedAt.isoformat() if proof.capturedAt else None,
        "deviceIdentifier": proof.deviceIdentifier,
        "gpsAccuracyMeters": proof.gpsAccuracyMeters,
        "location": geom,
        "metadata": proof.metadata or {},
    }


def _event_name(provider: str, event_type: str) -> str:
    normalized_provider = normalize_provider(provider)
    prefix = provider_profile(normalized_provider)["event_prefix"]
    normalized_event = str(event_type).strip().lower().replace("_", ".")
    return (
        f"{prefix}{normalized_event}"
        if not normalized_event.startswith(prefix)
        else normalized_event
    )


def build_outbound_event_payload(
    provider: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    order=None,
    integration=None,
    delivery_proof=None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_provider = normalize_provider(provider)
    profile = provider_profile(normalized_provider)
    order_status = payload.get("status") or getattr(order, "status", None)
    outbound_status = OUTBOUND_STATUS_MAP.get(order_status, order_status)
    merchant_id = payload.get("merchant_id") or (
        integration.merchantId if integration else None
    )
    order_id = (
        payload.get("external_order_id") or payload.get("order_id") or payload.get("id")
    )
    if order and getattr(order, "external_order_id", None):
        order_id = order.external_order_id

    event = {
        "id": event_id,
        "provider": normalized_provider,
        "eventType": event_type,
        "eventName": _event_name(normalized_provider, event_type),
        "acknowledgement": {
            "required": profile["ack_mode"] in {"POLL_AND_ACK", "WEBHOOK_ACK"},
            "mode": profile["ack_mode"],
        },
        "orderId": order_id,
        "merchantId": merchant_id,
        "orderStatus": outbound_status,
        "occurredAt": payload.get("occurred_at")
        or (
            getattr(order, "completedAt", None).isoformat()
            if order and getattr(order, "completedAt", None)
            else None
        ),
        "payload": payload,
    }
    if order:
        event["order"] = {
            "localId": str(order.id),
            "externalId": order.external_order_id,
            "status": order.status,
            "businessDate": order.businessDate.isoformat()
            if order.businessDate
            else None,
            "requestedAt": order.requestedAt.isoformat() if order.requestedAt else None,
            "acceptedAt": order.acceptedAt.isoformat() if order.acceptedAt else None,
            "startedAt": order.startedAt.isoformat() if order.startedAt else None,
            "arrivedAt": order.arrivedAt.isoformat() if order.arrivedAt else None,
            "completedAt": order.completedAt.isoformat() if order.completedAt else None,
        }
        if getattr(order, "driver_id", None):
            event["order"]["driverId"] = str(order.driver_id)
        if getattr(order, "store_id", None):
            event["order"]["storeId"] = str(order.store_id)
    proof_payload = serialize_delivery_proof(delivery_proof)
    if proof_payload:
        event["deliveryConfirmation"] = proof_payload
    return event
