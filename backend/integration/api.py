import hashlib
import logging
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.http import HttpRequest
from ninja import Router, Schema

from accounts.models import Operator
from logistics.models import Store
from config.core_models import tenant_context
from .connectors.registry import get_connector, list_registered_slugs
from .models import (
    IntegrationConnector,
    IntegrationWebhookLog,
    StoreIntegration,
)
from .services import create_order_from_intent

logger = logging.getLogger(__name__)

router = Router()


# ============================================================
# Schemas
# ============================================================


class ConnectorOut(Schema):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    auth_type: str
    config_schema: dict = {}
    capabilities: list = []
    status: str
    documentation_url: Optional[str] = None
    version: str = "1.0.0"


class StoreIntegrationCreateIn(Schema):
    store_id: str
    connector_slug: str
    config: dict = {}
    auto_create_order: bool = True


class StoreIntegrationUpdateIn(Schema):
    active: Optional[bool] = None
    auto_create_order: Optional[bool] = None
    config: Optional[dict] = None
    regenerate_secret: Optional[bool] = None


class StoreIntegrationOut(Schema):
    id: str
    store_id: str
    store_name: str
    connector_slug: str
    connector_name: str
    connector_icon_url: Optional[str] = None
    auth_type: str
    active: bool
    auto_create_order: bool
    webhook_url: str
    webhook_secret: Optional[str] = None
    config: dict = {}
    last_webhook_at: Optional[str] = None
    error_count: int = 0
    error_message: Optional[str] = None
    created_at: str


class WebhookLogItemOut(Schema):
    id: str
    connector_slug: str
    status: str
    order_id: Optional[str] = None
    error_detail: Optional[str] = None
    processing_ms: Optional[int] = None
    created_at: str


class WebhookLogsResponse(Schema):
    total: int
    logs: List[WebhookLogItemOut]


# ============================================================
# Helpers
# ============================================================


def _get_auth_info(request: HttpRequest) -> tuple[Optional[uuid.UUID], bool]:
    """Extrai (operator_id, is_admin) do auth context."""
    user = getattr(request, "auth", None)
    if not user:
        return None, False

    raw_op_id = None
    role = ""
    is_platform_admin = False

    if isinstance(user, dict):
        from accounts.auth import get_staff_member

        role = str(user.get("role", "")).upper()
        is_platform_admin = bool(user.get("is_platform_admin")) or role in ("PLATFORM_ADMIN", "SUPERADMIN")
        if is_platform_admin:
            raw_op_id = request.headers.get("X-Operator-Id") or user.get("operator_id")
        else:
            staff = get_staff_member(request)
            raw_op_id = staff.operator_id if staff else user.get("operator_id")
            role = str(staff.role if staff else "").upper()
    else:
        role = str(getattr(user, "role", "")).upper()
        raw_op_id = getattr(user, "operator_id", None) or getattr(getattr(user, "operator", None), "id", None)
        is_platform_admin = bool(getattr(user, "is_platform_admin", False)) or role in ("PLATFORM_ADMIN", "SUPERADMIN")
        if is_platform_admin and not raw_op_id:
            raw_op_id = request.headers.get("X-Operator-Id")

    is_admin = is_platform_admin or role in ("ADMIN", "OPERADOR_ADMIN")
    parsed_uuid: Optional[uuid.UUID] = None
    if raw_op_id:
        if isinstance(raw_op_id, uuid.UUID):
            parsed_uuid = raw_op_id
        else:
            try:
                parsed_uuid = uuid.UUID(str(raw_op_id))
            except (ValueError, TypeError):
                parsed_uuid = None

    return parsed_uuid, is_admin


def _get_operator_id(request: HttpRequest) -> Optional[uuid.UUID]:
    op_id, _ = _get_auth_info(request)
    return op_id


def _get_admin_operator_id(request: HttpRequest) -> Optional[uuid.UUID]:
    operator_id, is_admin = _get_auth_info(request)
    return operator_id if is_admin else None


def _validate_public_config(config: dict) -> Optional[str]:
    if not isinstance(config, dict):
        return "A configuração deve ser um objeto JSON."
    if len(str(config)) > 16_384:
        return "A configuração excede o limite permitido."
    sensitive_fragments = ("secret", "token", "password", "api_key", "apikey", "private_key")
    for key in config:
        normalized = str(key).lower().replace("-", "_")
        if any(fragment in normalized for fragment in sensitive_fragments):
            return "Credenciais secretas não podem ser armazenadas na configuração pública."
    return None


