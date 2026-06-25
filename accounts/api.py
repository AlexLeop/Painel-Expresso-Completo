import logging
from ninja import Router
from typing import List
from django.db import transaction
from django.utils import timezone
from uuid import uuid4
import redis

from accounts.models import Operator, SecurityDenylist, StaffMember, PlatformAdmin
from logistics.models import Driver
from accounts.auth import platform_admin_required, require_role, get_staff_member
from config.redis_client import get_redis
from shared_schemas.accounts import OperatorCreatePayload, OperatorResponse, DriverRegistrationPayload, DriverResponse, DenyListPayload, DenyListResponse

router = Router(tags=["Accounts"])
logger = logging.getLogger(__name__)
r = get_redis()

@router.post("/admin/operators", response=OperatorResponse)
def create_operator(request, payload: OperatorCreatePayload):
    admin = platform_admin_required(request)
    with transaction.atomic():
        operator = Operator.objects.create(
            id=uuid4(),
            name=payload.name,
            status=Operator.OperatorStatus.TRIAL
        )
        return operator

@router.post("/operator/drivers", response=DriverResponse)
def register_driver(request, payload: DriverRegistrationPayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
    
    with transaction.atomic():
        driver = Driver.objects.create(
            id=uuid4(),
            operator=staff.operator,
            supabase_uid=uuid4(), # Simulando Auth na criação manual
            name=payload.name,
            phone=payload.phone,
            pixKey=payload.pixKey or "",
            pixKeyType="CPF", # Default
            active=True
        )
        return driver

@router.post("/operator/security/deny-list", response=DenyListResponse)
def add_to_deny_list(request, payload: DenyListPayload):
    staff = require_role(["ADMIN", "MANAGER"])(request)
    
    with transaction.atomic():
        deny_entry = SecurityDenylist.objects.create(
            id=uuid4(),
            operator=staff.operator,
            targetId=payload.targetId,
            targetType=payload.targetType,
            reason=payload.reason,
            expiresAt=payload.expiresAt
        )
        
        # Sincroniza com o Redis (Layer 1)
        try:
            key = f"deny_list:{payload.targetType.lower()}:{payload.targetId}"
            if payload.expiresAt:
                delta = int((payload.expiresAt - timezone.now()).total_seconds())
                if delta > 0:
                    r.setex(key, delta, "BLOCKED")
            else:
                r.set(key, "BLOCKED")
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            # Postgres permanece como source of truth; o cache pode ser reconstruido depois.
            logger.warning("Falha ao sincronizar deny-list no Redis para %s:%s", payload.targetType, payload.targetId)
            
        return deny_entry

@router.post("/auth/login", response={200: dict, 404: dict})
def login_callback(request):
    """
    Rota chamada pelo app logo após obter o JWT do Supabase.
    Serve para invalidar sessões antigas na Fast Lane (Device Tokens).
    """
    driver_uid = request.auth.get('sub')
    try:
        driver = Driver.objects.get(supabase_uid=driver_uid)
    except Driver.DoesNotExist:
        return 404, {"error": "Driver não encontrado"}

    try:
        # Invalida todos os tokens da Fast Lane anteriores para este motorista
        tokens_key = f"fastlane:driver_tokens:{driver.id}"
        old_tokens = r.zrange(tokens_key, 0, -1)
        
        if old_tokens:
            pipe = r.pipeline()
            for t in old_tokens:
                pipe.delete(f"fastlane:token_meta:{t}")
            pipe.delete(tokens_key)
            pipe.execute()
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return 503, {"error": "Nao foi possivel invalidar sessoes antigas no momento."}

    return 200, {"message": "Sessão iniciada e tokens antigos invalidados com sucesso."}
