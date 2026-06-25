import os
import json
import httpx
import secrets
import time
import redis
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from uuid import UUID
from django.db import transaction
from django.utils import timezone as django_tz
from ninja import Router, File, Form
from ninja.files import UploadedFile

from config.redis_client import get_redis
from config.idempotency import idempotent
from config.core_models import tenant_context
from .models import (
    Order, Manifest, Stop, ScheduleEntry, Driver, Store, Turno,
    DriverDocument, DriverDocumentRequirement, DriverShiftSession,
    DriverStatusAudit, DriverIncident, DriverIncidentAttachment, Proof,
    DriverShiftReservation, DriverDevice, DriverDeviceSecurityEvent, DriverOfflineSyncBatch,
    DriverCommunicationThread, DriverCommunicationMessage, ComplianceDocument,
    OrderAssignmentAudit,
    DriverConsentAcceptance, PrivacyDataRequest
)
from .compliance import (
    SUPPORTED_PRIVACY_REQUEST_TYPES,
    normalize_privacy_request_type,
)
from .schemas import (
    OrderSchema, ManifestSchema,
    StopBatchCompleteItem, ShiftCheckInSchema, TelemetryPayload,
    DriverStatusPayload, DriverStatusResponse,
    OrderRejectPayload, OrderOfferDetailResponse, DriverCockpitResponse,
    OrderReleasePayload,
    DriverShiftCheckoutPayload, DriverIncidentCreatePayload,
    DriverPerformanceResponse, DriverCalendarItem, DriverShiftReservationPayload,
    DriverDeviceRegisterPayload, DriverDeviceAttestationPayload,
    DriverOfflineSyncPayload, DriverExpensePayload,
    CommunicationMessagePayload, DriverConsentItem, DriverConsentRevokePayload,
    PrivacyDataRequestCreatePayload, PrivacyDataRequestItem
)
from finance.services import SettlementEngine
router = Router(tags=["Logistics"])

r = get_redis()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

SUPPORTED_DRIVER_STATUSES = {
    "ONLINE": {"online": True},
    "OFFLINE": {"online": False},
    "PAUSED": {"online": True},
    "EN_ROUTE": {"online": True},
    "IN_SERVICE": {"online": True},
    "RESTING": {"online": True},
}

ACTIVE_DRIVER_ORDER_STATUSES = [
    Order.OrderStatus.ACCEPTED,
    Order.OrderStatus.STARTED,
    Order.OrderStatus.ARRIVED,
    Order.OrderStatus.CANCELED_IN_TRANSIT,
    Order.OrderStatus.RETURNING_TO_STORE,
]

MAX_ACTIVE_DRIVER_DEVICES = 3
SUPPORTED_DEVICE_PLATFORMS = {"ANDROID", "IOS"}
SUPPORTED_DEVICE_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
EXPENSE_TYPE_ALIASES = {
    "FUEL": "FUEL",
    "COMBUSTIVEL": "FUEL",
    "TOLL": "TOLL",
    "PEDAGIO": "TOLL",
    "PARKING": "PARKING",
    "ESTACIONAMENTO": "PARKING",
    "OTHER": "OTHER",
    "OUTRO": "OTHER",
}

def broadcast_disappearing_card(operator_id, order_id):
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return
        
    broadcast_endpoint = f"{SUPABASE_URL}/realtime/v1/api/broadcast"
    payload = {
        "messages": [{
            "topic": f"realtime:operator_{operator_id}",
            "event": "ORDER_TAKEN",
            "payload": {"order_id": str(order_id)}
        }]
    }
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        import httpx
        httpx.post(broadcast_endpoint, json=payload, headers=headers, timeout=2.0)
    except Exception as e:
        import logging
        logging.error(f"Supabase broadcast failed for Operator {operator_id}: {e}")


def _get_authenticated_driver(request) -> Driver:
    driver_uid = request.auth.get('sub')
    from ninja.errors import HttpError

    try:
        return Driver.objects.get(supabase_uid=driver_uid)
    except Driver.DoesNotExist:
        raise HttpError(404, "Driver não encontrado")


def _serialize_point(point) -> Optional[Dict[str, float]]:
    if not point:
        return None
    try:
        return {"lat": point.y, "lng": point.x}
    except Exception:
        return None


def _offer_rejection_key(driver_id, order_id) -> str:
    return f"driver_offer_rejection:{driver_id}:{order_id}"


def _order_claim_key(order_id) -> str:
    return f"order_claim:{order_id}"


def _mock_storage_url(namespace: str, entity_id: UUID, filename: str) -> str:
    return f"https://mocked-bucket.s3.amazonaws.com/{namespace}/{entity_id}/{filename}"


def _point_from_lat_lng(lat: Optional[float], lng: Optional[float]):
    if lat is None or lng is None:
        return None
    try:
        from django.contrib.gis.geos import Point
        return Point(lng, lat, srid=4326)
    except Exception:
        return None


def _build_order_offer_detail(order: Order) -> Dict:
    stops = list(Stop.objects.filter(order=order).order_by('sequence'))
    last_stop = stops[-1] if stops else None

    return {
        "id": order.id,
        "status": order.status,
        "fareValueCents": order.fareValueCents,
        "distanceMeters": order.distanceMeters,
        "businessDate": order.businessDate,
        "origin": {
            "store_id": order.store_id,
            "store_name": order.store.name,
            "average_prep_minutes": order.store.averagePrepTimeMinutes,
            "location": _serialize_point(order.store.geom),
        },
        "destination": {
            "stops_count": len(stops),
            "last_stop_id": last_stop.id if last_stop else None,
            "last_stop_location": _serialize_point(last_stop.geom) if last_stop else None,
        },
        "current_driver_id": order.driver_id,
        "stops": [
            {
                "id": stop.id,
                "sequence": stop.sequence,
                "type": stop.type,
                "requiresPin": stop.requiresPin,
                "completedAt": stop.completedAt,
                "location": _serialize_point(stop.geom),
            }
            for stop in stops
        ],
    }


def _get_driver_stop(driver: Driver, stop_id: UUID) -> Optional[Stop]:
    return Stop.objects.filter(
        pk=stop_id,
        operator=driver.operator,
        order__driver=driver,
    ).select_related('order').first()


def _period_bounds(period: str):
    today = django_tz.localdate()
    normalized = (period or "today").lower()
    if normalized == "month":
        start = today.replace(day=1)
    elif normalized == "week":
        start = today - timedelta(days=today.weekday())
    else:
        normalized = "today"
        start = today
    return normalized, start, today


def _purge_driver_fastlane_tokens(driver_id: UUID):
    try:
        tokens_key = f"fastlane:driver_tokens:{driver_id}"
        active_tokens = r.zrangebyscore(tokens_key, '-inf', '+inf')
        if active_tokens:
            pipe = r.pipeline()
            for token in active_tokens:
                pipe.delete(f"fastlane:token_meta:{token}")
            pipe.delete(tokens_key)
            pipe.execute()
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        pass


def _normalize_device_platform(platform: str) -> str:
    return (platform or "").strip().upper()


def _normalize_risk_level(risk_level: str) -> str:
    return (risk_level or "").strip().upper()


def _normalize_expense_type(expense_type: str) -> Optional[str]:
    normalized = (expense_type or "").strip().upper()
    return EXPENSE_TYPE_ALIASES.get(normalized)


def _get_driver_device(driver: Driver, device_identifier: str) -> Optional[DriverDevice]:
    return DriverDevice.objects.filter(
        operator=driver.operator,
        driver=driver,
        deviceIdentifier=device_identifier,
    ).first()


def _get_driver_order(driver: Driver, order_id: UUID) -> Optional[Order]:
    return Order.objects.filter(
        pk=order_id,
        operator=driver.operator,
        driver=driver,
    ).first()


def _get_active_driver_orders(driver: Driver, exclude_order_id: Optional[UUID] = None):
    orders = Order.objects.filter(
        operator=driver.operator,
        driver=driver,
        status__in=ACTIVE_DRIVER_ORDER_STATUSES,
    ).select_related('store').order_by('-acceptedAt', '-requestedAt')
    if exclude_order_id:
        orders = orders.exclude(pk=exclude_order_id)
    return orders


def _driver_active_orders_limit(driver: Driver) -> int:
    limit = getattr(driver, "maxActiveOrders", 0) or 0
    return max(limit, 1)


