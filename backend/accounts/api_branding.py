"""
API de White-Label (Branding) para Operadores Logísticos.

Endpoints:
  GET    /api/v1/branding/public/{slug}   — Branding público (sem auth, para tela de login)
  GET    /api/v1/branding                  — Branding completo do operador logado
  PUT    /api/v1/branding                  — Atualiza branding (admin do operator ou PlatformAdmin)
  POST   /api/v1/branding/logo             — Upload de logo
  POST   /api/v1/branding/favicon          — Upload de favicon
"""

import re
import uuid
import logging
from urllib.parse import urlparse
from ninja import Router, Schema, UploadedFile
from ninja.params.functions import File
from django.http import HttpRequest
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from typing import Optional

from accounts.models import Operator
from accounts.models_branding import OperatorBranding

logger = logging.getLogger(__name__)

router = Router()

# ============================================================
# Schemas
# ============================================================

HEX_COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")
VALID_THEME_MODES = {"light", "dark", "auto"}

GLOBAL_PLATFORM_BRANDING = {
    "id": "global",
    "operator_id": "global",
    "brand_name": "Expresso Neves",
    "logo_url": None,
    "favicon_url": None,
    "color_primary": "#E55C00",
    "color_secondary": "#4f46e5",
    "color_accent": "#f59e0b",
    "color_background": "#F9F9FA",
    "color_surface": "#ffffff",
    "color_text": "#18181b",
    "dark_color_background": "#0a0a0a",
    "dark_color_surface": "#171717",
    "dark_color_text": "#fafafa",
    "theme_mode": "light",
}


class BrandingPublicOut(Schema):
    brand_name: str
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    color_primary: str = "#6366f1"
    color_secondary: str = "#4f46e5"
    color_accent: str = "#f59e0b"
    theme_mode: str = "light"


class BrandingFullOut(Schema):
    id: str
    operator_id: str
    brand_name: str
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    color_primary: str
    color_secondary: str
    color_accent: str
    color_background: str
    color_surface: str
    color_text: str
    dark_color_background: str
    dark_color_surface: str
    dark_color_text: str
    theme_mode: str


class BrandingUpdateIn(Schema):
    brand_name: Optional[str] = None
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    color_accent: Optional[str] = None
    color_background: Optional[str] = None
    color_surface: Optional[str] = None
    color_text: Optional[str] = None
    dark_color_background: Optional[str] = None
    dark_color_surface: Optional[str] = None
    dark_color_text: Optional[str] = None
    theme_mode: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None


# ============================================================
# Helpers
# ============================================================


def _validate_hex_color(value: str) -> bool:
    """Valida formato hex #RRGGBB para prevenir XSS via CSS injection."""
    return bool(HEX_COLOR_REGEX.match(value))


def _get_auth_info(request: HttpRequest) -> tuple[Optional[uuid.UUID], bool]:
    """
    Extrai (operator_id, is_admin) do auth context.
    Suporta dict (claims de NativeJWTAuth) ou instâncias (StaffMember / PlatformAdmin).
    """
    user = getattr(request, "auth", None)
    if not user:
        return None, False

    from accounts.auth import get_staff_member

    raw_op_id = None
    role = ""
    is_platform_admin = False

    if isinstance(user, dict):
        role = str(user.get("role", "")).upper()
        is_platform_admin = bool(user.get("is_platform_admin")) or role in ("PLATFORM_ADMIN", "SUPERADMIN")
        if is_platform_admin:
            raw_op_id = request.headers.get("X-Operator-Id") or request.GET.get("operator_id") or user.get("operator_id")
        else:
            staff = get_staff_member(request)
            raw_op_id = staff.operator_id if staff else user.get("operator_id")
            role = (staff.role if staff else "").upper()
    else:
        role = str(getattr(user, "role", "")).upper()
        raw_op_id = getattr(user, "operator_id", None) or getattr(getattr(user, "operator", None), "id", None)
        is_platform_admin = bool(getattr(user, "is_platform_admin", False)) or role in ("PLATFORM_ADMIN", "SUPERADMIN")
        if is_platform_admin and not raw_op_id:
            raw_op_id = request.headers.get("X-Operator-Id") or request.GET.get("operator_id")

    is_admin = is_platform_admin or role in ("ADMIN", "OPERADOR_ADMIN")
    parsed_uuid: Optional[uuid.UUID] = None
    if raw_op_id and str(raw_op_id) not in ("global", "NaN", "undefined"):
        if isinstance(raw_op_id, uuid.UUID):
            parsed_uuid = raw_op_id
        else:
            try:
                parsed_uuid = uuid.UUID(str(raw_op_id))
            except (ValueError, TypeError):
                parsed_uuid = None

    return parsed_uuid, is_admin


def _image_signature_is_valid(file: UploadedFile, allowed_types: set[str]) -> bool:
    """Confere o conteúdo real do arquivo; o Content-Type vem do cliente."""

    header = file.read(32)
    file.seek(0)
    signatures = {
        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
        "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
        "image/x-icon": header.startswith(b"\x00\x00\x01\x00"),
        "image/vnd.microsoft.icon": header.startswith(b"\x00\x00\x01\x00"),
    }
    return file.content_type in allowed_types and signatures.get(file.content_type, False)


