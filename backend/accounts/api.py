import logging
from ninja import Router
from ninja.errors import HttpError
from django.db import transaction
from django.utils import timezone
from uuid import uuid4
import redis

from accounts.models import Operator, SecurityDenylist
from logistics.models import Driver
from accounts.auth import platform_admin_required, require_role
from config.redis_client import get_redis
from shared_schemas.accounts import (
    OperatorCreatePayload,
    OperatorResponse,
    DriverRegistrationPayload,
    DriverResponse,
    DenyListPayload,
    DenyListResponse,
    DriverBiometricPayload,
    DriverBiometricResponse,
    BiometricWebhookPayload,
)
import httpx
import hmac
import hashlib
import os
from asgiref.sync import sync_to_async
from ninja import Header
from accounts.tasks import process_biometrics_webhook

router = Router(tags=["Accounts"])
logger = logging.getLogger(__name__)
r = get_redis()


@router.post("/admin/operators", response=OperatorResponse)
def create_operator(request, payload: OperatorCreatePayload):
    platform_admin_required(request)
    with transaction.atomic():
        operator = Operator.objects.create(
            id=uuid4(), name=payload.name, status=Operator.OperatorStatus.TRIAL
        )
        return operator


@router.post("/operator/drivers", response=DriverResponse)
def register_driver(request, payload: DriverRegistrationPayload):
    staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)

    import re

    clean_cpf = re.sub(r"[^\d]", "", payload.cpf)
    if len(clean_cpf) != 11:
        return 400, {"error": "CPF inválido."}

    # Check if Driver with this CPF already exists
    if Driver.objects.filter(operator=staff.operator, phone=payload.phone).exists():
        return 409, {"error": "Motorista com este telefone já registrado."}

    with transaction.atomic():
        driver = Driver.objects.create(
            id=uuid4(),
            operator=staff.operator,
            supabase_uid=str(uuid4()),
            name=payload.name,
            phone=payload.phone,
            pixKey=payload.cpf,  # Storing CPF as pixKey
            pixKeyType="CPF",
            active=True,
        )
        return driver


@router.post("/operator/drivers/biometrics", response=DriverBiometricResponse)
async def verify_biometrics(request, payload: DriverBiometricPayload):
    staff = await sync_to_async(require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"]))(request)
    
    try:
        driver = await Driver.objects.aget(id=payload.driver_id, operator=staff.operator)
    except Driver.DoesNotExist:
        return 404, {"error": "Motorista não encontrado."}
    
    provider_url = os.environ.get("BIOMETRICS_PROVIDER_URL", "https://api.fake-biometrics.com/verify")
    api_key = os.environ.get("BIOMETRICS_API_KEY", "dummy")
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                provider_url,
                json={
                    "driver_id": str(driver.id),
                    "face_image": payload.face_image_base64,
                    "cnh_image": payload.cnh_image_base64
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
        except httpx.RequestError as exc:
            logger.error(f"Erro na requisição para provedor de biometria: {exc}")
            return 503, {"error": "Serviço de biometria indisponível."}

    logger.info(f"Biometria enviada para processamento async: {driver.id}")

    return {
        "status": "PROCESSING",
        "match_score": 0.0,
        "message": "Biometria enviada. Aguardando processamento (Webhook)."
    }


@router.post("/operator/drivers/biometrics/webhook", response={200: dict, 401: dict})
def biometrics_webhook(request, payload: BiometricWebhookPayload, x_signature: str = Header(None)):  # type: ignore
    secret = os.environ.get("WEBHOOK_SECRET", "dummy-secret").encode('utf-8')
    if not x_signature:
        return 401, {"error": "Assinatura não fornecida."}
        
    payload_bytes = request.body
    expected_signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_signature):
        return 401, {"error": "Assinatura inválida."}
        
    process_biometrics_webhook.delay(str(payload.driver_id), payload.status)  # type: ignore
    return 200, {"message": "Webhook recebido com sucesso."}


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
            expiresAt=payload.expiresAt,
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
            logger.warning(
                "Falha ao sincronizar deny-list no Redis para %s:%s",
                payload.targetType,
                payload.targetId,
            )

        return deny_entry


@router.post("/auth/login", response={200: dict, 404: dict})
def login_callback(request):
    """
    Rota chamada pelo app logo após obter o JWT do Supabase.
    Serve para invalidar sessões antigas na Fast Lane (Device Tokens).
    """
    driver_uid = request.auth.get("sub")
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
                pipe.delete(
                    f"fastlane:token_meta:{t.decode('utf-8') if isinstance(t, bytes) else t}"
                )
            pipe.delete(tokens_key)
            pipe.execute()
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return 503, {"error": "Nao foi possivel invalidar sessoes antigas no momento."}

    return 200, {"message": "Sessão iniciada e tokens antigos invalidados com sucesso."}


# -----------------------------------------------------------------------------
# Native Auth Core Handlers & Routers
# -----------------------------------------------------------------------------
from ninja import Schema
from accounts.models import PlatformAdmin, StaffMember
from logistics.models import Store
from accounts.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    SecurityError,
)


class LoginPayload(Schema):
    email: str
    password: str


class RefreshPayload(Schema):
    refresh_token: str


