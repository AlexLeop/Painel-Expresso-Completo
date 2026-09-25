import logging
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from accounts.models import StaffMember, PlatformAdmin
from typing import Any, List, Optional
from ninja.security import HttpBearer
from ninja.errors import HttpError
from logistics.models import ClientPortalUser
from accounts.security import decode_token, SecurityError

logger = logging.getLogger(__name__)


class NativeJWTAuth(HttpBearer):
    """
    Extrator e Validador JWT Nativo para o Django Ninja.
    Valida a assinatura localmente em O(1) com DJANGO_SECRET_KEY.
    """

    def authenticate(self, request: HttpRequest, token: str) -> Optional[Any]:
        try:
            claims = decode_token(token, expected_type="access")
            setattr(request, "auth", claims)
            return claims
        except SecurityError as e:
            logger.warning(f"Falha na validação do token JWT: {e}")
            raise HttpError(401, str(e))
        except Exception as e:
            logger.error(f"Erro inesperado na autenticação JWT: {e}")
            raise HttpError(401, "Token inválido")


# Alias para retrocompatibilidade
SupabaseJWTAuth = NativeJWTAuth


def get_staff_member(request: HttpRequest) -> Optional[StaffMember]:
    """Retorna o StaffMember a partir do JWT nativo extraído no request."""
    auth = getattr(request, "auth", None)
    if not auth:
        return None

    # Superadmin Sovereignty: Se for PlatformAdmin, cria representação soberana com bypass
    if auth.get("is_platform_admin"):
        from accounts.models import Operator

        uid = auth.get("sub")
        try:
            admin = PlatformAdmin.objects.filter(id=uid).first()
        except (ValidationError, ValueError, TypeError):
            admin = None
        if not admin and "email" in auth:
            admin = PlatformAdmin.objects.filter(email__iexact=auth["email"]).first()
        if not admin:
            return None

        target_operator_id = request.headers.get("X-Operator-Id") or auth.get("operator_id")
        op = None
        if target_operator_id and str(target_operator_id) not in ("global", "NaN", "undefined"):
            try:
                op = Operator.objects.filter(id=target_operator_id).first()
            except (ValidationError, ValueError, TypeError):
                op = None

        staff = StaffMember(
            id=admin.id,
            name=admin.name,
            email=admin.email,
            role=StaffMember.RoleType.ADMIN,
            operator=op,
            operator_id=op.id if op else None,
            active=True,
        )
        staff.is_platform_admin = True
        return staff

    uid = auth.get("sub")
    try:
        return StaffMember.objects.select_related("operator").get(id=uid, active=True)
    except (StaffMember.DoesNotExist, ValueError):
        try:
            return StaffMember.objects.select_related("operator").get(supabase_uid=uid, active=True)
        except (StaffMember.DoesNotExist, ValueError):
            return None


def require_role(roles: List[str]):
    """
    Dependência Ninja para exigir Roles específicos.
    Superadmin (is_platform_admin=True) possui soberania total e bypassa restrições de papel.
    """

    def dependency(request: HttpRequest) -> StaffMember:
        staff = get_staff_member(request)
        if not staff:
            raise HttpError(401, "Não autenticado ou Staff não encontrado.")
        if getattr(staff, "is_platform_admin", False):
            return staff
        if staff.role not in roles:
            raise HttpError(403, f"Acesso negado. Requer um dos roles: {roles}")
        return staff

    return dependency


def platform_admin_required(request: HttpRequest):
    """Dependência Ninja para Platform Admins globais (Superadmin)."""
    if not hasattr(request, "auth") or not request.auth:
        raise HttpError(401, "Não autenticado.")
    if not request.auth.get("is_platform_admin"):
        raise HttpError(403, "Acesso negado. Requer privilégios de Platform Admin.")

    uid = request.auth.get("sub")
    try:
        admin = PlatformAdmin.objects.filter(id=uid).first()
    except (ValidationError, ValueError, TypeError):
        admin = None
    if not admin and "email" in request.auth:
        admin = PlatformAdmin.objects.filter(email__iexact=request.auth["email"]).first()
    if not admin:
        raise HttpError(403, "Platform Admin não encontrado no banco.")
    return admin


def get_client_portal_user(request: HttpRequest) -> Optional[ClientPortalUser]:
    """Retorna o ClientPortalUser autenticado pelo JWT do Supabase."""
    if not hasattr(request, "auth") or not request.auth:
        return None
    uid = request.auth.get("sub")
    try:
        user = ClientPortalUser.objects.select_related("client", "operator").filter(
            id=uid, active=True
        ).first()
    except (ValidationError, ValueError, TypeError):
        user = None
    if user:
        return user
    try:
        return ClientPortalUser.objects.select_related("client", "operator").get(
            supabase_uid=uid, active=True
        )
    except (ClientPortalUser.DoesNotExist, ValidationError, ValueError, TypeError):
        if "email" in request.auth:
            return ClientPortalUser.objects.select_related("client", "operator").filter(
                email__iexact=request.auth["email"], active=True
            ).first()
        return None


def client_portal_required(request: HttpRequest) -> ClientPortalUser:
    client_user = get_client_portal_user(request)
    if not client_user:
        raise HttpError(
            401, "Não autenticado ou usuário do portal do cliente não encontrado."
        )
    return client_user
