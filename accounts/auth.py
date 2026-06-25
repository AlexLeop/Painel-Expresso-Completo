from django.http import HttpRequest
from accounts.models import StaffMember, PlatformAdmin
from typing import List, Optional
from ninja.errors import HttpError
from logistics.models import ClientPortalUser

def get_staff_member(request: HttpRequest) -> Optional[StaffMember]:
    """Retorna o StaffMember a partir do JWT extraído pelo middleware global."""
    if not hasattr(request, "auth") or not request.auth:
        return None
    uid = request.auth.get("sub")
    try:
        return StaffMember.objects.get(supabase_uid=uid, active=True)
    except StaffMember.DoesNotExist:
        return None

def require_role(roles: List[str]):
    """Dependência Ninja para exigir Roles específicos."""
    def dependency(request: HttpRequest):
        staff = get_staff_member(request)
        if not staff:
            raise HttpError(401, "Não autenticado ou Staff não encontrado.")
        if staff.role not in roles:
            raise HttpError(403, f"Acesso negado. Requer um dos roles: {roles}")
        return staff
    return dependency

def platform_admin_required(request: HttpRequest):
    """Dependência Ninja para Platform Admins globais."""
    if not hasattr(request, "auth") or not request.auth:
        raise HttpError(401, "Não autenticado.")
    uid = request.auth.get("sub")
    try:
        admin = PlatformAdmin.objects.get(supabase_uid=uid)
        return admin
    except PlatformAdmin.DoesNotExist:
        raise HttpError(403, "Acesso negado. Requer privilégios de Platform Admin.")


def get_client_portal_user(request: HttpRequest) -> Optional[ClientPortalUser]:
    """Retorna o ClientPortalUser autenticado pelo JWT do Supabase."""
    if not hasattr(request, "auth") or not request.auth:
        return None
    uid = request.auth.get("sub")
    try:
        return ClientPortalUser.objects.select_related("client", "operator").get(supabase_uid=uid)
    except ClientPortalUser.DoesNotExist:
        return None


def client_portal_required(request: HttpRequest) -> ClientPortalUser:
    client_user = get_client_portal_user(request)
    if not client_user:
        raise HttpError(401, "Não autenticado ou usuário do portal do cliente não encontrado.")
    return client_user