def handle_login(request, payload: LoginPayload):
    email = payload.email.strip().lower()
    raw_password = payload.password

    # 1. Checa PlatformAdmin (Superadmin Soberano)
    admin = PlatformAdmin.objects.filter(email__iexact=email).first()
    if admin and admin.check_password(raw_password):
        token_payload = {
            "sub": str(admin.id),
            "email": admin.email,
            "role": "admin",
            "is_platform_admin": True,
            "operator_id": None,
        }
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token({"sub": str(admin.id), "type": "refresh"})

        all_ops = Operator.objects.all()
        companies_list = [{"id": "global", "nome": "Administração Global"}]
        for op in all_ops:
            companies_list.append({"id": str(op.id), "nome": op.name})

        return 200, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(admin.id),
                "email": admin.email,
                "name": admin.name,
                "role": "admin",
                "is_platform_admin": True,
                "company_id": "global",
                "operator_id": None,
                "companies": companies_list,
            },
        }

    # 2. Checa StaffMember (Equipe interna do Operador)
    staff = StaffMember.objects.filter(email__iexact=email, active=True).select_related("operator").first()
    if staff and staff.check_password(raw_password):
        token_payload = {
            "sub": str(staff.id),
            "email": staff.email,
            "role": staff.role,
            "is_platform_admin": False,
            "operator_id": str(staff.operator_id),
        }
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token({"sub": str(staff.id), "type": "refresh"})

        try:
            stores = list(Store.objects.filter(operator_id=staff.operator_id).values("id", "name"))
            companies_list = [{"id": str(s["id"]), "nome": s["name"]} for s in stores]
        except Exception:
            companies_list = []

        if not companies_list:
            op_name = staff.operator.name if staff.operator else "Operação Principal"
            companies_list = [{"id": str(staff.operator_id), "nome": op_name}]

        return 200, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(staff.id),
                "email": staff.email,
                "name": staff.name,
                "role": staff.role,
                "is_platform_admin": False,
                "operator_id": str(staff.operator_id),
                "company_id": str(staff.operator_id),
                "companies": companies_list,
            },
        }

    raise HttpError(401, "Credenciais inválidas.")


def handle_me(request):
    if not hasattr(request, "auth") or not request.auth:
        raise HttpError(401, "Não autenticado.")

    uid = request.auth.get("sub")
    is_admin = request.auth.get("is_platform_admin", False)

    if is_admin:
        admin = PlatformAdmin.objects.filter(id=uid).first()
        if not admin and "email" in request.auth:
            admin = PlatformAdmin.objects.filter(email=request.auth["email"]).first()

        all_ops = Operator.objects.all()
        companies_list = [{"id": "global", "nome": "Administração Global"}]
        for op in all_ops:
            companies_list.append({"id": str(op.id), "nome": op.name})

        return {
            "authenticated": True,
            "user": {
                "id": str(admin.id) if admin else uid,
                "email": admin.email if admin else request.auth.get("email", ""),
                "name": admin.name if admin else "Platform Admin",
                "role": "admin",
                "is_platform_admin": True,
                "company_id": "global",
                "machine_empresa_id": "global",
                "companies": companies_list,
            },
        }

    staff = StaffMember.objects.filter(id=uid, active=True).first()
    if not staff and "email" in request.auth:
        staff = StaffMember.objects.filter(email=request.auth["email"], active=True).first()

    if not staff:
        raise HttpError(401, "Usuário não encontrado.")

    try:
        stores = list(Store.objects.filter(operator_id=staff.operator_id).values("id", "name"))
        companies_list = [{"id": str(s["id"]), "nome": s["name"]} for s in stores]
    except Exception:
        companies_list = []

    if not companies_list:
        op_name = staff.operator.name if staff.operator else "Operação Principal"
        companies_list = [{"id": str(staff.operator_id), "nome": op_name}]

    return {
        "authenticated": True,
        "user": {
            "id": str(staff.id),
            "email": staff.email,
            "name": staff.name,
            "role": staff.role,
            "is_platform_admin": False,
            "operator_id": str(staff.operator_id),
            "company_id": str(staff.operator_id),
            "machine_empresa_id": str(staff.operator_id),
            "companies": companies_list,
        },
    }


def handle_refresh(request, payload: RefreshPayload):
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise HttpError(401, "Token não é de renovação.")
        uid = decoded.get("sub")
    except SecurityError as e:
        raise HttpError(401, str(e))

    admin = PlatformAdmin.objects.filter(id=uid).first()
    if admin:
        token_payload = {
            "sub": str(admin.id),
            "email": admin.email,
            "role": "admin",
            "is_platform_admin": True,
            "operator_id": None,
        }
        return {"access_token": create_access_token(token_payload), "token_type": "bearer"}

    staff = StaffMember.objects.filter(id=uid, active=True).first()
    if staff:
        token_payload = {
            "sub": str(staff.id),
            "email": staff.email,
            "role": staff.role,
            "is_platform_admin": False,
            "operator_id": str(staff.operator_id),
        }
        return {"access_token": create_access_token(token_payload), "token_type": "bearer"}

    raise HttpError(401, "Usuário não encontrado.")


def handle_logout(request):
    return {"success": True, "message": "Logout realizado com sucesso."}


# Router dedicado para /api/v1/auth/
api_auth_router = Router(tags=["Native Auth API"])
api_auth_router.post("/login", auth=None)(handle_login)
api_auth_router.get("/me")(handle_me)
api_auth_router.post("/refresh", auth=None)(handle_refresh)
api_auth_router.post("/logout")(handle_logout)

# Alias para manter compatibilidade
auth_router = api_auth_router