def _save_brand_asset(file: UploadedFile, operator_id: uuid.UUID, kind: str) -> str:
    content_type = file.content_type or ""
    extensions = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
    }
    extension = extensions.get(content_type, ".png")
    safe_kind = get_valid_filename(kind)
    filename = f"branding/{safe_kind}/{operator_id}/{uuid.uuid4().hex}{extension}"
    stored_name = default_storage.save(filename, file)
    return default_storage.url(stored_name)


def _delete_stored_brand_asset(asset_url: Optional[str]) -> None:
    if not asset_url:
        return
    path = urlparse(asset_url).path.lstrip("/")
    if path.startswith("media/"):
        path = path[len("media/"):]
    if path.startswith("branding/") and default_storage.exists(path):
        default_storage.delete(path)


def _get_operator_id(request: HttpRequest) -> Optional[uuid.UUID]:
    op_id, _ = _get_auth_info(request)
    return op_id


def _serialize_branding(branding: OperatorBranding) -> dict:
    """Serializa branding completo."""
    return {
        "id": str(branding.id),
        "operator_id": str(branding.operator_id),
        "brand_name": branding.brand_name,
        "logo_url": branding.logo_url,
        "favicon_url": branding.favicon_url,
        "color_primary": branding.color_primary,
        "color_secondary": branding.color_secondary,
        "color_accent": branding.color_accent,
        "color_background": branding.color_background,
        "color_surface": branding.color_surface,
        "color_text": branding.color_text,
        "dark_color_background": branding.dark_color_background,
        "dark_color_surface": branding.dark_color_surface,
        "dark_color_text": branding.dark_color_text,
        "theme_mode": branding.theme_mode,
    }


def _serialize_public(branding: OperatorBranding) -> dict:
    """Serializa campos públicos apenas (para tela de login)."""
    return {
        "brand_name": branding.brand_name,
        "logo_url": branding.logo_url,
        "favicon_url": branding.favicon_url,
        "color_primary": branding.color_primary,
        "color_secondary": branding.color_secondary,
        "color_accent": branding.color_accent,
        "theme_mode": branding.theme_mode,
    }


# ============================================================
# Endpoints
# ============================================================


@router.get("/public/{slug}", auth=None, response={200: dict, 404: dict})
def get_public_branding(request: HttpRequest, slug: str):
    """
    Branding público de um operador por slug.
    Usado na tela de login para exibir logo/cores antes da autenticação.

    Este endpoint é público (sem auth) e retorna apenas campos visuais.
    Usa service-level query que bypassa RLS (sem role authenticated).
    """
    try:
        operator = Operator.objects.filter(slug=slug).first()
        if not operator:
            return 404, {"error": "Operador não encontrado."}

        branding = OperatorBranding.objects.filter(operator=operator).first()
        if not branding:
            # Retorna defaults com o nome do operador
            return 200, {
                "brand_name": operator.name,
                "logo_url": None,
                "favicon_url": None,
                "color_primary": "#6366f1",
                "color_secondary": "#4f46e5",
                "color_accent": "#f59e0b",
                "theme_mode": "light",
            }

        return 200, _serialize_public(branding)
    except Exception as e:
        logger.exception(f"Erro ao buscar branding público: {e}")
        return 404, {"error": "Erro ao buscar branding."}


@router.get("", response={200: dict, 404: dict})
def get_branding(request: HttpRequest):
    """
    Branding completo do operador logado.
    Requer autenticação. Retorna todos os campos de personalização.
    """
    operator_id, is_admin = _get_auth_info(request)
    if not operator_id:
        if is_admin:
            # PlatformAdmin sem operadora vinculada (escopo global):
            # SEMPRE retorna a marca oficial do sistema ("Expresso Neves").
            # NUNCA vazar dados ou nomes de empresas de operadoras logísticas.
            return 200, dict(GLOBAL_PLATFORM_BRANDING)
        return 404, {"error": "Operador não identificado."}

    branding = OperatorBranding.objects.filter(operator_id=operator_id).first()
    if not branding:
        # Cria branding default a partir do Operator
        operator = Operator.objects.filter(id=operator_id).first()
        if not operator:
            return 404, {"error": "Operador não encontrado."}

        branding = OperatorBranding.objects.create(
            id=uuid.uuid4(),
            operator=operator,
            brand_name=operator.name,
        )

    return 200, _serialize_branding(branding)