def _validate_connector_config(connector: Optional[IntegrationConnector], config: dict) -> Optional[str]:
    error = _validate_public_config(config)
    if error:
        return error
    schema = (connector.config_schema or {}) if connector else {}
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    if schema.get("additionalProperties") is False:
        unknown = sorted(set(config) - set(properties))
        if unknown:
            return f"Campos de configuração não suportados: {', '.join(unknown)}."
    for required in schema.get("required", []):
        if required not in config:
            return f"Campo de configuração obrigatório: {required}."
    for key, value in config.items():
        rule = properties.get(key, {})
        expected = rule.get("type")
        if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            return f"{key} deve ser um número inteiro."
        if expected == "string" and not isinstance(value, str):
            return f"{key} deve ser texto."
        if isinstance(value, (int, float)):
            if "minimum" in rule and value < rule["minimum"]:
                return f"{key} está abaixo do mínimo permitido."
            if "maximum" in rule and value > rule["maximum"]:
                return f"{key} excede o máximo permitido."
        if isinstance(value, str) and len(value) > rule.get("maxLength", 16_384):
            return f"{key} excede o tamanho permitido."
    return None


def _sanitized_headers(headers: dict) -> dict:
    allowed = {"content-type", "user-agent", "x-request-id", "x-event-id"}
    return {str(k).lower(): str(v)[:500] for k, v in headers.items() if str(k).lower() in allowed}


def _serialize_integration(integration: StoreIntegration, show_secret: bool = False) -> dict:
    connector = integration.connector
    slug = connector.slug if connector else (integration.provider or "generic-webhook")
    name = connector.name if connector else (integration.provider or "Webhook")
    icon = connector.icon_url if connector else None
    auth_type = connector.auth_type if connector else "webhook_signature"

    webhook_url = f"/api/v1/integration/webhooks/{slug}/{integration.id}"

    raw_secret = integration.get_webhook_secret() or integration.webhook_secret
    if raw_secret:
        if show_secret:
            secret = raw_secret
        else:
            secret = f"{raw_secret[:8]}...{raw_secret[-4:]}" if len(raw_secret) > 12 else "***"
    else:
        secret = None

    return {
        "id": str(integration.id),
        "store_id": str(integration.store_id),
        "store_name": getattr(integration.store, "name", "Loja"),
        "connector_slug": slug,
        "connector_name": name,
        "connector_icon_url": icon,
        "auth_type": auth_type,
        "active": integration.active,
        "auto_create_order": integration.auto_create_order,
        "webhook_url": webhook_url,
        "webhook_secret": secret,
        "config": integration.config or {},
        "last_webhook_at": integration.last_webhook_at.isoformat() if integration.last_webhook_at else None,
        "error_count": integration.error_count,
        "error_message": integration.error_message,
        "created_at": integration.createdAt.isoformat() if hasattr(integration, "createdAt") and integration.createdAt else "",
    }


# ============================================================
# Gateway de Webhooks (Sem Auth de sessão - usa HMAC/Secret)
# ============================================================