def _serialize_active_order(order: Order) -> Dict:
    next_stop = Stop.objects.filter(
        order=order,
        completedAt__isnull=True,
    ).order_by('sequence').first()

    return {
        "order_id": str(order.id),
        "status": order.status,
        "fare_cents": order.fareValueCents,
        "store_name": order.store.name,
        "manifest_id": str(order.manifest_id) if order.manifest_id else None,
        "next_stop_id": str(next_stop.id) if next_stop else None,
        "next_stop_type": next_stop.type if next_stop else None,
        "next_stop_sequence": next_stop.sequence if next_stop else None,
    }


def _point_coordinates(value) -> Optional[tuple[float, float]]:
    x = getattr(value, "x", None)
    y = getattr(value, "y", None)
    if x is None or y is None:
        return None
    return float(x), float(y)


def _driver_reached_capacity(driver: Driver, exclude_order_id: Optional[UUID] = None) -> bool:
    return _get_active_driver_orders(driver, exclude_order_id=exclude_order_id).count() >= _driver_active_orders_limit(driver)


def _order_belongs_to_grouped_manifest(order: Order) -> bool:
    if not order.manifest_id:
        return False
    return Order.objects.filter(
        operator=order.operator,
        manifest_id=order.manifest_id,
    ).exclude(pk=order.id).exists()


def clear_order_runtime_state(order: Order, previous_driver_id: Optional[UUID]) -> None:
    if not previous_driver_id:
        return
    try:
        pipe = r.pipeline()
        pipe.srem(f"active_orders:driver:{previous_driver_id}", str(order.id))
        pipe.delete(f"public_tracker:{order.id}:active")
        pipe.delete(_order_claim_key(order.id))
        for stop_id in Stop.objects.filter(order=order).values_list("id", flat=True):
            pipe.srem(f"active_stops:driver:{previous_driver_id}", str(stop_id))
        pipe.execute()
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        pass


def _release_order_claim(order_id: UUID) -> None:
    try:
        r.delete(_order_claim_key(order_id))
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        pass


def _request_ip(request) -> Optional[str]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _serialize_driver_consent(document: ComplianceDocument, acceptance: Optional[DriverConsentAcceptance]) -> Dict:
    is_active_acceptance = acceptance is not None and acceptance.revokedAt is None
    return {
        "consent_id": document.id,
        "audience_type": document.audienceType,
        "code": document.code,
        "title": document.title,
        "version": document.version,
        "body": document.body,
        "required": document.required,
        "accepted": is_active_acceptance,
        "effective_at": document.effectiveAt,
        "accepted_at": acceptance.acceptedAt if acceptance else None,
        "revoked_at": acceptance.revokedAt if acceptance else None,
        "revoked_reason": acceptance.revokedReason if acceptance else None,
        "metadata": document.metadata or {},
    }


def _serialize_privacy_request(data_request: PrivacyDataRequest) -> Dict:
    return {
        "request_id": data_request.id,
        "subject_type": data_request.subjectType,
        "request_type": data_request.requestType,
        "status": data_request.status,
        "description": data_request.description,
        "resolution": data_request.resolution,
        "resolved_at": data_request.resolvedAt,
        "metadata": data_request.metadata or {},
        "created_at": data_request.createdAt,
        "updated_at": data_request.updatedAt,
    }



@router.get("/orders", response=List[OrderSchema])
def list_orders(request):
    driver = _get_authenticated_driver(request)

    from django.db.models import Q
    orders = list(Order.objects.filter(
        operator=driver.operator
    ).filter(
        Q(status=Order.OrderStatus.OFFERED, driver_id__isnull=True) |
        Q(status=Order.OrderStatus.OFFERED, driver=driver) |
        Q(driver=driver, status__in=ACTIVE_DRIVER_ORDER_STATUSES)
    ).select_related('store', 'driver'))

    try:
        rejected_offer_ids = {
            str(order.id)
            for order in orders
            if order.status == Order.OrderStatus.OFFERED and r.get(_offer_rejection_key(driver.id, order.id))
        }
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        rejected_offer_ids = set()

    return [
        order for order in orders
        if not (order.status == Order.OrderStatus.OFFERED and str(order.id) in rejected_offer_ids)
    ]


@router.get("/orders/{order_id}", response={200: OrderOfferDetailResponse, 403: dict, 404: dict})
def get_order_detail(request, order_id: UUID):
    driver = _get_authenticated_driver(request)

    order = Order.objects.filter(
        pk=order_id,
        operator=driver.operator,
    ).select_related('store', 'driver').first()

    if not order:
        return 404, {"error": "Ordem não encontrada."}

    is_visible_offer = order.status == Order.OrderStatus.OFFERED and (
        order.driver_id is None or order.driver_id == driver.id
    )
    is_owned_order = order.driver_id == driver.id

    if not (is_visible_offer or is_owned_order):
        return 403, {"error": "Ordem não está visível para este motorista."}

    return 200, _build_order_offer_detail(order)


@router.get("/cockpit", response=DriverCockpitResponse)
def get_cockpit(request):
    driver = _get_authenticated_driver(request)
    today = django_tz.localdate()

    from django.db.models import Sum
    from finance.models import Wallet, WalletTransaction
    from logistics.models import DriverDocumentRequirement, DriverDocument

    wallet, _ = Wallet.objects.get_or_create(driver=driver, operator=driver.operator)
    earnings_today = WalletTransaction.objects.filter(
        destination_driver_wallet=wallet,
        createdAt__date=today,
    ).aggregate(total=Sum('amountCents'))["total"] or 0

    deliveries_today = Order.objects.filter(
        driver=driver,
        businessDate=today,
        status=Order.OrderStatus.COMPLETED,
    ).count()

    active_orders = list(_get_active_driver_orders(driver))
    active_order_payload = _serialize_active_order(active_orders[0]) if active_orders else None
    active_orders_payload = [_serialize_active_order(order) for order in active_orders]

    shift_payload = None
    open_session = DriverShiftSession.objects.filter(
        driver=driver,
        status='OPEN',
    ).select_related('scheduleEntry__store', 'scheduleEntry__turno').order_by('-checkInAt').first()

    schedule = ScheduleEntry.objects.filter(
        driver=driver,
        date=today,
    ).select_related('store', 'turno').order_by('createdAt').first()

    if schedule:
        start_minutes = schedule.turno.startTime.hour * 60 + schedule.turno.startTime.minute
        end_minutes = schedule.turno.endTime.hour * 60 + schedule.turno.endTime.minute
        planned_minutes = end_minutes - start_minutes
        if planned_minutes < 0:
            planned_minutes += 24 * 60

        shift_payload = {
            "schedule_id": str(schedule.id),
            "store_id": str(schedule.store_id),
            "store_name": schedule.store.name,
            "turno_id": str(schedule.turno_id),
            "turno_name": schedule.turno.name,
            "date": str(schedule.date),
            "planned_minutes": planned_minutes,
            "session_id": str(open_session.id) if open_session else None,
            "checked_in_at": open_session.checkInAt.isoformat() if open_session else None,
        }

    required_types = set(DriverDocumentRequirement.objects.filter(
        tax_class=driver.tax_classification,
        is_required=True,
    ).values_list('document_type', flat=True))
    submitted_types = set(DriverDocument.objects.filter(
        driver=driver,
        status__in=['PENDING_APPROVAL', 'APPROVED'],
    ).values_list('document_type', flat=True))

    return {
        "driver": {
            "id": str(driver.id),
            "name": driver.name,
            "online": driver.online,
            "active": driver.active,
            "status": driver.operational_status,
        },
        "shift": shift_payload,
        "today": {
            "earnings_cents": earnings_today,
            "deliveries": deliveries_today,
        },
        "wallet": {
            "balance_cents": wallet.balanceCents,
        },
        "active_order": active_order_payload,
        "active_orders": active_orders_payload,
        "active_orders_count": len(active_orders_payload),
        "active_orders_limit": _driver_active_orders_limit(driver),
        "pending_documents": len(required_types - submitted_types),
        "unread_messages": 0,
    }