@router.put("", response={200: dict, 400: dict, 403: dict})
def update_branding(request: HttpRequest, payload: BrandingUpdateIn):
    """
    Atualiza branding do operador logado.
    Requer role ADMIN do operator ou PlatformAdmin.
    """
    operator_id, is_admin = _get_auth_info(request)
    if not operator_id:
        return 403, {"error": "Acesso negado. Selecione uma operadora para personalizar a marca."}
    if not is_admin:
        return 403, {"error": "Apenas administradores podem alterar o branding."}

    branding = OperatorBranding.objects.filter(operator_id=operator_id).first()
    if not branding:
        operator = Operator.objects.filter(id=operator_id).first()
        if not operator:
            return 400, {"error": "Operador não encontrado."}
        branding = OperatorBranding.objects.create(
            id=uuid.uuid4(),
            operator=operator,
            brand_name=operator.name,
        )

    # Validar e atualizar campos
    color_fields = [
        "color_primary", "color_secondary", "color_accent",
        "color_background", "color_surface", "color_text",
        "dark_color_background", "dark_color_surface", "dark_color_text",
    ]

    data = payload.dict(exclude_unset=True)
    errors = []

    for field in color_fields:
        if field in data and data[field] is not None:
            if not _validate_hex_color(data[field]):
                errors.append(f"{field} deve ser um hex válido (#RRGGBB)")

    if "theme_mode" in data and data["theme_mode"] not in VALID_THEME_MODES:
        errors.append(f"theme_mode deve ser: {', '.join(VALID_THEME_MODES)}")

    if "brand_name" in data and data["brand_name"] is not None:
        if len(data["brand_name"].strip()) == 0:
            errors.append("brand_name não pode ser vazio")
        elif len(data["brand_name"]) > 255:
            errors.append("brand_name máximo de 255 caracteres")

    if errors:
        return 400, {"error": "Validação falhou.", "details": errors}

    # URLs de assets só podem ser criadas pelos endpoints de upload. Aqui,
    # aceitar null permite remover logo/favicon com segurança.
    for asset_field in ("logo_url", "favicon_url"):
        if asset_field in data and data[asset_field] is not None:
            data.pop(asset_field)
        elif asset_field in data:
            _delete_stored_brand_asset(getattr(branding, asset_field, None))

    # Aplicar campos
    for field, value in data.items():
        if hasattr(branding, field):
            setattr(branding, field, value)

    branding.save()
    if "brand_name" in data and data["brand_name"]:
        Operator.objects.filter(id=operator_id).update(name=data["brand_name"])
    return 200, _serialize_branding(branding)


@router.post("/logo", response={200: dict, 400: dict, 403: dict})
def upload_logo(request: HttpRequest, file: UploadedFile = File(...)):
    """
    Upload do logo do operador.
    Aceita PNG, JPG e WebP. Máximo 2MB. SVG é rejeitado por risco de script.
    """
    operator_id, is_admin = _get_auth_info(request)
    if not operator_id:
        return 403, {"error": "Acesso negado. Selecione uma operadora para enviar a logo."}
    if not is_admin:
        return 403, {"error": "Apenas administradores podem alterar o branding."}

    # Validar tipo de arquivo
    allowed_types = {"image/png", "image/jpeg", "image/webp"}
    if not _image_signature_is_valid(file, allowed_types):
        return 400, {"error": "Arquivo inválido. Aceitos: PNG, JPG e WebP reais."}

    # Validar tamanho (2MB)
    if (file.size or 0) > 2 * 1024 * 1024:
        return 400, {"error": "Logo deve ter no máximo 2MB."}

    logo_url = _save_brand_asset(file, operator_id, "logos")

    # Atualizar branding
    branding = OperatorBranding.objects.filter(operator_id=operator_id).first()
    if branding:
        _delete_stored_brand_asset(branding.logo_url)
        branding.logo_url = logo_url
        branding.save()
    else:
        operator = Operator.objects.filter(id=operator_id).first()
        if operator:
            OperatorBranding.objects.create(
                id=uuid.uuid4(),
                operator=operator,
                brand_name=operator.name,
                logo_url=logo_url,
            )

    return 200, {"logo_url": logo_url}


@router.post("/favicon", response={200: dict, 400: dict, 403: dict})
def upload_favicon(request: HttpRequest, file: UploadedFile = File(...)):
    """
    Upload do favicon do operador.
    Aceita ICO ou PNG. Máximo 100KB. SVG é rejeitado por risco de script.
    """
    operator_id, is_admin = _get_auth_info(request)
    if not operator_id:
        return 403, {"error": "Acesso negado. Selecione uma operadora para enviar o favicon."}
    if not is_admin:
        return 403, {"error": "Apenas administradores podem alterar o branding."}

    allowed_types = {"image/x-icon", "image/vnd.microsoft.icon", "image/png"}
    if not _image_signature_is_valid(file, allowed_types):
        return 400, {"error": "Arquivo inválido. Aceitos: ICO ou PNG reais."}

    if (file.size or 0) > 100 * 1024:
        return 400, {"error": "Favicon deve ter no máximo 100KB."}

    favicon_url = _save_brand_asset(file, operator_id, "favicons")

    branding = OperatorBranding.objects.filter(operator_id=operator_id).first()
    if branding:
        _delete_stored_brand_asset(branding.favicon_url)
        branding.favicon_url = favicon_url
        branding.save()
    else:
        operator = Operator.objects.filter(id=operator_id).first()
        if operator:
            OperatorBranding.objects.create(
                id=uuid.uuid4(),
                operator=operator,
                brand_name=operator.name,
                favicon_url=favicon_url,
            )

    return 200, {"favicon_url": favicon_url}
