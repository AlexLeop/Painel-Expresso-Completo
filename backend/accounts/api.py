import logging
from ninja import Router
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

    from config.supabase_client import supabase
    import re

    clean_cpf = re.sub(r"[^\d]", "", payload.cpf)
    if len(clean_cpf) != 11:
        return 400, {"error": "CPF inválido."}

    # Check if Driver with this CPF already exists (assuming CPF maps to pixKey for now or is stored in metadata)
    if Driver.objects.filter(operator=staff.operator, phone=payload.phone).exists():
        return 409, {"error": "Motorista com este telefone já registrado."}

    with transaction.atomic():
        auth_uid = str(uuid4())  # Fallback to mock if supabase is not available
        if supabase is not None:
            try:
                clean_phone = "".join(filter(str.isdigit, payload.phone))
                if not clean_phone.startswith("55"):
                    clean_phone = f"55{clean_phone}"

                logger.info(f"Registrando motorista com Phone Auth OTP: +{clean_phone}")

                resp = supabase.auth.admin.create_user(
                    {
                        "phone": f"+{clean_phone}",
                        "phone_confirm": True,
                        "user_metadata": {
                            "name": payload.name,
                            "role": "driver",
                            "operator_id": str(staff.operator.id),
                        },
                    }
                )
                auth_uid = resp.user.id
            except Exception as e:
                logger.error(f"Falha ao criar usuário no Supabase Auth: {e}")
                return 500, {
                    "error": "Falha na integração com provedor de autenticação."
                }

        driver = Driver.objects.create(
            id=uuid4(),
            operator=staff.operator,
            supabase_uid=auth_uid,
            name=payload.name,
            phone=payload.phone,
            pixKey=payload.cpf,  # Storing CPF as pixKey temporarily if not strictly defined
            pixKeyType="CPF",  # Default
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