@router.get("/performance", response=DriverPerformanceResponse)
def get_driver_performance(request, period: str = "today"):
    driver = _get_authenticated_driver(request)
    _, start_date, end_date = _period_bounds(period)

    from django.db.models import Sum
    from finance.models import Wallet, WalletTransaction

    wallet, _ = Wallet.objects.get_or_create(driver=driver, operator=driver.operator)
    deliveries = Order.objects.filter(
        driver=driver,
        completedAt__date__gte=start_date,
        completedAt__date__lte=end_date,
        status=Order.OrderStatus.COMPLETED,
    ).count()
    accepted = Order.objects.filter(
        driver=driver,
        acceptedAt__date__gte=start_date,
        acceptedAt__date__lte=end_date,
    ).count()
    incidents_open = DriverIncident.objects.filter(
        driver=driver,
        status='OPEN',
    ).count()
    earnings_cents = WalletTransaction.objects.filter(
        destination_driver_wallet=wallet,
        createdAt__date__gte=start_date,
        createdAt__date__lte=end_date,
    ).aggregate(total=Sum('amountCents'))["total"] or 0

    rejected = 0
    try:
        from integration.models import IntegrationOutbox
        rejected = IntegrationOutbox.objects.filter(
            operator_id=driver.operator_id,
            eventType='ORDER_REJECTED_BY_DRIVER',
            payload__driver_id=str(driver.id),
            createdAt__date__gte=start_date,
            createdAt__date__lte=end_date,
        ).count()
    except Exception:
        rejected = 0

    acceptance_denominator = accepted + rejected
    acceptance_rate = round((accepted / acceptance_denominator) * 100, 2) if acceptance_denominator else 0.0
    completion_rate = round((deliveries / accepted) * 100, 2) if accepted else 0.0

    return {
        "deliveries": deliveries,
        "earnings_cents": earnings_cents,
        "incidents_open": incidents_open,
        "acceptance_rate": acceptance_rate,
        "completion_rate": completion_rate,
    }


@router.get("/shifts/calendar", response=List[DriverCalendarItem])
def get_driver_calendar(request, start_date: Optional[date] = None, end_date: Optional[date] = None):
    driver = _get_authenticated_driver(request)
    start = start_date or django_tz.localdate()
    end = end_date or (start + timedelta(days=14))

    schedules = ScheduleEntry.objects.filter(
        driver=driver,
        date__gte=start,
        date__lte=end,
    ).select_related('store', 'turno').order_by('date', 'turno__startTime')

    reservations = DriverShiftReservation.objects.filter(
        driver=driver,
        date__gte=start,
        date__lte=end,
    ).select_related('store', 'turno').order_by('date', 'turno__startTime')

    items = [
        {
            "kind": "SCHEDULE",
            "date": str(schedule.date),
            "status": "CONFIRMED",
            "store_id": str(schedule.store_id),
            "store_name": schedule.store.name,
            "turno_id": str(schedule.turno_id),
            "turno_name": schedule.turno.name,
        }
        for schedule in schedules
    ]
    items.extend([
        {
            "kind": "RESERVATION",
            "date": str(reservation.date),
            "status": reservation.status,
            "store_id": str(reservation.store_id),
            "store_name": reservation.store.name,
            "turno_id": str(reservation.turno_id),
            "turno_name": reservation.turno.name,
        }
        for reservation in reservations
    ])
    items.sort(key=lambda item: (item["date"], item["turno_name"], item["kind"]))
    return items


@router.post("/shifts/reservations", response={201: dict, 400: dict, 409: dict})
def create_shift_reservation(request, payload: DriverShiftReservationPayload):
    driver = _get_authenticated_driver(request)

    store = Store.objects.filter(pk=payload.store_id, operator=driver.operator).first()
    turno = Turno.objects.filter(pk=payload.turno_id, operator=driver.operator).first()
    if not store or not turno:
        return 400, {"error": "Store ou turno inválido para este operador."}

    if ScheduleEntry.objects.filter(driver=driver, turno=turno, date=payload.date).exists():
        return 409, {"error": "Já existe escala confirmada para esta data e turno."}

    reservation, created = DriverShiftReservation.objects.get_or_create(
        operator=driver.operator,
        driver=driver,
        store=store,
        turno=turno,
        date=payload.date,
        defaults={
            "status": "REQUESTED",
            "note": payload.note,
        }
    )
    if not created and reservation.status != 'CANCELED':
        return 409, {"error": "Já existe reserva ativa para esta data e turno."}

    if not created:
        reservation.status = 'REQUESTED'
        reservation.note = payload.note
        reservation.decidedAt = None
        reservation.save(update_fields=['status', 'note', 'decidedAt'])

    return 201, {
        "reservation_id": str(reservation.id),
        "status": reservation.status,
    }


@router.post("/status", response={200: DriverStatusResponse, 422: dict})
def update_driver_status(request, payload: DriverStatusPayload):
    driver = _get_authenticated_driver(request)
    desired_status = payload.status.strip().upper()

    if desired_status not in SUPPORTED_DRIVER_STATUSES:
        return 422, {
            "error": "Status ainda não suportado pelo schema atual.",
            "supported_statuses": list(SUPPORTED_DRIVER_STATUSES.keys()),
        }

    now = django_tz.now()
    previous_status = getattr(driver, 'operational_status', 'OFFLINE')
    driver.online = SUPPORTED_DRIVER_STATUSES[desired_status]["online"]
    driver.operational_status = desired_status
    driver.lastPingAt = now
    driver.save(update_fields=['online', 'operational_status', 'lastPingAt'])

    DriverStatusAudit.objects.create(
        operator=driver.operator,
        driver=driver,
        previous_status=previous_status,
        new_status=desired_status,
        reason=payload.reason,
    )

    try:
        from integration.models import IntegrationOutbox
        IntegrationOutbox.objects.create(
            operator_id=driver.operator_id,
            aggregateType='DRIVER',
            aggregateId=driver.id,
            eventType='DRIVER_STATUS_CHANGED',
            payload={
                'driver_id': str(driver.id),
                'status': desired_status,
                'previous_status': previous_status,
                'reason': payload.reason,
                'updated_at': now.isoformat(),
            }
        )
    except Exception:
        pass

    return 200, {
        "driver_id": driver.id,
        "status": desired_status,
        "online": driver.online,
        "reason": payload.reason,
        "updated_at": now,
    }

@router.post("/location", response=dict)
def update_location(request, payload: TelemetryPayload):
    driver = _get_authenticated_driver(request)

    try:
        from django.contrib.gis.geos import Point
        driver.geom = Point(payload.lng, payload.lat, srid=4326)
    except Exception:
        pass # Ignora no Windows nativo sem GDAL
        
    driver.lastPingAt = django_tz.now()
    driver.speedKmh = payload.speedKmh
    driver.heading = payload.heading
    driver.online = True
    driver.save(update_fields=['geom', 'lastPingAt', 'speedKmh', 'heading', 'online'])
    
    return {"status": "ok"}


