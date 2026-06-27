from ninja import NinjaAPI
from typing import Optional
from logistics.models import Driver, Order
from accounts.models import Operator, StaffMember, PlatformAdmin
from config.api import SupabaseJWTAuth

panel_api = NinjaAPI(urls_namespace="panel_api")
auth_bearer = SupabaseJWTAuth()

@panel_api.get("/auth/me", auth=auth_bearer)
def auth_me(request):
    """
    Retorna o perfil do usuário autenticado no Supabase.
    Procura em StaffMember e PlatformAdmin.
    """
    uid = request.auth.get("sub")
    
    try:
        admin = PlatformAdmin.objects.get(supabase_uid=uid)
        return {
            "authenticated": True,
            "user": {
                "id": str(admin.id),
                "email": admin.email,
                "name": admin.name,
                "role": "admin",
                "company_id": "global",
            }
        }
    except PlatformAdmin.DoesNotExist:
        pass

    try:
        staff = StaffMember.objects.get(supabase_uid=uid, active=True)
        return {
            "authenticated": True,
            "user": {
                "id": str(staff.id),
                "email": staff.email,
                "name": staff.name,
                "role": staff.role.lower(),
                "company_id": str(staff.operator_id),
            }
        }
    except StaffMember.DoesNotExist:
        return panel_api.create_response(request, {"authenticated": False, "error": "Usuário não encontrado no banco de dados."}, status=401)


@panel_api.get("/db/configs")
def get_configs(request, company_id: Optional[str] = None):
    return {"company_id": company_id, "features": {}}


@panel_api.get("/db/company-drivers")
def get_company_drivers(
    request, company_id: Optional[str] = None, active_only: Optional[int] = 0
):
    drivers = Driver.objects.all()[:50]
    return [
        {
            "id": str(d.id),
            "name": d.name,
            "active": d.active,
            "company_id": company_id,
            "driverId": str(d.id),
        }
        for d in drivers
    ]


@panel_api.get("/db/companies")
def get_companies(request):
    ops = Operator.objects.all()
    return [{"id": str(o.id), "name": o.name} for o in ops]


@panel_api.get("/machine/rides")
def get_rides(request):
    orders = Order.objects.all().order_by("-created_at")[:50]
    return [
        {
            "id": str(o.id),
            "driver_id": str(o.driver_id) if o.driver_id else None,
            "status": o.status,
            "price": 0,
            "distance": 0,
        }
        for o in orders
    ]


@panel_api.get("/schedules")
def get_schedules(request, company_id: Optional[str] = None):
    return []


@panel_api.get("/db/entries")
def get_entries(request, company_id: Optional[str] = None):
    return []


@panel_api.get("/db/users")
def get_users(request):
    return []


@panel_api.get("/db/snapshots")
def get_snapshots(request):
    return []


# Catch-all
@panel_api.api_operation(["GET", "POST", "PUT", "DELETE"], "/{path:path}")
def catch_all(request, path: str):
    return {}