@router.post(
    "/webhooks/{connector_slug}/{integration_id}",
    auth=None,
    response={200: dict, 202: dict, 400: dict, 401: dict, 404: dict, 500: dict, 503: dict},
)
def receive_connector_webhook(
    request: HttpRequest,
    connector_slug: str,
    integration_id: str,
):
    """
    Gateway de Ingestão de Webhooks dos Conectores (Generic, iFood, etc).
    Valida autenticidade via conector, deduplica via SHA-256 e gera corridas.
    """
    start_time = time.perf_counter()
    raw_body = request.body
    if len(raw_body) > 1_048_576:
        return 400, {"error": "Payload excede o limite de 1 MB."}
    request_headers = dict(request.headers.items())

    # 1. Buscar integração
    try:
        target_id = uuid.UUID(integration_id)
    except (ValueError, TypeError):
        return 404, {"error": "ID de integração inválido."}

    # Webhooks não possuem uma sessão de usuário. Em PostgreSQL, a função
    # SECURITY DEFINER resolve somente o tenant da integração opaca; toda a
    # leitura/escrita seguinte volta a acontecer sob as policies RLS normais.
    if connection.vendor == "postgresql" and not getattr(
        request, "_integration_tenant_scoped", False
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT resolve_store_integration_operator(%s::uuid)", [str(target_id)]
            )
            row = cursor.fetchone()
        operator_id = row[0] if row else None
        if not operator_id:
            return 404, {"error": f"Integração '{integration_id}' não encontrada."}
        request._integration_tenant_scoped = True
        with tenant_context(operator_id):
            return receive_connector_webhook(
                request, connector_slug=connector_slug, integration_id=integration_id
            )

    integration = (
        StoreIntegration.objects.filter(id=target_id)
        .select_related("operator", "store", "connector")
        .first()
    )

    if not integration:
        return 404, {"error": f"Integração '{integration_id}' não encontrada."}

    if not integration.active:
        return 503, {"error": "Esta integração está desativada ou pausada pelo operador."}

    # 2. Resolver conector
    configured_slug = integration.connector.slug if integration.connector else None
    if configured_slug != connector_slug:
        return 404, {"error": "Conector não corresponde à integração informada."}

    connector = get_connector(connector_slug)
    if not connector:
        # Tentar verificar se o slug do conector na integração confere
        if integration.connector and integration.connector.slug == connector_slug:
            connector = get_connector(integration.connector.slug)
    if not connector:
        return 404, {"error": f"Conector '{connector_slug}' não suportado ou inativo."}

    # 3. Validar assinatura/autenticidade
    if not connector.verify_webhook(request_headers, raw_body, integration):
        return 401, {"error": "Assinatura ou credencial do webhook inválida."}

    # 4. Deduplicação via SHA-256 do payload bruto
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    existing_log = (
        IntegrationWebhookLog.objects.filter(
            integration=integration,
            raw_payload_hash=payload_hash,
        )
        .first()
    )

    if existing_log and existing_log.status in (
        IntegrationWebhookLog.LogStatus.PROCESSED,
        IntegrationWebhookLog.LogStatus.DUPLICATE,
    ):
        return 200, {
            "status": "already_processed",
            "webhook_id": str(existing_log.id),
            "order_id": str(existing_log.order_id) if existing_log.order_id else None,
            "message": "Webhook já processado com sucesso anteriormente.",
        }

    # 5. Criar registro inicial de auditoria
    try:
        with transaction.atomic():
            log = IntegrationWebhookLog.objects.create(
                integration=integration,
                connector_slug=connector_slug,
                raw_payload_hash=payload_hash,
                status=IntegrationWebhookLog.LogStatus.RECEIVED,
            )
    except IntegrityError:
        existing_log = IntegrationWebhookLog.objects.filter(
            integration=integration, raw_payload_hash=payload_hash
        ).first()
        return 200, {
            "status": "already_processed",
            "webhook_id": str(existing_log.id) if existing_log else None,
            "order_id": str(existing_log.order_id) if existing_log and existing_log.order_id else None,
        }

    # 6. Parsear e Normalizar
    try:
        normalized_headers = {str(key).lower(): value for key, value in request_headers.items()}
        content_type = normalized_headers.get("content-type", "application/json")
        parsed_payload = connector.parse_payload(raw_body, content_type=content_type)
        order_intent = connector.normalize(parsed_payload, integration)
    except Exception as e:
        logger.warning("Erro ao parsear webhook da integração %s: %s", integration.id, e)
        log.status = IntegrationWebhookLog.LogStatus.FAILED
        log.error_detail = "payload_validation_failed"
        log.save(update_fields=["status", "error_detail"])

        integration.error_count += 1
        integration.error_message = "payload_validation_failed"
        integration.save(update_fields=["error_count", "error_message"])

        return 400, {"error": "Payload inválido para este conector.", "webhook_id": str(log.id)}

    # 7. Criar corrida se auto_create_order estiver ativo
    if integration.auto_create_order:
        try:
            order = create_order_from_intent(order_intent, integration, webhook_log=log)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            log.processing_ms = elapsed_ms
            log.save(update_fields=["processing_ms"])

            return 200, {
                "status": "processed",
                "webhook_id": str(log.id),
                "order_id": str(order.id),
                "external_order_id": order_intent.external_order_id,
            }
        except Exception as e:
            logger.exception("Falha ao criar corrida para webhook %s: %s", log.id, e)
            log.status = IntegrationWebhookLog.LogStatus.FAILED
            log.error_detail = "order_creation_failed"
            log.save(update_fields=["status", "error_detail"])

            integration.error_count += 1
            integration.error_message = "order_creation_failed"
            integration.save(update_fields=["error_count", "error_message"])

            return 500, {"error": "Não foi possível criar a corrida.", "webhook_id": str(log.id)}

    # Se auto_create_order for falso, aceita o webhook para processamento posterior
    return 202, {
        "status": "received",
        "webhook_id": str(log.id),
        "external_order_id": order_intent.external_order_id,
    }