@router.post("/orders/{order_id}/accept", response=OrderSchema)
@idempotent(timeout=86400, schema=OrderSchema)
def accept_order(request, order_id: UUID):
    driver_uid = request.auth.get('sub')
    
    try:
        driver = Driver.objects.get(supabase_uid=driver_uid)
    except Driver.DoesNotExist:
        from django.http import JsonResponse
        return JsonResponse({"error": "Driver não encontrado."}, status=404)

    if not driver.active:
        from django.http import JsonResponse
        return JsonResponse({"error": "Motorista suspenso na base."}, status=403)

    try:
        if r.get(f"deny_list:driver:{driver.id}"):
            from django.http import JsonResponse
            return JsonResponse({"error": "Motorista bloqueado (Deny-list)."}, status=403)
        if r.get(f"deny_list:operator:{driver.operator_id}"):
            from django.http import JsonResponse
            return JsonResponse({"error": "Operador suspenso financeiramente na base."}, status=403)
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        from django.http import JsonResponse
        return JsonResponse({"error": "Fail-closed de segurança. Sistema indisponível."}, status=503)

    # Resolve a concorrência no Redis em < 50ms (Fail-closed)
    try:
        claim_script = """
        local order_key = KEYS[1]
        local driver_id = ARGV[1]
        
        local current = redis.call('GET', order_key)
        if current == false then
            redis.call('SET', order_key, driver_id, 'EX', 86400)
            return 1
        elseif current == driver_id then
            return 1
        else
            return 0
        end
        """
        claimed = r.eval(claim_script, 1, _order_claim_key(order_id), str(driver.id))
        if not claimed:
            from django.http import JsonResponse
            return JsonResponse({"error": "Ordem já capturada por outro entregador ou inexistente."}, status=409)
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        from django.http import JsonResponse
        return JsonResponse({"error": "Fail-closed de segurança. Sistema indisponível."}, status=503)

    with transaction.atomic():
        driver = Driver.objects.select_for_update().get(pk=driver.pk)
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        
        if not order:
            _release_order_claim(order_id)
            from django.http import JsonResponse
            return JsonResponse({"error": "Ordem inexistente."}, status=404)

        if order.operator_id != driver.operator_id:
            _release_order_claim(order_id)
            from django.http import JsonResponse
            return JsonResponse({"error": "Ordem não pertence ao operador do motorista."}, status=403)
        
        # Se a ordem já estava aceita por este driver (idempotência no DB além do Redis)
        if order.status == Order.OrderStatus.ACCEPTED and order.driver_id == driver.id:
            pass # Já estava salva
        elif order.status == Order.OrderStatus.OFFERED and order.driver_id and order.driver_id != driver.id:
            _release_order_claim(order_id)
            from django.http import JsonResponse
            return JsonResponse({"error": "A ordem está reservada para outro motorista."}, status=403)
        elif order.status != Order.OrderStatus.OFFERED:
            _release_order_claim(order_id)
            from django.http import JsonResponse
            return JsonResponse({"error": "Ordem não está mais disponível para aceite."}, status=400)
        elif _driver_reached_capacity(driver):
            _release_order_claim(order_id)
            from django.http import JsonResponse
            return JsonResponse({
                "error": "Motorista atingiu o limite operacional de ordens ativas.",
                "active_orders_limit": _driver_active_orders_limit(driver),
            }, status=409)
        else:
            order.status = Order.OrderStatus.ACCEPTED
            order.driver = driver
            order.acceptedAt = django_tz.now()
            order.save(update_fields=['status', 'driver', 'acceptedAt'])
            
            # Setup Live Tracker & Geofence in Redis
            try:
                # 1. Tracker Setup
                r.sadd(f"active_orders:driver:{driver.id}", str(order.id))
                r.setex(f"public_tracker:{order.id}:active", 14400, 1) # 4h TTL
                
                # 2. Geofence Setup
                geo_key = f"driver:location:{order.operator_id}"
                for stop in Stop.objects.filter(order=order):
                    point = _point_coordinates(stop.geom)
                    if point:
                        r.geoadd(geo_key, (point[0], point[1], f"stop:{stop.id}:point"))
                    r.sadd(f"active_stops:driver:{driver.id}", str(stop.id))
                    r.setex(f"stop:{stop.id}:radius", 86400, 150.0)
            except Exception as e:
                import logging
                logging.error(f"Redis setup failed for order {order.id}: {e}")
            
            broadcast_disappearing_card(order.operator_id, order.id)

        return order


@router.post("/orders/{order_id}/reject", response={200: dict, 403: dict, 404: dict, 409: dict, 503: dict})
@idempotent(timeout=86400)
def reject_order(request, order_id: UUID, payload: OrderRejectPayload):
    driver = _get_authenticated_driver(request)

    if not driver.active:
        return 403, {"error": "Motorista suspenso na base."}

    order = Order.objects.filter(
        pk=order_id,
        operator=driver.operator,
    ).select_related('store').first()

    if not order:
        return 404, {"error": "Ordem inexistente."}

    if order.status != Order.OrderStatus.OFFERED:
        return 409, {"error": "A ordem não está disponível para recusa."}

    if order.driver_id and order.driver_id != driver.id:
        return 403, {"error": "A ordem está reservada para outro motorista."}

    rejection_payload = {
        "driver_id": str(driver.id),
        "order_id": str(order.id),
        "reason_code": payload.reason_code,
        "reason_text": payload.reason_text,
        "rejected_at": django_tz.now().isoformat(),
    }

    try:
        r.setex(
            _offer_rejection_key(driver.id, order.id),
            86400,
            json.dumps(rejection_payload),
        )
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return 503, {"error": "Sistema de recusa temporariamente indisponível."}

    try:
        from integration.models import IntegrationOutbox
        IntegrationOutbox.objects.create(
            operator_id=driver.operator_id,
            aggregateType='ORDER',
            aggregateId=order.id,
            eventType='ORDER_REJECTED_BY_DRIVER',
            payload=rejection_payload,
        )
    except Exception:
        pass

    return 200, {
        "status": "rejected",
        "order_id": str(order.id),
        "reason_code": payload.reason_code,
    }


@router.post("/orders/{order_id}/release", response={200: OrderSchema, 403: dict, 404: dict, 409: dict})
@idempotent(timeout=86400, schema=OrderSchema)
def release_order(request, order_id: UUID, payload: OrderReleasePayload):
    driver = _get_authenticated_driver(request)

    with transaction.atomic():
        driver = Driver.objects.select_for_update().get(pk=driver.pk)
        order = Order.objects.select_for_update().filter(
            pk=order_id,
            operator=driver.operator,
        ).select_related("store").first()

        if not order:
            return 404, {"error": "Ordem inexistente."}

        if order.driver_id != driver.id:
            return 403, {"error": "A ordem não pertence a este motorista."}

        if order.status != Order.OrderStatus.ACCEPTED:
            return 409, {"error": "A ordem não está em estado seguro para devolução."}

        if _order_belongs_to_grouped_manifest(order):
            return 409, {"error": "A ordem pertence a um manifesto agrupado e precisa ser redistribuída pela operação."}

        previous_driver = order.driver
        order.driver = None
        order.status = Order.OrderStatus.OFFERED
        order.acceptedAt = None
        order.save(update_fields=["driver", "status", "acceptedAt"])

        OrderAssignmentAudit.objects.create(
            operator=driver.operator,
            order=order,
            previousDriver=previous_driver,
            newDriver=None,
            changedByDriver=driver,
            reason=payload.reason,
        )

        from integration.models import IntegrationOutbox
        IntegrationOutbox.objects.create(
            operator_id=driver.operator_id,
            aggregateType="ORDER",
            aggregateId=order.id,
            eventType="ORDER_RELEASED_BY_DRIVER",
            payload={
                "order_id": str(order.id),
                "previous_driver_id": str(driver.id),
                "reason": payload.reason,
                "occurred_at": django_tz.now().isoformat(),
            },
        )

    clear_order_runtime_state(order, driver.id)
    broadcast_disappearing_card(order.operator_id, order.id)
    return order


@router.post("/orders/{order_id}/start", response=OrderSchema)
@idempotent(timeout=86400, schema=OrderSchema)
def start_order(request, order_id: UUID):
    driver_uid = request.auth.get('sub')
    
    try:
        driver = Driver.objects.get(supabase_uid=driver_uid)
    except Driver.DoesNotExist:
        from django.http import JsonResponse
        return JsonResponse({"error": "Driver não encontrado."}, status=404)

    with tenant_context(driver.operator_id):
        order = Order.objects.filter(pk=order_id).first()
        if not order:
            from django.http import JsonResponse
            return JsonResponse({"error": "Ordem inexistente."}, status=404)

        if order.driver_id != driver.id:
            from django.http import JsonResponse
            return JsonResponse({"error": "Ordem não pertence a este motorista."}, status=403)

        if order.status == Order.OrderStatus.STARTED:
            pass # Idempotent
        elif order.status != Order.OrderStatus.ACCEPTED:
            from django.http import JsonResponse
            return JsonResponse({"error": f"Ordem não pode ser iniciada a partir do status {order.status}."}, status=400)
        else:
            order.status = Order.OrderStatus.STARTED
            order.startedAt = django_tz.now()
            order.save(update_fields=['status', 'startedAt'])
            
            # Dispara webhook via Outbox
            from integration.models import IntegrationOutbox
            IntegrationOutbox.objects.create(
                operator_id=order.operator_id,
                aggregateType='ORDER',
                aggregateId=order.id,
                eventType='ORDER_STARTED',
                payload={'id': str(order.id), 'status': 'STARTED'}
            )
            
        return order



