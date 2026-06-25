from ninja import Router
from typing import List, Dict
from django.db import transaction
from django.utils import timezone
from datetime import date
from pydantic import BaseModel, Field
from uuid import UUID

from config.redis_client import get_redis
from logistics.models import (
    Store, Driver, Order, Manifest, ScheduleEntry, Turno, Stop,
    OrderAssignmentAudit, DriverCommunicationThread, DriverCommunicationMessage,
    ComplianceDocument, PrivacyDataRequest, ComplianceRetentionPolicy
)
from logistics.compliance import (
    SUPPORTED_COMPLIANCE_AUDIENCES,
    SUPPORTED_PRIVACY_REQUEST_STATUSES,
    SUPPORTED_RETENTION_RESOURCE_TYPES,
    normalize_compliance_audience,
    normalize_privacy_request_status,
    normalize_retention_resource_type,
)
from finance.models import Contract
from accounts.auth import require_role
from integration.models import IntegrationOutbox
from finance.business_date import resolve_store_business_date
from logistics.schemas import (
    OrderSchema, DriverSchema, DispatchPayload,
    OrderReassignmentPayload, CommunicationThreadCreatePayload, CommunicationMessagePayload,
    ComplianceDocumentPayload, PrivacyDataRequestItem, PrivacyDataRequestResolvePayload,
    ComplianceRetentionPolicyPayload, ComplianceRetentionPolicyItem
)

router = Router(tags=["Operator"])
r = get_redis()

class ContractPayload(BaseModel):
    store_id: UUID
    compensationMode: str
    rideFeePerDeliveryCents: int
    minimumRidesFeeFloorCents: int
    minimumFloorBps: int
    adminTaxThresholdCents: int
    adminTaxFixedAmountCents: int
    adminTaxBps: int

class SchedulePayload(BaseModel):
    driver_id: UUID
    store_id: UUID
    turno_id: UUID
    target_date: date
    minGuaranteedOverrideCents: int = 0


def _serialize_privacy_request(data_request: PrivacyDataRequest) -> Dict:
    return {
        "request_id": str(data_request.id),
        "subject_type": data_request.subjectType,
        "request_type": data_request.requestType,
        "status": data_request.status,
        "description": data_request.description,
        "resolution": data_request.resolution,
        "resolved_at": data_request.resolvedAt.isoformat() if data_request.resolvedAt else None,
        "metadata": data_request.metadata or {},
        "created_at": data_request.createdAt.isoformat() if data_request.createdAt else None,
        "updated_at": data_request.updatedAt.isoformat() if data_request.updatedAt else None,
    }


def _serialize_retention_policy(policy: ComplianceRetentionPolicy) -> Dict:
    return {
        "policy_id": str(policy.id),
        "resource_type": policy.resourceType,
        "retention_days": policy.retentionDays,
        "active": policy.active,
        "last_executed_at": policy.lastExecutedAt.isoformat() if policy.lastExecutedAt else None,
        "metadata": policy.metadata or {},
        "created_at": policy.createdAt.isoformat() if policy.createdAt else None,
        "updated_at": policy.updatedAt.isoformat() if policy.updatedAt else None,
    }


def _clear_order_runtime_state(order: Order, previous_driver_id):
    from logistics.api_driver import clear_order_runtime_state

    clear_order_runtime_state(order, previous_driver_id)

@router.get("/dashboard", response=Dict)
def get_dashboard(request):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    
    # Aggregates for the dashboard
    today = timezone.localdate()
    orders_today = Order.objects.filter(operator=staff.operator, businessDate=today).count()
    active_drivers = Driver.objects.filter(operator=staff.operator, active=True).count()
    online_drivers = Driver.objects.filter(operator=staff.operator, online=True).count()
    
    return {
        "orders_today": orders_today,
        "active_drivers": active_drivers,
        "online_drivers": online_drivers
    }