# ============================================================
# Gateway Legado (Compatibilidade com implementações existentes)
# ============================================================


@router.post(
    "/webhooks/{source}", auth=None, response={410: dict}
)
def receive_webhook(request: HttpRequest, source: str, payload: Dict[Any, Any]):
    """
    Gateway legado desativado. Integrações devem usar a URL com connector_slug
    e integration_id, que aplica segredo individual, deduplicação e RLS.
    """
    return 410, {
        "error": "Endpoint legado desativado. Reconfigure a integração usando o gateway versionado."
    }

# ============================================================
# API de Gestão do Hub (Autenticada para o Operador)
# ============================================================


@router.get("/connectors", response=List[ConnectorOut])
def list_connectors(request: HttpRequest):
    """
    Retorna o catálogo de conectores disponíveis no Hub de Integrações.
    """
    connectors = IntegrationConnector.objects.filter(
        slug__in=list_registered_slugs(), status="active"
    ).order_by("name")
    return [
        {
            "id": str(c.id),
            "slug": c.slug,
            "name": c.name,
            "description": c.description,
            "icon_url": c.icon_url,
            "auth_type": c.auth_type,
            "config_schema": c.config_schema or {},
            "capabilities": c.capabilities or [],
            "status": c.status,
            "documentation_url": c.documentation_url,
            "version": c.version,
        }
        for c in connectors
    ]


@router.get("/stores", response=List[dict])
def list_operator_stores(request: HttpRequest):
    """
    Lista as lojas do operador para seleção rápida no cadastro de integrações.
    """
    operator_id = _get_operator_id(request)
    if not operator_id:
        return []
    stores = Store.objects.filter(operator_id=operator_id).order_by("name")
    return [{"id": str(s.id), "name": s.name} for s in stores]


@router.get("", response={200: List[StoreIntegrationOut], 401: dict})
def list_store_integrations(request: HttpRequest):
    """
    Lista todas as integrações configuradas nas lojas do operador logado.
    """
    operator_id = _get_operator_id(request)
    if not operator_id:
        return 401, {"error": "Autenticação requerida."}

    integrations = (
        StoreIntegration.objects.filter(operator_id=operator_id)
        .select_related("store", "connector")
        .order_by("-createdAt")
    )
    return [_serialize_integration(item, show_secret=False) for item in integrations]


@router.post("", response={201: StoreIntegrationOut, 400: dict, 401: dict, 404: dict})
def create_store_integration(request: HttpRequest, payload: StoreIntegrationCreateIn):
    """
    Cria uma nova integração de conector vinculada a uma loja do operador.
    Gera automaticamente o webhook_secret para assinatura HMAC.
    """
    operator_id = _get_admin_operator_id(request)
    if not operator_id:
        return 401, {"error": "Administrador do operador requerido."}

    # Validar loja
    store = Store.objects.filter(id=payload.store_id, operator_id=operator_id).first()
    if not store:
        return 404, {"error": "Loja não encontrada para este operador."}

    # Buscar conector
    connector = IntegrationConnector.objects.filter(
        slug=payload.connector_slug, status="active"
    ).first()
    if not connector or not get_connector(payload.connector_slug):
        return 404, {"error": "Conector ainda não está disponível para conexão."}

    config_error = _validate_connector_config(connector, payload.config or {})
    if config_error:
        return 400, {"error": config_error}

    # Verificar se já existe integração ativa para esta loja e conector
    existing = StoreIntegration.objects.filter(
        store=store,
        connector=connector,
    ).first()
    if existing:
        return 400, {
            "error": f"A loja '{store.name}' já possui uma integração com '{connector.name}'. Edite a existente ou exclua-a."
        }

    # Gerar webhook secret criptograficamente seguro
    generated_secret = f"whsec_{secrets.token_hex(24)}"

    integration = StoreIntegration(
        operator_id=operator_id,
        store=store,
        connector=connector,
        provider=connector.slug.upper(),
        webhook_secret=generated_secret,
        config=payload.config or {},
        auto_create_order=payload.auto_create_order,
        active=True,
    )
    integration.save()

    return 201, _serialize_integration(integration, show_secret=True)