@router.post("/stops/complete-batch", response=Dict)
@idempotent(timeout=86400)
def complete_stops_batch(request, items: List[StopBatchCompleteItem]):
    driver_uid = request.auth.get('sub')
    try:
        driver = Driver.objects.get(supabase_uid=driver_uid)
    except Driver.DoesNotExist:
        from django.http import JsonResponse
        return JsonResponse({"error": "Driver não encontrado."}, status=404)

    if not driver.active:
        from django.http import JsonResponse
        return JsonResponse({"error": "Motorista suspenso na base."}, status=403)

    try:
        if r.get(f"deny_list:driver:{driver.id}"):
            from django.http import JsonResponse
            return JsonResponse({"error": "Motorista bloqueado (Deny-list)."}, status=403)
        if r.get(f"deny_list:operator:{driver.operator_id}"):
            from django.http import JsonResponse
            return JsonResponse({"error": "Operador suspenso financeiramente na base."}, status=403)
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        from django.http import JsonResponse
        return JsonResponse({"error": "Fail-closed de segurança. Sistema indisponível."}, status=503)

    # Execução Atômica Unificada: Validação + Completar dentro do mesmo atomic
    # Impede TOCTOU (Time-of-Check vs Time-of-Use) entre validação de PIN e execução
    completed_ids = []
    orders_to_check = set()
    
    with transaction.atomic():
        for item in items:
            # select_for_update ANTES de validar PIN — trava a row impedindo mudanças
            stop = Stop.objects.select_for_update().filter(
                pk=item.stop_id, order__driver=driver
            ).select_related('order').first()
            
            if not stop or stop.completedAt:
                continue
            
            # Validação de PIN DENTRO do lock (impede TOCTOU)
            if stop.requiresPin:
                if not item.delivery_pin:
                    from django.http import JsonResponse
                    return JsonResponse({
                        "error": "INVALID_POD_PIN",
                        "message": f"PIN obrigatório para a parada {stop.id}."
                    }, status=400)
                
                from django.contrib.auth.hashers import check_password
                hash_in_db = stop.deliveryPinHash or ""
                is_valid = check_password(item.delivery_pin, hash_in_db)
                if not is_valid:
                    from django.http import JsonResponse
                    return JsonResponse({
                        "error": "INVALID_POD_PIN",
                        "message": f"PIN incorreto para a parada {stop.id}."
                    }, status=400)
            
            stop.completedAt = item.timestamp
            stop.save()
            completed_ids.append(stop.id)
            orders_to_check.add(stop.order_id)
            
        for order_id in orders_to_check:
            order = Order.objects.select_for_update().filter(pk=order_id).first()
            if order and order.status != Order.OrderStatus.COMPLETED:
                pending_stops = Stop.objects.filter(order=order, completedAt__isnull=True).count()
                if pending_stops == 0:
                    order.status = Order.OrderStatus.COMPLETED
                    order.completedAt = django_tz.now()
                    order.save()
                    
                    try:
                        SettlementEngine.settle_order(order)
                    except Exception as e:
                        import logging
                        logging.error(f"Failed to settle order {order.id}: {e}")
                        
                    # Cleanup Redis and trigger webhook
                    try:
                        r.srem(f"active_orders:driver:{driver.id}", str(order.id))
                        r.delete(f"public_tracker:{order.id}:active")
                        
                        from integration.models import IntegrationOutbox
                        IntegrationOutbox.objects.create(
                            operator_id=order.operator_id,
                            aggregateType='ORDER',
                            aggregateId=order.id,
                            eventType='ORDER_COMPLETED',
                            payload={'id': str(order.id), 'status': 'COMPLETED'}
                        )
                    except Exception as e:
                        import logging
                        logging.error(f"Redis cleanup failed for order {order.id}: {e}")

    return {"completed_stops": completed_ids}


@router.post("/shifts/check-in", response={201: dict, 400: dict, 403: dict})
def check_in_shift(request, payload: ShiftCheckInSchema):
    try:
        driver = _get_authenticated_driver(request)
        store = Store.objects.get(pk=payload.store_id)
        turno = Turno.objects.get(pk=payload.turno_id)
    except Exception:
        return 400, {"error": "Referência inválida."}

    if not driver.active:
        return 403, {"error": "Motorista suspenso na base."}

    try:
        if r.get(f"deny_list:driver:{driver.id}"):
            return 403, {"error": "Motorista bloqueado (Deny-list)."}
        if r.get(f"deny_list:operator:{driver.operator_id}"):
            return 403, {"error": "Operador suspenso financeiramente na base."}
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return 503, {"error": "Fail-closed de segurança. Sistema indisponível."}

    schedule, _ = ScheduleEntry.objects.get_or_create(
        operator=driver.operator,
        driver=driver,
        store=store,
        turno=turno,
        date=payload.date,
        defaults={'minGuaranteedOverrideCents': 0}
    )

    existing_open_session = DriverShiftSession.objects.filter(
        driver=driver,
        status='OPEN',
    ).first()
    if existing_open_session:
        return 400, {"error": "Já existe uma sessão de turno aberta para este motorista."}

    now = django_tz.now()
    session = DriverShiftSession.objects.create(
        operator=driver.operator,
        driver=driver,
        scheduleEntry=schedule,
        status='OPEN',
        checkInAt=now,
    )

    previous_status = getattr(driver, 'operational_status', 'OFFLINE')
    driver.operational_status = 'ONLINE'
    driver.online = True
    driver.lastPingAt = now
    driver.save(update_fields=['operational_status', 'online', 'lastPingAt'])

    DriverStatusAudit.objects.create(
        operator=driver.operator,
        driver=driver,
        previous_status=previous_status,
        new_status='ONLINE',
        reason='CHECK_IN',
    )

    device_token = secrets.token_urlsafe(32)
    ttl_seconds = 14 * 60 * 60
    
    import json
    # A Identidade Inviolável na Fast Lane
    token_meta = {
        "driver_id": str(driver.id),
        "operator_id": str(driver.operator_id)
    }
    r.setex(f"fastlane:token_meta:{device_token}", ttl_seconds, json.dumps(token_meta))
    
    # Índice Secundário para poder invalidar todos os tokens de um motorista banido
    # Usa ZADD com score = timestamp de expiração para evitar reset de TTL
    expiration_ts = time.time() + ttl_seconds
    tokens_key = f"fastlane:driver_tokens:{driver.id}"
    r.zadd(tokens_key, {device_token: expiration_ts})
    # Limpa tokens expirados do índice (score < agora)
    r.zremrangebyscore(tokens_key, 0, time.time())
    r.expire(tokens_key, ttl_seconds)  # TTL de segurança no sorted set inteiro

    return 201, {
        "message": "Check-in realizado com sucesso.",
        "device_token": device_token,
        "schedule_id": str(schedule.id),
        "session_id": str(session.id)
    }