@router.post("/contracts", response=Dict)
def create_contract(request, payload: ContractPayload):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    
    with transaction.atomic():
        store = Store.objects.get(pk=payload.store_id, operator=staff.operator)
        contract, created = Contract.objects.update_or_create(
            operator=staff.operator,
            store=store,
            defaults={
                "compensationMode": payload.compensationMode,
                "rideFeePerDeliveryCents": payload.rideFeePerDeliveryCents,
                "minimumRidesFeeFloorCents": payload.minimumRidesFeeFloorCents,
                "minimumFloorBps": payload.minimumFloorBps,
                "adminTaxThresholdCents": payload.adminTaxThresholdCents,
                "adminTaxFixedAmountCents": payload.adminTaxFixedAmountCents,
                "adminTaxBps": payload.adminTaxBps,
            }
        )
        return {"id": str(contract.id), "store_id": str(store.id), "created": created}

@router.post("/schedule", response=Dict)
def create_schedule(request, payload: SchedulePayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    
    with transaction.atomic():
        driver = Driver.objects.get(pk=payload.driver_id, operator=staff.operator)
        store = Store.objects.get(pk=payload.store_id, operator=staff.operator)
        turno = Turno.objects.get(pk=payload.turno_id, operator=staff.operator)
        
        schedule, created = ScheduleEntry.objects.get_or_create(
            operator=staff.operator,
            driver=driver,
            store=store,
            turno=turno,
            date=payload.target_date,
            defaults={
                "minGuaranteedOverrideCents": payload.minGuaranteedOverrideCents
            }
        )
        return {"id": str(schedule.id), "created": created}

@router.post("/orders/dispatch", response=OrderSchema)
def dispatch_order(request, payload: DispatchPayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    
    with transaction.atomic():
        store = Store.objects.get(pk=payload.store_id, operator=staff.operator)
        # Se um driver foi especificado, já nasce OFFERED para ele.
        # Caso contrário, nasce OFFERED para a praça.
        driver = None
        if payload.driver_id:
            driver = Driver.objects.get(pk=payload.driver_id, operator=staff.operator)
            
        b_date = resolve_store_business_date(store, explicit_business_date=payload.businessDate)
        
        order = Order.objects.create(
            operator=staff.operator,
            store=store,
            driver=driver,
            status=Order.OrderStatus.OFFERED,
            fareValueCents=payload.fareValueCents,
            distanceMeters=payload.distanceMeters or 0,
            businessDate=b_date
        )
        
        # Broadcast (via Celery ou direto se async) para a praça ou motoboy
        from logistics.api_driver import broadcast_disappearing_card
        broadcast_disappearing_card(staff.operator.id, order.id)
        
        return order


@router.post("/orders/{order_id}/reassign", response={200: dict, 404: dict, 409: dict})
def reassign_order(request, order_id: UUID, payload: OrderReassignmentPayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    order = Order.objects.filter(
        pk=order_id,
        operator=staff.operator,
    ).select_related("store", "driver").first()
    if not order:
        return 404, {"error": "Ordem não encontrada."}
    if order.status not in {Order.OrderStatus.OFFERED, Order.OrderStatus.ACCEPTED}:
        return 409, {"error": "A ordem não está em estado seguro para redistribuição."}

    new_driver = None
    if payload.new_driver_id:
        new_driver = Driver.objects.filter(pk=payload.new_driver_id, operator=staff.operator).first()
        if not new_driver:
            return 404, {"error": "Motorista de destino não encontrado."}

    previous_driver = order.driver
    with transaction.atomic():
        order.driver = new_driver
        order.status = Order.OrderStatus.OFFERED
        order.acceptedAt = None
        order.save(update_fields=["driver", "status", "acceptedAt"])

        OrderAssignmentAudit.objects.create(
            operator=staff.operator,
            order=order,
            previousDriver=previous_driver,
            newDriver=new_driver,
            changedByStaff=staff,
            reason=payload.reason,
        )

        IntegrationOutbox.objects.create(
            operator=staff.operator,
            aggregateType="ORDER",
            aggregateId=order.id,
            eventType="ORDER_REASSIGNED",
            payload={
                "order_id": str(order.id),
                "store_id": str(order.store_id),
                "previous_driver_id": str(previous_driver.id) if previous_driver else None,
                "new_driver_id": str(new_driver.id) if new_driver else None,
                "reason": payload.reason,
                "changed_by_staff_id": str(staff.id),
                "occurred_at": timezone.now().isoformat(),
            },
        )

    _clear_order_runtime_state(order, previous_driver.id if previous_driver else None)
    from logistics.api_driver import broadcast_disappearing_card
    broadcast_disappearing_card(staff.operator.id, order.id)

    return 200, {
        "order_id": str(order.id),
        "status": order.status,
        "driver_id": str(order.driver_id) if order.driver_id else None,
    }

from ninja.pagination import paginate

from ninja import FilterSchema, Query
from typing import Optional

class OrderFilterSchema(FilterSchema):
    status: Optional[str] = None
    store_id: Optional[UUID] = None

@router.get("/orders", response=List[OrderSchema])
@paginate
def list_orders(request, filters: OrderFilterSchema = Query(...)):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    qs = Order.objects.filter(operator=staff.operator)
    qs = filters.filter(qs)
    return qs.select_related('store', 'driver').order_by('-requestedAt')

@router.get("/drivers", response=List[DriverSchema])
@paginate
def list_drivers(request):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    return Driver.objects.filter(operator=staff.operator).order_by('-online', 'name')


@router.get("/communications/threads", response=List[dict])
def list_operator_threads(request):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    threads = DriverCommunicationThread.objects.filter(
        operator=staff.operator,
    ).select_related("order", "store", "driver").order_by("-updatedAt")[:200]
    return [
        {
            "thread_id": str(thread.id),
            "order_id": str(thread.order_id) if thread.order_id else None,
            "store_id": str(thread.store_id) if thread.store_id else None,
            "driver_id": str(thread.driver_id),
            "status": thread.status,
            "source_type": thread.sourceType,
            "subject": thread.subject,
            "updated_at": thread.updatedAt.isoformat() if thread.updatedAt else None,
        }
        for thread in threads
    ]


@router.post("/communications/threads", response={201: dict, 404: dict, 409: dict})
def create_operator_thread(request, payload: CommunicationThreadCreatePayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    order = Order.objects.filter(
        pk=payload.order_id,
        operator=staff.operator,
    ).select_related("store", "driver").first()
    if not order:
        return 404, {"error": "Ordem não encontrada."}
    if not order.driver_id:
        return 409, {"error": "A ordem ainda não possui motorista vinculado."}

    thread = DriverCommunicationThread.objects.create(
        operator=staff.operator,
        order=order,
        store=order.store,
        driver=order.driver,
        sourceType="OPERATOR",
        status="OPEN",
        subject=payload.subject,
        metadata=payload.metadata,
    )
    message = DriverCommunicationMessage.objects.create(
        operator=staff.operator,
        thread=thread,
        senderType="OPERATOR",
        senderName=staff.name,
        message=payload.message,
        metadata=payload.metadata,
    )
    return 201, {"thread_id": str(thread.id), "message_id": str(message.id)}


@router.post("/communications/threads/{thread_id}/messages", response={201: dict, 404: dict})
def send_operator_thread_message(request, thread_id: UUID, payload: CommunicationMessagePayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    thread = DriverCommunicationThread.objects.filter(
        pk=thread_id,
        operator=staff.operator,
    ).first()
    if not thread:
        return 404, {"error": "Thread não encontrada."}

    message = DriverCommunicationMessage.objects.create(
        operator=staff.operator,
        thread=thread,
        senderType="OPERATOR",
        senderName=staff.name,
        message=payload.message,
        metadata=payload.metadata,
    )
    thread.updatedAt = timezone.now()
    thread.save(update_fields=["updatedAt"])
    return 201, {"thread_id": str(thread.id), "message_id": str(message.id)}


@router.get("/compliance/documents", response=List[dict])
def list_compliance_documents(request, audience_type: str = "DRIVER"):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    normalized_audience = normalize_compliance_audience(audience_type)
    documents = ComplianceDocument.objects.filter(
        operator=staff.operator,
        audienceType=normalized_audience,
    ).order_by("-active", "-effectiveAt", "-createdAt")[:200]
    return [
        {
            "document_id": str(document.id),
            "audience_type": document.audienceType,
            "code": document.code,
            "title": document.title,
            "version": document.version,
            "required": document.required,
            "active": document.active,
            "effective_at": document.effectiveAt.isoformat() if document.effectiveAt else None,
            "archived_at": document.archivedAt.isoformat() if document.archivedAt else None,
            "metadata": document.metadata,
        }
        for document in documents
    ]


@router.post("/compliance/documents", response={201: dict, 400: dict, 409: dict})
def create_compliance_document(request, payload: ComplianceDocumentPayload):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    normalized_audience = normalize_compliance_audience(payload.audience_type)
    if normalized_audience not in SUPPORTED_COMPLIANCE_AUDIENCES:
        return 400, {"error": "Audience de compliance não suportada."}

    existing = ComplianceDocument.objects.filter(
        operator=staff.operator,
        audienceType=normalized_audience,
        code=payload.code,
        version=payload.version,
    ).first()
    if existing:
        return 409, {"error": "Já existe um documento com este código e versão."}

    document = ComplianceDocument.objects.create(
        operator=staff.operator,
        audienceType=normalized_audience,
        code=payload.code,
        title=payload.title,
        version=payload.version,
        body=payload.body,
        required=payload.required,
        active=True,
        effectiveAt=payload.effective_at or timezone.now(),
        metadata=payload.metadata,
    )
    return 201, {
        "document_id": str(document.id),
        "audience_type": document.audienceType,
        "code": document.code,
        "version": document.version,
        "active": document.active,
    }


@router.post("/compliance/documents/{document_id}/archive", response={200: dict, 404: dict, 409: dict})
def archive_compliance_document(request, document_id: UUID):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    document = ComplianceDocument.objects.filter(
        pk=document_id,
        operator=staff.operator,
    ).first()
    if not document:
        return 404, {"error": "Documento de compliance não encontrado."}
    if not document.active:
        return 409, {"error": "Documento já está arquivado."}

    document.active = False
    document.archivedAt = timezone.now()
    document.save(update_fields=["active", "archivedAt", "updatedAt"])
    return 200, {
        "document_id": str(document.id),
        "active": document.active,
        "archived_at": document.archivedAt.isoformat() if document.archivedAt else None,
    }


@router.get("/privacy/requests", response=List[PrivacyDataRequestItem])
def list_privacy_requests(request, status: str = "", subject_type: str = ""):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    queryset = PrivacyDataRequest.objects.filter(
        operator=staff.operator,
    ).select_related("driver", "clientPortalUser").order_by("-createdAt")

    normalized_status = normalize_privacy_request_status(status) if status else ""
    if normalized_status:
        queryset = queryset.filter(status=normalized_status)

    normalized_subject_type = subject_type.strip().upper() if subject_type else ""
    if normalized_subject_type:
        queryset = queryset.filter(subjectType=normalized_subject_type)

    return [_serialize_privacy_request(data_request) for data_request in queryset[:200]]


@router.post("/privacy/requests/{request_id}/resolve", response={200: dict, 400: dict, 404: dict, 409: dict})
def resolve_privacy_request(request, request_id: UUID, payload: PrivacyDataRequestResolvePayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    data_request = PrivacyDataRequest.objects.filter(
        pk=request_id,
        operator=staff.operator,
    ).first()
    if not data_request:
        return 404, {"error": "Solicitação de privacidade não encontrada."}
    if data_request.status in {"RESOLVED", "REJECTED"}:
        return 409, {"error": "Solicitação já está encerrada."}

    normalized_status = normalize_privacy_request_status(payload.status)
    if normalized_status not in SUPPORTED_PRIVACY_REQUEST_STATUSES - {"OPEN", "IN_PROGRESS"}:
        return 400, {
            "error": "Status final inválido para encerramento.",
            "supported_statuses": ["RESOLVED", "REJECTED"],
        }

    data_request.status = normalized_status
    data_request.resolution = payload.resolution
    data_request.resolvedAt = timezone.now()
    data_request.metadata = {
        **(data_request.metadata or {}),
        **payload.metadata,
        "resolved_by_staff_id": str(staff.id),
    }
    data_request.save(update_fields=["status", "resolution", "resolvedAt", "metadata", "updatedAt"])

    return 200, {
        "request_id": str(data_request.id),
        "status": data_request.status,
        "resolved_at": data_request.resolvedAt.isoformat() if data_request.resolvedAt else None,
    }


@router.get("/compliance/retention-policies", response=List[ComplianceRetentionPolicyItem])
def list_retention_policies(request):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    policies = ComplianceRetentionPolicy.objects.filter(
        operator=staff.operator,
    ).order_by("-active", "resourceType", "-createdAt")[:200]
    return [_serialize_retention_policy(policy) for policy in policies]


@router.post("/compliance/retention-policies", response={200: dict, 201: dict, 400: dict})
def upsert_retention_policy(request, payload: ComplianceRetentionPolicyPayload):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    normalized_resource_type = normalize_retention_resource_type(payload.resource_type)
    if normalized_resource_type not in SUPPORTED_RETENTION_RESOURCE_TYPES:
        return 400, {
            "error": "Recurso de retenção não suportado.",
            "supported_resource_types": sorted(SUPPORTED_RETENTION_RESOURCE_TYPES),
        }

    policy = ComplianceRetentionPolicy.objects.filter(
        operator=staff.operator,
        resourceType=normalized_resource_type,
    ).first()
    if policy:
        policy.retentionDays = payload.retention_days
        policy.active = payload.active
        policy.metadata = payload.metadata
        policy.save(update_fields=["retentionDays", "active", "metadata", "updatedAt"])
        return 200, {
            "policy_id": str(policy.id),
            "resource_type": policy.resourceType,
            "retention_days": policy.retentionDays,
            "active": policy.active,
        }

    policy = ComplianceRetentionPolicy.objects.create(
        operator=staff.operator,
        resourceType=normalized_resource_type,
        retentionDays=payload.retention_days,
        active=payload.active,
        metadata=payload.metadata,
    )
    return 201, {
        "policy_id": str(policy.id),
        "resource_type": policy.resourceType,
        "retention_days": policy.retentionDays,
        "active": policy.active,
    }


@router.post("/compliance/retention-policies/{policy_id}/disable", response={200: dict, 404: dict, 409: dict})
def disable_retention_policy(request, policy_id: UUID):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    policy = ComplianceRetentionPolicy.objects.filter(
        pk=policy_id,
        operator=staff.operator,
    ).first()
    if not policy:
        return 404, {"error": "Política de retenção não encontrada."}
    if not policy.active:
        return 409, {"error": "Política de retenção já está desativada."}

    policy.active = False
    policy.save(update_fields=["active", "updatedAt"])
    return 200, {
        "policy_id": str(policy.id),
        "active": policy.active,
    }

@router.get("/proofs/{proof_id}/url", response={200: dict, 403: dict, 404: dict})
def get_proof_url(request, proof_id: UUID):
    """
    Gera uma Presigned URL curta (15 minutos) para visualização do Proof of Delivery.
    Soluciona a quebra de LGPD por URLs públicas eternas.
    """
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    from logistics.models import Proof
    
    try:
        proof = Proof.objects.get(pk=proof_id, operator=staff.operator)
    except Proof.DoesNotExist:
        return 404, {"error": "Proof não encontrado."}
        
    import os
    import httpx
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        # Fallback local se não configurado
        return 200, {"url": proof.fileUrl}
        
    # Assume que proof.fileUrl guarde o path dentro do bucket, ex: "proofs/123/file.jpg"
    # ou guarde o próprio path, e usaremos 'proofs' como bucket default.
    parts = proof.fileUrl.split("/", 1)
    if len(parts) >= 2 and parts[0] in ["proofs", "driver-docs"]:
        bucket_name = parts[0]
        file_path = parts[1]
    else:
        bucket_name = "proofs"
        file_path = proof.fileUrl
        
    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket_name}/{file_path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Pede URL válida por 900s (15 min)
        resp = httpx.post(sign_url, json={"expiresIn": 900}, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            signed_url_path = data.get('signedURL')
            return 200, {"url": f"{SUPABASE_URL}/storage/v1{signed_url_path}"}
        else:
            return 403, {"error": f"Falha ao gerar URL assinada: {resp.text}"}
    except Exception as e:
        return 403, {"error": f"Erro interno ao gerar URL: {str(e)}"}