@router.patch("/{integration_id}", response={200: StoreIntegrationOut, 400: dict, 401: dict, 404: dict})
def update_store_integration(
    request: HttpRequest,
    integration_id: str,
    payload: StoreIntegrationUpdateIn,
):
    """
    Atualiza status (ativar/pausar), auto_create_order, configs ou regenera o webhook_secret.
    """
    operator_id = _get_admin_operator_id(request)
    if not operator_id:
        return 401, {"error": "Administrador do operador requerido."}

    try:
        target_id = uuid.UUID(integration_id)
    except (ValueError, TypeError):
        return 404, {"error": "ID de integração inválido."}

    integration = (
        StoreIntegration.objects.filter(id=target_id, operator_id=operator_id)
        .select_related("store", "connector")
        .first()
    )
    if not integration:
        return 404, {"error": "Integração não encontrada."}

    fields_to_update = []
    show_secret = False

    if payload.active is not None:
        integration.active = payload.active
        fields_to_update.append("active")

    if payload.auto_create_order is not None:
        integration.auto_create_order = payload.auto_create_order
        fields_to_update.append("auto_create_order")

    if payload.config is not None:
        config_error = _validate_connector_config(integration.connector, payload.config)
        if config_error:
            return 400, {"error": config_error}
        integration.config = payload.config
        fields_to_update.append("config")

    if payload.regenerate_secret:
        integration.webhook_secret = f"whsec_{secrets.token_hex(24)}"
        fields_to_update.append("webhook_secret")
        show_secret = True

    if fields_to_update:
        integration.save(update_fields=fields_to_update)

    return 200, _serialize_integration(integration, show_secret=show_secret)


@router.delete("/{integration_id}", response={200: dict, 401: dict, 404: dict})
def delete_store_integration(request: HttpRequest, integration_id: str):
    """
    Exclui uma integração de loja.
    """
    operator_id = _get_admin_operator_id(request)
    if not operator_id:
        return 401, {"error": "Administrador do operador requerido."}

    try:
        target_id = uuid.UUID(integration_id)
    except (ValueError, TypeError):
        return 404, {"error": "ID de integração inválido."}

    integration = StoreIntegration.objects.filter(
        id=target_id, operator_id=operator_id
    ).first()
    if not integration:
        return 404, {"error": "Integração não encontrada."}

    integration.active = False
    integration.save(update_fields=["active", "updatedAt"])
    return 200, {"success": True, "message": "Integração desativada com sucesso."}


@router.get("/{integration_id}/logs", response={200: WebhookLogsResponse, 401: dict, 404: dict})
def list_integration_webhook_logs(
    request: HttpRequest,
    integration_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Retorna o histórico de webhooks recebidos por uma integração específica para auditoria e depuração.
    """
    operator_id = _get_operator_id(request)
    if not operator_id:
        return 401, {"error": "Autenticação requerida."}

    try:
        target_id = uuid.UUID(integration_id)
    except (ValueError, TypeError):
        return 404, {"error": "ID de integração inválido."}

    integration = StoreIntegration.objects.filter(
        id=target_id, operator_id=operator_id
    ).first()
    if not integration:
        return 404, {"error": "Integração não encontrada."}

    qs = IntegrationWebhookLog.objects.filter(integration=integration)
    if status:
        qs = qs.filter(status=status.lower())

    limit = max(1, min(limit, 100))
    offset = max(0, min(offset, 100_000))
    total = qs.count()
    logs = qs.order_by("-createdAt")[offset : offset + limit]

    return {
        "total": total,
        "logs": [
            {
                "id": str(item.id),
                "connector_slug": item.connector_slug,
                "status": item.status,
                "order_id": str(item.order_id) if item.order_id else None,
                "error_detail": item.error_detail,
                "processing_ms": item.processing_ms,
                "created_at": item.createdAt.isoformat() if item.createdAt else "",
            }
            for item in logs
        ],
    }