@router.post("/shifts/check-out", response={200: dict, 400: dict, 404: dict})
def check_out_shift(request, payload: DriverShiftCheckoutPayload):
    driver = _get_authenticated_driver(request)
    session = DriverShiftSession.objects.filter(
        driver=driver,
        status='OPEN',
    ).select_related('scheduleEntry').order_by('-checkInAt').first()

    if not session:
        return 404, {"error": "Nenhuma sessão de turno aberta encontrada."}

    now = django_tz.now()
    session.status = 'CLOSED'
    session.checkOutAt = now
    session.reason = payload.reason
    session.save(update_fields=['status', 'checkOutAt', 'reason'])

    previous_status = getattr(driver, 'operational_status', 'OFFLINE')
    driver.operational_status = 'OFFLINE'
    driver.online = False
    driver.lastPingAt = now
    driver.save(update_fields=['operational_status', 'online', 'lastPingAt'])

    DriverStatusAudit.objects.create(
        operator=driver.operator,
        driver=driver,
        previous_status=previous_status,
        new_status='OFFLINE',
        reason=payload.reason or 'CHECK_OUT',
    )

    worked_minutes = int((now - session.checkInAt).total_seconds() // 60)
    return 200, {
        "message": "Check-out realizado com sucesso.",
        "session_id": str(session.id),
        "worked_minutes": worked_minutes,
    }


@router.post("/documents/upload", response={200: dict, 403: dict, 404: dict})
def upload_document(
    request, 
    document_type: Form[str],
    file: File[UploadedFile],
    expiresAt: Form[str | None] = None
):
    """
    [Flow 4.2 & 4.3] Upload de Documentos e Onboarding do Motorista.
    Integração com Supabase Storage.
    """
    driver = _get_authenticated_driver(request)
        
    if not driver.active:
        return 403, {"error": "Motorista suspenso na base."}
        
    # State transition: INVITED -> PENDING_DOCUMENTS no primeiro login/upload
    if driver.onboarding_status == 'INVITED':
        driver.onboarding_status = 'PENDING_DOCUMENTS'
        driver.save(update_fields=['onboarding_status'])
        
    # Aqui iria o script Boto3 / Supabase Python para o Bucket `driver-docs`
    file_url = _mock_storage_url("driver-docs", driver.id, file.name)
    
    expires_date = date.fromisoformat(expiresAt) if expiresAt else None
    
    DriverDocument.objects.create(
        operator=driver.operator,
        driver=driver,
        name=file.name,
        fileUrl=file_url,
        expiresAt=expires_date,
        document_type=document_type,
        status='PENDING_APPROVAL'
    )
    
    # [Flow 4.3] Verificar se todos os documentos obrigatórios foram enviados
    required_types = DriverDocumentRequirement.objects.filter(
        tax_class=driver.tax_classification,
        is_required=True
    ).values_list('document_type', flat=True)
    
    submitted_types = DriverDocument.objects.filter(
        driver=driver,
        status__in=['PENDING_APPROVAL', 'APPROVED']
    ).values_list('document_type', flat=True)
    
    missing = set(required_types) - set(submitted_types)
    
    if not missing:
        # Tudo enviado, transiciona para UNDER_REVIEW
        driver.onboarding_status = 'UNDER_REVIEW'
        driver.save(update_fields=['onboarding_status'])
    
    return 200, {
        "message": "Upload efetuado com sucesso.",
        "filename": file.name,
        "onboarding_status": driver.onboarding_status,
        "missing_documents": list(missing)
    }


@router.post("/stops/{stop_id}/pickup-proof", response={201: dict, 400: dict, 404: dict})
def upload_pickup_proof(
    request,
    stop_id: UUID,
    proof_type: Form[str],
    file: File[UploadedFile],
    lat: Form[float | None] = None,
    lng: Form[float | None] = None,
    gps_accuracy_meters: Form[int | None] = None,
    captured_at: Form[str | None] = None,
    pin_code: Form[str | None] = None,
    qr_code: Form[str | None] = None,
    barcode: Form[str | None] = None,
    confirmation_code: Form[str | None] = None,
):
    driver = _get_authenticated_driver(request)
    stop = _get_driver_stop(driver, stop_id)

    if not stop:
        return 404, {"error": "Parada não encontrada para este motorista."}
    if stop.type != Stop.StopType.PICKUP:
        return 400, {"error": "A parada informada não é de coleta."}

    proof = Proof.objects.create(
        operator=driver.operator,
        stop=stop,
        type=proof_type.upper(),
        stage='PICKUP',
        fileUrl=_mock_storage_url("proofs", stop.id, file.name),
        geom=_point_from_lat_lng(lat, lng),
        gpsAccuracyMeters=gps_accuracy_meters,
        deviceIdentifier=request.headers.get("x-device-id"),
        confirmationCode=confirmation_code,
        qrCode=qr_code,
        barcode=barcode,
        metadata={
            "pin_code": pin_code,
            "captured_at_client": captured_at,
            "original_filename": file.name,
        },
    )

    return 201, {
        "proof_id": str(proof.id),
        "stage": proof.stage,
        "file_url": proof.fileUrl,
    }


@router.post("/stops/{stop_id}/delivery-proof", response={201: dict, 400: dict, 404: dict})
def upload_delivery_proof(
    request,
    stop_id: UUID,
    proof_type: Form[str],
    file: File[UploadedFile],
    lat: Form[float | None] = None,
    lng: Form[float | None] = None,
    gps_accuracy_meters: Form[int | None] = None,
    captured_at: Form[str | None] = None,
    pin_code: Form[str | None] = None,
    qr_code: Form[str | None] = None,
    barcode: Form[str | None] = None,
    confirmation_code: Form[str | None] = None,
):
    driver = _get_authenticated_driver(request)
    stop = _get_driver_stop(driver, stop_id)

    if not stop:
        return 404, {"error": "Parada não encontrada para este motorista."}
    if stop.type == Stop.StopType.PICKUP:
        return 400, {"error": "Use o endpoint de coleta para esta parada."}

    proof = Proof.objects.create(
        operator=driver.operator,
        stop=stop,
        type=proof_type.upper(),
        stage='DELIVERY',
        fileUrl=_mock_storage_url("proofs", stop.id, file.name),
        geom=_point_from_lat_lng(lat, lng),
        gpsAccuracyMeters=gps_accuracy_meters,
        deviceIdentifier=request.headers.get("x-device-id"),
        confirmationCode=confirmation_code,
        qrCode=qr_code,
        barcode=barcode,
        metadata={
            "pin_code": pin_code,
            "captured_at_client": captured_at,
            "original_filename": file.name,
        },
    )

    return 201, {
        "proof_id": str(proof.id),
        "stage": proof.stage,
        "file_url": proof.fileUrl,
    }


@router.post("/incidents", response={201: dict, 400: dict, 404: dict})
def create_incident(request, payload: DriverIncidentCreatePayload):
    driver = _get_authenticated_driver(request)
    order = None
    stop = None

    if payload.order_id:
        order = Order.objects.filter(
            pk=payload.order_id,
            operator=driver.operator,
            driver=driver,
        ).first()
        if not order:
            return 404, {"error": "Ordem não encontrada para este motorista."}

    if payload.stop_id:
        stop = _get_driver_stop(driver, payload.stop_id)
        if not stop:
            return 404, {"error": "Parada não encontrada para este motorista."}

    incident = DriverIncident.objects.create(
        operator=driver.operator,
        driver=driver,
        order=order,
        stop=stop,
        type=payload.type.upper(),
        status='OPEN',
        description=payload.description,
        geom=_point_from_lat_lng(payload.lat, payload.lng),
        metadata=payload.metadata,
    )

    try:
        from integration.models import IntegrationOutbox
        IntegrationOutbox.objects.create(
            operator_id=driver.operator_id,
            aggregateType='DRIVER_INCIDENT',
            aggregateId=incident.id,
            eventType='DRIVER_INCIDENT_CREATED',
            payload={
                "driver_id": str(driver.id),
                "incident_id": str(incident.id),
                "type": incident.type,
            },
        )
    except Exception:
        pass

    return 201, {
        "incident_id": str(incident.id),
        "status": incident.status,
        "type": incident.type,
    }


@router.post("/incidents/{incident_id}/attachments", response={201: dict, 404: dict})
def attach_incident_evidence(
    request,
    incident_id: UUID,
    attachment_type: Form[str],
    file: File[UploadedFile],
    lat: Form[float | None] = None,
    lng: Form[float | None] = None,
    captured_at: Form[str | None] = None,
):
    driver = _get_authenticated_driver(request)
    incident = DriverIncident.objects.filter(
        pk=incident_id,
        operator=driver.operator,
        driver=driver,
    ).first()

    if not incident:
        return 404, {"error": "Ocorrência não encontrada para este motorista."}

    attachment = DriverIncidentAttachment.objects.create(
        operator=driver.operator,
        incident=incident,
        type=attachment_type.upper(),
        fileUrl=_mock_storage_url("incident-attachments", incident.id, file.name),
        metadata={
            "lat": lat,
            "lng": lng,
            "captured_at_client": captured_at,
            "original_filename": file.name,
        },
    )

    return 201, {
        "attachment_id": str(attachment.id),
        "file_url": attachment.fileUrl,
    }


@router.post("/devices/register", response={201: dict, 400: dict, 409: dict})
def register_driver_device(request, payload: DriverDeviceRegisterPayload):
    driver = _get_authenticated_driver(request)
    platform = _normalize_device_platform(payload.platform)

    if platform not in SUPPORTED_DEVICE_PLATFORMS:
        return 400, {
            "error": "Plataforma do dispositivo não suportada.",
            "supported_platforms": sorted(SUPPORTED_DEVICE_PLATFORMS),
        }

    now = django_tz.now()
    with transaction.atomic():
        device = DriverDevice.objects.select_for_update().filter(
            operator=driver.operator,
            driver=driver,
            deviceIdentifier=payload.device_identifier,
        ).first()

        active_devices = DriverDevice.objects.select_for_update().filter(
            operator=driver.operator,
            driver=driver,
            status='ACTIVE',
        )

        if not device and active_devices.count() >= MAX_ACTIVE_DRIVER_DEVICES:
            return 409, {
                "error": "Limite de dispositivos ativos atingido para este motorista.",
                "max_active_devices": MAX_ACTIVE_DRIVER_DEVICES,
            }

        if device and device.status != 'ACTIVE' and active_devices.count() >= MAX_ACTIVE_DRIVER_DEVICES:
            return 409, {
                "error": "Revogue outro dispositivo antes de reativar este aparelho.",
                "max_active_devices": MAX_ACTIVE_DRIVER_DEVICES,
            }

        if device:
            device.platform = platform
            device.label = payload.label
            device.status = 'ACTIVE'
            device.trusted = True
            device.metadata = payload.metadata
            device.lastSeenAt = now
            device.save(update_fields=['platform', 'label', 'status', 'trusted', 'metadata', 'lastSeenAt'])
        else:
            device = DriverDevice.objects.create(
                operator=driver.operator,
                driver=driver,
                deviceIdentifier=payload.device_identifier,
                platform=platform,
                label=payload.label,
                status='ACTIVE',
                trusted=True,
                metadata=payload.metadata,
                lastSeenAt=now,
            )

    return 201, {
        "device_id": str(device.id),
        "status": device.status,
        "trusted": device.trusted,
        "active_devices": DriverDevice.objects.filter(
            operator=driver.operator,
            driver=driver,
            status='ACTIVE',
        ).count(),
    }


@router.get("/devices", response=List[dict])
def list_driver_devices(request):
    driver = _get_authenticated_driver(request)
    devices = DriverDevice.objects.filter(
        operator=driver.operator,
        driver=driver,
    ).order_by('-lastSeenAt', '-createdAt')

    return [
        {
            "device_id": str(device.id),
            "device_identifier": device.deviceIdentifier,
            "platform": device.platform,
            "label": device.label,
            "status": device.status,
            "trusted": device.trusted,
            "last_seen_at": device.lastSeenAt.isoformat() if device.lastSeenAt else None,
            "created_at": device.createdAt.isoformat() if device.createdAt else None,
        }
        for device in devices
    ]


@router.post("/devices/{device_id}/revoke", response={200: dict, 404: dict})
def revoke_driver_device(request, device_id: UUID):
    driver = _get_authenticated_driver(request)
    device = DriverDevice.objects.filter(
        pk=device_id,
        operator=driver.operator,
        driver=driver,
    ).first()

    if not device:
        return 404, {"error": "Dispositivo não encontrado para este motorista."}

    if device.status != 'REVOKED' or device.trusted:
        device.status = 'REVOKED'
        device.trusted = False
        device.save(update_fields=['status', 'trusted'])
        _purge_driver_fastlane_tokens(driver.id)

    return 200, {
        "device_id": str(device.id),
        "status": device.status,
        "trusted": device.trusted,
    }


@router.post("/security/device-attestation", response={201: dict, 400: dict, 404: dict, 409: dict})
def attest_driver_device(request, payload: DriverDeviceAttestationPayload):
    driver = _get_authenticated_driver(request)
    risk_level = _normalize_risk_level(payload.risk_level)

    if risk_level not in SUPPORTED_DEVICE_RISK_LEVELS:
        return 400, {
            "error": "Nível de risco não suportado.",
            "supported_risk_levels": sorted(SUPPORTED_DEVICE_RISK_LEVELS),
        }

    device = _get_driver_device(driver, payload.device_identifier)
    if not device:
        return 404, {"error": "Dispositivo não registrado para este motorista."}
    if device.status != 'ACTIVE':
        return 409, {"error": "O dispositivo informado não está ativo."}

    event = DriverDeviceSecurityEvent.objects.create(
        operator=driver.operator,
        driver=driver,
        device=device,
        riskLevel=risk_level,
        flags=payload.flags,
    )

    device.lastSeenAt = django_tz.now()
    if risk_level in {'HIGH', 'CRITICAL'}:
        device.trusted = False
    device.save(update_fields=['lastSeenAt', 'trusted'])

    action = "none"
    if risk_level in {'HIGH', 'CRITICAL'}:
        _purge_driver_fastlane_tokens(driver.id)
        action = "fastlane_tokens_purged"

    return 201, {
        "security_event_id": str(event.id),
        "device_id": str(device.id),
        "risk_level": event.riskLevel,
        "trusted": device.trusted,
        "action": action,
    }


@router.post("/offline/sync", response={202: dict, 400: dict, 404: dict, 409: dict})
def sync_driver_offline_batch(request, payload: DriverOfflineSyncPayload):
    driver = _get_authenticated_driver(request)
    if not payload.items:
        return 400, {"error": "O lote offline precisa conter ao menos um item."}

    device = _get_driver_device(driver, payload.device_identifier)
    if not device:
        return 404, {"error": "Dispositivo não registrado para este motorista."}
    if device.status != 'ACTIVE':
        return 409, {"error": "O dispositivo informado não está ativo."}

    batch = DriverOfflineSyncBatch.objects.create(
        operator=driver.operator,
        driver=driver,
        deviceIdentifier=device.deviceIdentifier,
        payload={"items": payload.items},
        itemCount=len(payload.items),
        status='RECEIVED',
    )
    device.lastSeenAt = django_tz.now()
    device.save(update_fields=['lastSeenAt'])

    try:
        from integration.models import IntegrationOutbox
        IntegrationOutbox.objects.create(
            operator_id=driver.operator_id,
            aggregateType='DRIVER_OFFLINE_SYNC',
            aggregateId=batch.id,
            eventType='DRIVER_OFFLINE_SYNC_RECEIVED',
            payload={
                "driver_id": str(driver.id),
                "device_identifier": device.deviceIdentifier,
                "batch_id": str(batch.id),
                "item_count": batch.itemCount,
            },
        )
    except Exception:
        pass

    return 202, {
        "batch_id": str(batch.id),
        "status": batch.status,
        "item_count": batch.itemCount,
    }


@router.post("/expenses", response={201: dict, 400: dict, 404: dict})
def create_driver_expense(request, payload: DriverExpensePayload):
    driver = _get_authenticated_driver(request)
    expense_type = _normalize_expense_type(payload.type)
    if not expense_type:
        return 400, {
            "error": "Tipo de despesa não suportado.",
            "supported_types": sorted(set(EXPENSE_TYPE_ALIASES.values())),
        }

    order = None
    if payload.order_id:
        order = _get_driver_order(driver, payload.order_id)
        if not order:
            return 404, {"error": "Ordem não encontrada para este motorista."}

    from finance.models import DriverExpense

    expense = DriverExpense.objects.create(
        operator=driver.operator,
        driver=driver,
        order=order,
        type=expense_type,
        amountCents=payload.amountCents,
        description=payload.description,
        status='SUBMITTED',
        metadata=payload.metadata,
    )

    return 201, {
        "expense_id": str(expense.id),
        "status": expense.status,
        "type": expense.type,
        "amount_cents": expense.amountCents,
    }


@router.post("/expenses/{expense_id}/receipt", response={201: dict, 404: dict})
def upload_driver_expense_receipt(
    request,
    expense_id: UUID,
    file: File[UploadedFile],
    lat: Form[float | None] = None,
    lng: Form[float | None] = None,
    captured_at: Form[str | None] = None,
):
    driver = _get_authenticated_driver(request)
    from finance.models import DriverExpense, DriverExpenseReceipt

    expense = DriverExpense.objects.filter(
        pk=expense_id,
        operator=driver.operator,
        driver=driver,
    ).first()
    if not expense:
        return 404, {"error": "Despesa não encontrada para este motorista."}

    receipt = DriverExpenseReceipt.objects.create(
        operator=driver.operator,
        expense=expense,
        fileUrl=_mock_storage_url("expense-receipts", expense.id, file.name),
        metadata={
            "lat": lat,
            "lng": lng,
            "captured_at_client": captured_at,
            "device_identifier": request.headers.get("x-device-id"),
            "original_filename": file.name,
        },
    )

    return 201, {
        "receipt_id": str(receipt.id),
        "expense_id": str(expense.id),
        "file_url": receipt.fileUrl,
    }


@router.get("/communications/threads", response=List[dict])
def list_driver_threads(request):
    driver = _get_authenticated_driver(request)
    threads = DriverCommunicationThread.objects.filter(
        operator=driver.operator,
        driver=driver,
    ).select_related("order", "store").order_by("-updatedAt")[:200]

    return [
        {
            "thread_id": str(thread.id),
            "order_id": str(thread.order_id) if thread.order_id else None,
            "store_id": str(thread.store_id) if thread.store_id else None,
            "status": thread.status,
            "source_type": thread.sourceType,
            "subject": thread.subject,
            "updated_at": thread.updatedAt.isoformat() if thread.updatedAt else None,
        }
        for thread in threads
    ]


@router.get("/communications/threads/{thread_id}/messages", response={200: List[dict], 404: dict})
def list_driver_thread_messages(request, thread_id: UUID):
    driver = _get_authenticated_driver(request)
    thread = DriverCommunicationThread.objects.filter(
        pk=thread_id,
        operator=driver.operator,
        driver=driver,
    ).first()
    if not thread:
        return 404, {"error": "Thread não encontrada para este motorista."}

    messages = DriverCommunicationMessage.objects.filter(thread=thread).order_by("createdAt")
    return 200, [
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


@router.post("/communications/threads/{thread_id}/messages", response={201: dict, 404: dict})
def send_driver_thread_message(request, thread_id: UUID, payload: CommunicationMessagePayload):
    driver = _get_authenticated_driver(request)
    thread = DriverCommunicationThread.objects.filter(
        pk=thread_id,
        operator=driver.operator,
        driver=driver,
    ).first()
    if not thread:
        return 404, {"error": "Thread não encontrada para este motorista."}

    message = DriverCommunicationMessage.objects.create(
        operator=driver.operator,
        thread=thread,
        senderType="DRIVER",
        senderName=driver.name,
        message=payload.message,
        metadata=payload.metadata,
    )
    thread.updatedAt = django_tz.now()
    thread.save(update_fields=["updatedAt"])

    return 201, {
        "thread_id": str(thread.id),
        "message_id": str(message.id),
    }


@router.get("/compliance/consents", response=List[DriverConsentItem])
def list_driver_consents(request):
    driver = _get_authenticated_driver(request)
    now = django_tz.now()
    documents = list(
        ComplianceDocument.objects.filter(
            operator=driver.operator,
            audienceType="DRIVER",
            active=True,
            archivedAt__isnull=True,
            effectiveAt__lte=now,
        ).order_by("-required", "-effectiveAt", "-createdAt")
    )
    acceptances = {
        acceptance.document_id: acceptance
        for acceptance in DriverConsentAcceptance.objects.filter(
            operator=driver.operator,
            driver=driver,
            document_id__in=[document.id for document in documents],
        )
    }
    return [
        _serialize_driver_consent(document, acceptances.get(document.id))
        for document in documents
    ]


@router.post("/compliance/consents/{consent_id}/accept", response={200: dict, 404: dict, 409: dict})
@idempotent(timeout=86400)
def accept_driver_consent(request, consent_id: UUID):
    driver = _get_authenticated_driver(request)
    now = django_tz.now()
    document = ComplianceDocument.objects.filter(
        pk=consent_id,
        operator=driver.operator,
        audienceType="DRIVER",
    ).first()
    if not document:
        return 404, {"error": "Termo não encontrado para este motorista."}
    if not document.active or document.archivedAt is not None:
        return 409, {"error": "Termo não está mais ativo para aceite."}
    if document.effectiveAt and document.effectiveAt > now:
        return 409, {"error": "Termo ainda não está vigente para aceite."}

    acceptance = DriverConsentAcceptance.objects.filter(
        operator=driver.operator,
        driver=driver,
        document=document,
    ).first()
    created = False

    device_identifier = request.headers.get("x-device-id")
    request_ip = _request_ip(request)
    user_agent = request.headers.get("user-agent")
    metadata = {"accepted_via": "driver_api"}

    if acceptance:
        update_fields = []
        if acceptance.revokedAt is not None:
            acceptance.revokedAt = None
            acceptance.revokedReason = None
            update_fields.extend(["revokedAt", "revokedReason"])
        if acceptance.deviceIdentifier != device_identifier:
            acceptance.deviceIdentifier = device_identifier
            update_fields.append("deviceIdentifier")
        if acceptance.ipAddress != request_ip:
            acceptance.ipAddress = request_ip
            update_fields.append("ipAddress")
        if acceptance.userAgent != user_agent:
            acceptance.userAgent = user_agent
            update_fields.append("userAgent")
        merged_metadata = {**(acceptance.metadata or {}), **metadata}
        if merged_metadata != (acceptance.metadata or {}):
            acceptance.metadata = merged_metadata
            update_fields.append("metadata")
        if update_fields:
            acceptance.save(update_fields=update_fields)
    else:
        created = True
        acceptance = DriverConsentAcceptance.objects.create(
            operator=driver.operator,
            driver=driver,
            document=document,
            deviceIdentifier=device_identifier,
            ipAddress=request_ip,
            userAgent=user_agent,
            metadata=metadata,
        )

    return 200, {
        "consent_id": str(document.id),
        "acceptance_id": str(acceptance.id),
        "accepted": True,
        "already_accepted": not created,
        "accepted_at": acceptance.acceptedAt.isoformat() if acceptance.acceptedAt else None,
    }


@router.post("/compliance/consents/{consent_id}/revoke", response={200: dict, 404: dict, 409: dict})
@idempotent(timeout=86400)
def revoke_driver_consent(request, consent_id: UUID, payload: DriverConsentRevokePayload):
    driver = _get_authenticated_driver(request)
    acceptance = DriverConsentAcceptance.objects.filter(
        operator=driver.operator,
        driver=driver,
        document_id=consent_id,
    ).first()
    if not acceptance:
        return 404, {"error": "Termo ainda não possui aceite para este motorista."}

    if acceptance.revokedAt is not None:
        return 200, {
            "consent_id": str(consent_id),
            "acceptance_id": str(acceptance.id),
            "revoked": True,
            "already_revoked": True,
            "revoked_at": acceptance.revokedAt.isoformat() if acceptance.revokedAt else None,
        }

    acceptance.revokedAt = django_tz.now()
    acceptance.revokedReason = payload.reason
    acceptance.metadata = {
        **(acceptance.metadata or {}),
        "revoked_via": "driver_api",
    }
    acceptance.save(update_fields=["revokedAt", "revokedReason", "metadata"])

    return 200, {
        "consent_id": str(consent_id),
        "acceptance_id": str(acceptance.id),
        "revoked": True,
        "already_revoked": False,
        "revoked_at": acceptance.revokedAt.isoformat() if acceptance.revokedAt else None,
    }


@router.get("/privacy/requests", response=List[PrivacyDataRequestItem])
def list_driver_privacy_requests(request):
    driver = _get_authenticated_driver(request)
    data_requests = PrivacyDataRequest.objects.filter(
        operator=driver.operator,
        driver=driver,
        subjectType="DRIVER",
    ).order_by("-createdAt")[:200]
    return [_serialize_privacy_request(data_request) for data_request in data_requests]


@router.post("/privacy/requests", response={201: dict, 400: dict})
def create_driver_privacy_request(request, payload: PrivacyDataRequestCreatePayload):
    driver = _get_authenticated_driver(request)
    normalized_request_type = normalize_privacy_request_type(payload.request_type)
    if normalized_request_type not in SUPPORTED_PRIVACY_REQUEST_TYPES:
        return 400, {
            "error": "Tipo de solicitação de privacidade não suportado.",
            "supported_request_types": sorted(SUPPORTED_PRIVACY_REQUEST_TYPES),
        }

    data_request = PrivacyDataRequest.objects.create(
        operator=driver.operator,
        subjectType="DRIVER",
        driver=driver,
        requestType=normalized_request_type,
        status="OPEN",
        description=payload.description,
        metadata={
            **payload.metadata,
            "opened_via": "driver_api",
        },
    )
    return 201, {
        "request_id": str(data_request.id),
        "subject_type": data_request.subjectType,
        "request_type": data_request.requestType,
        "status": data_request.status,
    }
