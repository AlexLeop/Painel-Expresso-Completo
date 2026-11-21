import logging
from ninja import Router
from typing import List, Dict, Any, Optional
from django.shortcuts import get_object_or_404
from pydantic import BaseModel, ConfigDict
from finance.models import ManualEntry
from logistics.models import Driver, Store
from accounts.models import Operator
from config.idempotency import idempotent
from django.db import transaction

logger = logging.getLogger(__name__)

_schema_ensured = True

def _ensure_database_schema():
    # DDL em runtime removido por segurança operacional e estabilidade sob escala.
    # Todas as alterações de schema residem exclusivamente em database/migrations/.
    pass

router = Router(tags=["Frontend DB Integration (Legacy)"])

class EntryPayload(BaseModel):
    id: Optional[str] = None
    companyId: Optional[int] = None
    company_id: Optional[int] = None
    driverId: Optional[str] = None
    driverName: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    description: Optional[str] = None
    turnoId: Optional[str] = None

@router.get("/entries")
def get_entries(request, company_id: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None):
    from accounts.auth import get_client_portal_user, require_role
    from ninja.errors import HttpError
    from finance.models import ManualEntry

    try:
        client_user = get_client_portal_user(request)
        if client_user:
            qs = ManualEntry.objects.filter(store__client_id=client_user.client_id, visibleToStore=True)
            if company_id and company_id != "global":
                try:
                    qs = qs.filter(store_id=company_id)
                except Exception:
                    pass
        else:
            staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
            is_admin = bool(getattr(staff, "is_platform_admin", False))
            qs = ManualEntry.objects.all()
            if not is_admin:
                qs = qs.filter(operator_id=staff.operator_id)
            elif company_id and company_id != "global":
                qs = qs.filter(operator_id=company_id)

        if start:
            qs = qs.filter(createdAt__gte=start)
        if end:
            qs = qs.filter(createdAt__lte=end)
            
        res = []
        for entry in qs:
            try:
                drv_name = entry.driver.name if getattr(entry, "driver", None) else ""
            except Exception:
                drv_name = ""
            res.append({
                "id": str(entry.id),
                "driverName": drv_name,
                "motoboy": drv_name,
                "type": entry.description or "",
                "categoria": "Crédito" if (entry.amountCents or 0) > 0 else "Débito",
                "valor": (entry.amountCents or 0) / 100.0,
                "data": entry.createdAt.strftime("%Y-%m-%d") if hasattr(entry.createdAt, 'strftime') else str(entry.createdAt),
                "description": entry.description or ""
            })
        return res
    except HttpError:
        raise
    except (ValueError, TypeError):
        raise HttpError(422, "Filtros de lançamento inválidos.")

@router.post("/entries")
def create_entry(request, payload: EntryPayload):
    from accounts.auth import require_role
    from ninja.errors import HttpError

    staff = require_role(["ADMIN", "MANAGER"])(request)
    requested_company_id = payload.company_id or payload.companyId
    company_id = requested_company_id if getattr(staff, "is_platform_admin", False) else staff.operator_id
    if not company_id:
        raise HttpError(422, "Selecione explicitamente um operador.")
    operator = get_object_or_404(Operator, pk=company_id)

    if not payload.driverId or payload.driverId == "9999":
        raise HttpError(422, "Selecione um motoboy válido.")
    driver = Driver.objects.filter(id=payload.driverId, operator=operator).first()
    if not driver:
        raise HttpError(404, "Motoboy não encontrado neste operador.")
        
    amt_cents = int((payload.amount or 0) * 100)

    from accounts.models import StaffMember
    staff_member = staff if not getattr(staff, "is_platform_admin", False) else None
    if not staff_member:
        staff_member = StaffMember.objects.filter(operator=operator).order_by("createdAt").first()

    entry = ManualEntry.objects.create(
        operator=operator,
        driver=driver,
        created_by_staff=staff_member,
        amountCents=amt_cents,
        description=f"[PlatformAdmin: {staff.name}] {payload.description or payload.type or ''}" if getattr(staff, "is_platform_admin", False) else (payload.description or payload.type or ""),
        status=ManualEntry.EntryStatus.APPROVED,
        taxCategory="NON_TAXABLE_REIMBURSEMENT" if amt_cents >= 0 else "DEDUCTION"
    )
    return {"success": True, "id": str(entry.id)}

@router.put("/entries")
def update_entry(request, payload: EntryPayload):
    from accounts.auth import require_role
    from ninja.errors import HttpError

    staff = require_role(["ADMIN", "MANAGER"])(request)
    if not payload.id:
        raise HttpError(422, "ID do lançamento é obrigatório.")
    entries = ManualEntry.objects.filter(pk=payload.id)
    if not getattr(staff, "is_platform_admin", False):
        entries = entries.filter(operator_id=staff.operator_id)
    entry = entries.first()
    if not entry:
        raise HttpError(404, "Lançamento não encontrado.")
    if payload.amount is not None:
        entry.amountCents = int(payload.amount * 100)
    if payload.description or payload.type:
        entry.description = payload.description or payload.type or entry.description
    entry.save()
    
    return {"success": True}

@router.delete("/entries")
def delete_entry(request, id: str):
    from accounts.auth import require_role
    from ninja.errors import HttpError

    staff = require_role(["ADMIN"])(request)
    entries = ManualEntry.objects.filter(pk=id)
    if not getattr(staff, "is_platform_admin", False):
        entries = entries.filter(operator_id=staff.operator_id)
    entry = entries.first()
    if not entry:
        raise HttpError(404, "Lançamento não encontrado.")
    entry.delete()
    return {"success": True}

@router.get("/companies")
def get_companies(request):
    from accounts.auth import get_client_portal_user, require_role
    from accounts.models import Operator
    from logistics.models import Store
    from finance.models import Contract

    _ensure_database_schema()

    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")

    qs = Store.objects.select_related("operator", "client").all()
    if client_id or auth.get("user_type") == "client_portal_user":
        client_user = get_client_portal_user(request)
        qs = qs.filter(client=client_user.client) if client_user else qs.none()
    else:
        staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
        if not getattr(staff, "is_platform_admin", False):
            qs = qs.filter(operator_id=staff.operator_id)
        elif staff.operator_id:
            qs = qs.filter(operator_id=staff.operator_id)

    res = []
    for s in qs:
        contract = Contract.objects.filter(store=s).first()
        lat = None
        lng = None
        if getattr(s, "geom", None):
            try:
                lat = float(s.geom.y)
                lng = float(s.geom.x)
            except Exception:
                pass

        bal = compute_store_balance(s)

        res.append({
            "id": str(s.id),
            "nome": s.name,
            "name": s.name,
            "documento": s.client.document if s.client else "",
            "telefone": "",
            "endereco": s.name,
            "lat": lat,
            "lng": lng,
            "active": s.operational if hasattr(s, "operational") else True,
            "ride_fee_per_delivery": (contract.rideFeePerDeliveryCents / 100.0) if (contract and contract.rideFeePerDeliveryCents) else 1.6,
            "minimum_rides_fee_floor": (contract.minimumRidesFeeFloorCents / 100.0) if (contract and contract.minimumRidesFeeFloorCents) else 350.0,
            "daily_rate_weekday": (contract.dailyRateWeekdayCents / 100.0) if (contract and contract.dailyRateWeekdayCents) else 60.0,
            "daily_rate_saturday": (contract.dailyRateSaturdayCents / 100.0) if (contract and contract.dailyRateSaturdayCents) else 70.0,
            "daily_rate_sunday": (contract.dailyRateSundayCents / 100.0) if (contract and contract.dailyRateSundayCents) else 80.0,
            "daily_rate_holiday": (contract.dailyRateHolidayCents / 100.0) if (contract and contract.dailyRateHolidayCents) else 80.0,
            "operator_id": str(s.operator_id),
            "operator_name": s.operator.name if s.operator else "",
            "billing_mode": bal.get("billing_mode", "PRE_PAGO"),
            "balance_cents": bal.get("balance_cents", 0),
            "balance_reais": bal.get("balance_reais", 0.0),
        })

    return res

@router.get("/users")
def get_users(request):
    from accounts.auth import require_role
    from accounts.models import StaffMember, PlatformAdmin
    from logistics.models import ClientPortalUser
    from ninja.errors import HttpError

    _ensure_database_schema()

    auth = getattr(request, "auth", None) or {}
    user_type = auth.get("user_type")
    client_id = auth.get("client_id")
    user_role = str(auth.get("role", "")).lower()

    try:
        if user_type == "client_portal_user" or client_id:
            if user_role == "operador_loja":
                # Operador comum da loja apenas despacha pedidos; não gerencia equipe
                return []
            # Gestor da Loja (lojista): lista a si mesmo e os operadores da sua própria loja
            res = []
            try:
                for c in ClientPortalUser.objects.filter(client_id=client_id).select_related("client").order_by("-createdAt"):
                    res.append({
                        "id": str(c.id),
                        "nome": c.name,
                        "name": c.name,
                        "email": c.email,
                        "role": getattr(c, "role", None) or "lojista",
                        "active": getattr(c, "active", True),
                        "companies": [{"id": str(c.client_id), "name": c.client.name}] if c.client else [],
                    })
            except Exception as e:
                logger.warning(f"Erro ao listar ClientPortalUser da loja {client_id}: {e}")
            return res

        actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
        is_admin = bool(getattr(actor, "is_platform_admin", False))
        op_id = actor.operator_id

        res = []
        if is_admin:
            # PlatformAdmin vê toda a hierarquia
            try:
                for p in PlatformAdmin.objects.all().order_by("-createdAt"):
                    res.append({
                        "id": str(p.id),
                        "nome": p.name,
                        "name": p.name,
                        "email": p.email,
                        "role": "superadmin",
                        "active": True,
                        "companies": [{"id": "global", "name": "Administração Global"}],
                    })
            except Exception as e:
                logger.warning(f"Erro ao listar PlatformAdmin: {e}")

            try:
                for u in StaffMember.objects.select_related("operator").all().order_by("-createdAt"):
                    res.append({
                        "id": str(u.id),
                        "nome": u.name,
                        "name": u.name,
                        "email": u.email,
                        "role": u.role,
                        "active": u.active,
                        "companies": [{"id": str(u.operator_id), "name": u.operator.name}] if u.operator else [],
                    })
            except Exception as e:
                logger.warning(f"Erro ao listar StaffMember para admin: {e}")

            try:
                for c in ClientPortalUser.objects.select_related("client").all().order_by("-createdAt"):
                    res.append({
                        "id": str(c.id),
                        "nome": c.name,
                        "name": c.name,
                        "email": c.email,
                        "role": getattr(c, "role", None) or "lojista",
                        "active": getattr(c, "active", True),
                        "companies": [{"id": str(c.client_id), "name": c.client.name}] if c.client else [],
                    })
            except Exception as e:
                logger.warning(f"Erro ao listar ClientPortalUser para admin: {e}")

        elif op_id:
            # Staff do operador vê seus colaboradores e usuários das lojas da sua central
            try:
                for u in StaffMember.objects.filter(operator_id=op_id).select_related("operator").order_by("-createdAt"):
                    res.append({
                        "id": str(u.id),
                        "nome": u.name,
                        "name": u.name,
                        "email": u.email,
                        "role": u.role,
                        "active": u.active,
                        "companies": [{"id": str(u.operator_id), "name": u.operator.name}] if u.operator else [],
                    })
            except Exception as e:
                logger.warning(f"Erro ao listar StaffMember para operador {op_id}: {e}")

            try:
                for c in ClientPortalUser.objects.filter(operator_id=op_id).select_related("client").order_by("-createdAt"):
                    res.append({
                        "id": str(c.id),
                        "nome": c.name,
                        "name": c.name,
                        "email": c.email,
                        "role": getattr(c, "role", None) or "lojista",
                        "active": getattr(c, "active", True),
                        "companies": [{"id": str(c.client_id), "name": c.client.name}] if c.client else [],
                    })
            except Exception as e:
                logger.warning(f"Erro ao listar ClientPortalUser para operador {op_id}: {e}")

        return res
    except HttpError:
        raise
    except Exception as e:
        logger.exception(f"Erro inesperado em get_users: {e}")
        return []

class UserPayload(BaseModel):
    id: Optional[str] = None
    fullName: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    companyId: Optional[str] = None
    companyIds: Optional[list] = None
    active: Optional[bool] = None


def _normalized_user_role(value: Optional[str]) -> str:
    aliases = {
        "ADMIN": "ADMIN",
        "ADMINISTRADOR": "ADMIN",
        "MANAGER": "MANAGER",
        "GESTOR": "MANAGER",
        "OPERATOR": "OPERATOR_ROLE",
        "OPERADOR": "OPERATOR_ROLE",
        "OPERATOR_ROLE": "OPERATOR_ROLE",
        "SUPERVISOR": "OPERATOR_ROLE",
        "COORDINATOR": "OPERATOR_ROLE",
        "COORDENADOR": "OPERATOR_ROLE",
        "VIEWER": "VIEWER",
        "VISUALIZADOR": "VIEWER",
        "LOJISTA": "LOJISTA",
        "GESTOR_LOJA": "LOJISTA",
        "GESTOR DA LOJA": "LOJISTA",
        "OPERADOR_LOJA": "OPERADOR_LOJA",
        "OPERADOR DA LOJA": "OPERADOR_LOJA",
        "FUNCIONARIO_LOJA": "OPERADOR_LOJA",
        "FUNCIONARIO DA LOJA": "OPERADOR_LOJA",
        "SUPERADMIN": "PLATFORM_ADMIN",
        "SUPERADMIN MASTER": "PLATFORM_ADMIN",
        "PLATFORM_ADMIN": "PLATFORM_ADMIN",
    }
    role = aliases.get((value or "OPERATOR_ROLE").strip().upper())
    if not role:
        from ninja.errors import HttpError

        raise HttpError(422, "Papel de usuário inválido.")
    return role


def _email_already_in_use(email: str, *, exclude_model=None, exclude_id=None) -> bool:
    from accounts.models import PlatformAdmin, StaffMember
    from logistics.models import ClientPortalUser

    for model in (PlatformAdmin, StaffMember, ClientPortalUser):
        queryset = model.objects.filter(email__iexact=email)
        if model is exclude_model and exclude_id:
            queryset = queryset.exclude(pk=exclude_id)
        if queryset.exists():
            return True
    return False


def _operator_from_company_reference(company_id: Optional[str]):
    """Resolve os IDs usados pela UI sem permitir fallback para outro tenant."""
    from accounts.models import Operator
    from logistics.models import Client, Store
    from django.core.exceptions import ValidationError

    if not company_id or company_id in ("global", "NaN", "undefined"):
        return None
    try:
        operator = Operator.objects.filter(id=company_id).first()
        if operator:
            return operator
        store = Store.objects.select_related("operator").filter(id=company_id).first()
        if store:
            return store.operator
        client = Client.objects.select_related("operator").filter(id=company_id).first()
        return client.operator if client else None
    except (ValidationError, ValueError, TypeError):
        return None

@router.post("/users")
def create_user(request, payload: UserPayload):
    from accounts.models import StaffMember, Operator, PlatformAdmin
    from logistics.models import ClientPortalUser, Client, Store
    from accounts.auth import require_role
    from django.db import IntegrityError, transaction
    from ninja.errors import HttpError
    import uuid

    _ensure_database_schema()

    auth = getattr(request, "auth", None) or {}
    user_type = auth.get("user_type")
    client_id = auth.get("client_id")
    caller_role = str(auth.get("role", "")).lower()

    # 1. Lojista (Gestor da Loja) cadastrando funcionário/operador da loja
    if user_type == "client_portal_user" or client_id:
        if caller_role not in ("lojista", "gestor", "gestor_loja"):
            raise HttpError(403, "Apenas o gestor da loja pode cadastrar funcionários/operadores para a loja.")

        if not payload.email or not payload.fullName:
            raise HttpError(422, "Nome e e-mail são obrigatórios.")
        if not payload.password or len(payload.password) < 6:
            raise HttpError(422, "A senha deve ter pelo menos 6 caracteres.")

        email = payload.email.strip().lower()
        if _email_already_in_use(email):
            raise HttpError(409, "Já existe um usuário com este e-mail.")

        client = Client.objects.filter(id=client_id, active=True).first()
        if not client:
            raise HttpError(404, "Loja parceira não encontrada ou inativa.")

        req_role = (payload.role or "").strip().lower()
        role_to_set = "lojista" if req_role in ("lojista", "gestor", "gestor_loja") else "operador_loja"

        with transaction.atomic():
            c_user = ClientPortalUser(
                id=uuid.uuid4(),
                supabase_uid=uuid.uuid4(),
                operator=client.operator,
                client=client,
                name=payload.fullName.strip(),
                email=email,
                role=role_to_set,
                active=True,
            )
            c_user.set_password(payload.password)
            c_user.save()
        return {"success": True, "id": str(c_user.id)}

    # 2. Staff da Central Logística ou PlatformAdmin
    actor = require_role(["ADMIN", "MANAGER"])(request)
    try:
        if not payload.email or not payload.fullName:
            raise HttpError(422, "Nome e e-mail são obrigatórios.")
        if not payload.password or len(payload.password) < 10:
            raise HttpError(422, "A senha deve ter pelo menos 10 caracteres.")

        email = payload.email.strip().lower()
        if _email_already_in_use(email):
            raise HttpError(409, "Já existe um usuário com este e-mail.")

        is_platform_admin = bool(getattr(actor, "is_platform_admin", False))

        c_id = payload.companyId
        if not c_id and payload.companyIds and len(payload.companyIds) > 0:
            c_id = payload.companyIds[0]

        role = _normalized_user_role(payload.role)
        if not is_platform_admin and role == "PLATFORM_ADMIN":
            raise HttpError(403, "Apenas o proprietário da plataforma pode criar administradores globais.")
        if actor.role == "MANAGER" and role in {"ADMIN", "MANAGER", "PLATFORM_ADMIN"}:
            raise HttpError(403, "Gestores não podem criar usuários com nível igual ou superior.")

        target_operator = None if is_platform_admin else actor.operator
        if is_platform_admin and role != "PLATFORM_ADMIN":
            target_operator = _operator_from_company_reference(c_id)
            if not target_operator:
                raise HttpError(422, "Selecione um operador válido para o novo usuário.")

        if role in ("LOJISTA", "OPERADOR_LOJA"):
            client = None
            if c_id:
                stores = Store.objects.select_related("client", "operator").filter(id=c_id)
                clients = Client.objects.select_related("operator").filter(id=c_id)
                if not is_platform_admin:
                    stores = stores.filter(operator=actor.operator)
                    clients = clients.filter(operator=actor.operator)
                store = stores.first()
                if store and store.client:
                    client = store.client
                if not client:
                    client = clients.first()
            if not client and target_operator:
                client = Client.objects.filter(operator=target_operator, active=True).first()
            if not client:
                raise HttpError(422, "Nenhum cliente/loja válido foi selecionado.")

            role_to_set = "operador_loja" if role == "OPERADOR_LOJA" else "lojista"
            with transaction.atomic():
                c_user = ClientPortalUser(
                    id=uuid.uuid4(),
                    supabase_uid=uuid.uuid4(),
                    operator=client.operator,
                    client=client,
                    name=payload.fullName.strip(),
                    email=email,
                    role=role_to_set,
                    active=True,
                )
                c_user.set_password(payload.password)
                c_user.save()
            return {"success": True, "id": str(c_user.id)}

        if role == "PLATFORM_ADMIN":
            if not is_platform_admin:
                raise HttpError(403, "Permissão insuficiente.")
            with transaction.atomic():
                p_admin = PlatformAdmin(id=uuid.uuid4(), name=payload.fullName.strip(), email=email)
                p_admin.set_password(payload.password)
                p_admin.save()
            return {"success": True, "id": str(p_admin.id)}

        if not target_operator:
            raise HttpError(422, "Operador inválido ou não informado.")
        with transaction.atomic():
            staff = StaffMember(
                id=uuid.uuid4(),
                operator=target_operator,
                name=payload.fullName.strip(),
                email=email,
                role=role,
                active=True,
            )
            staff.set_password(payload.password)
            staff.save()
        return {"success": True, "id": str(staff.id)}
    except HttpError:
        raise
    except IntegrityError:
        raise HttpError(409, "Não foi possível criar o usuário porque os dados já estão em uso.")
    except (ValueError, TypeError):
        raise HttpError(422, "Dados de usuário inválidos.")

@router.put("/users")
def update_user(request, payload: UserPayload):
    from accounts.models import StaffMember, PlatformAdmin
    from accounts.auth import require_role
    from logistics.models import ClientPortalUser
    from ninja.errors import HttpError

    if not payload.id:
        raise HttpError(422, "ID do usuário é obrigatório.")

    auth = getattr(request, "auth", None) or {}
    user_type = auth.get("user_type")
    client_id = auth.get("client_id")
    caller_role = str(auth.get("role", "")).lower()

    # 1. Se for usuário da loja (Lojista / Operador da Loja)
    if user_type == "client_portal_user" or client_id:
        target = ClientPortalUser.objects.filter(id=payload.id, client_id=client_id).first()
        if not target:
            raise HttpError(404, "Usuário da loja não encontrado.")

        is_self = str(auth.get("sub")) == payload.id
        if not is_self and caller_role not in ("lojista", "gestor", "gestor_loja"):
            raise HttpError(403, "Apenas o gestor da loja pode editar membros da equipe.")

        update_fields = []
        if payload.fullName:
            target.name = payload.fullName.strip()
            update_fields.append("name")
        if payload.email:
            email = payload.email.strip().lower()
            if _email_already_in_use(email, exclude_model=ClientPortalUser, exclude_id=target.pk):
                raise HttpError(409, "Já existe um usuário com este e-mail.")
            target.email = email
            update_fields.append("email")
        if payload.password and len(payload.password) >= 6:
            target.set_password(payload.password)
            update_fields.append("passwordHash")
        if payload.active is not None and not is_self and caller_role in ("lojista", "gestor", "gestor_loja"):
            target.active = payload.active
            update_fields.append("active")
        if payload.role and not is_self and caller_role in ("lojista", "gestor", "gestor_loja"):
            req_role = (payload.role or "").strip().lower()
            target.role = "lojista" if req_role in ("lojista", "gestor", "gestor_loja") else "operador_loja"
            update_fields.append("role")

        if update_fields:
            target.save(update_fields=update_fields)
        return {"success": True}

    # 2. Staff / PlatformAdmin
    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    is_platform_admin = bool(getattr(actor, "is_platform_admin", False))
    is_self = str(actor.id) == payload.id
    actor_role = getattr(actor, "role", None)
    can_manage = is_platform_admin or actor_role in {"ADMIN", "MANAGER"}
    if not is_self and not can_manage:
        raise HttpError(403, "Você só pode editar o próprio perfil.")

    staff_qs = StaffMember.objects.filter(id=payload.id)
    client_qs = ClientPortalUser.objects.filter(id=payload.id)
    if not is_platform_admin:
        staff_qs = staff_qs.filter(operator=actor.operator)
        client_qs = client_qs.filter(operator=actor.operator)

    target = staff_qs.first()
    target_kind = "staff"
    if not target:
        target = client_qs.first()
        target_kind = "client"
    if not target and is_platform_admin:
        target = PlatformAdmin.objects.filter(id=payload.id).first()
        target_kind = "platform"
    if not target:
        raise HttpError(404, "Usuário não encontrado.")

    target_role = getattr(target, "role", None)
    if actor_role == "MANAGER" and target_kind == "staff" and target_role in {"ADMIN", "MANAGER"} and not is_self:
        raise HttpError(403, "Gestores não podem editar usuários com nível igual ou superior.")
    if not is_self and not can_manage:
        raise HttpError(403, "Permissão insuficiente.")

    update_fields = []
    if payload.fullName:
        target.name = payload.fullName.strip()
        update_fields.append("name")
    if payload.email:
        email = payload.email.strip().lower()
        if _email_already_in_use(email, exclude_model=type(target), exclude_id=target.pk):
            raise HttpError(409, "Já existe um usuário com este e-mail.")
        target.email = email
        update_fields.append("email")
    if payload.password and len(payload.password) >= 6:
        target.set_password(payload.password)
        update_fields.append("passwordHash")
    if payload.role:
        if is_self:
            raise HttpError(403, "Não é permitido alterar o próprio papel.")
        role = _normalized_user_role(payload.role)
        if target_kind == "client" and isinstance(target, ClientPortalUser):
            target.role = "operador_loja" if role == "OPERADOR_LOJA" else "lojista"
            update_fields.append("role")
        elif target_kind == "staff" and isinstance(target, StaffMember):
            if role in {"LOJISTA", "OPERADOR_LOJA", "PLATFORM_ADMIN"}:
                raise HttpError(422, "A alteração solicitada não é compatível com este usuário.")
            if actor_role == "MANAGER" and role in {"ADMIN", "MANAGER"}:
                raise HttpError(403, "Gestores não podem conceder nível igual ou superior.")
            target.role = role
            update_fields.append("role")
    if payload.active is not None:
        if is_self:
            raise HttpError(403, "Não é permitido desativar o próprio acesso.")
        if target_kind == "platform":
            raise HttpError(422, "Administradores globais não podem ser desativados por esta rota.")
        setattr(target, "active", payload.active)
        update_fields.append("active")
    if update_fields:
        target.save(update_fields=update_fields)
    return {"success": True}

@router.delete("/users")
def delete_user(request, id: str):
    from accounts.models import StaffMember, PlatformAdmin
    from accounts.auth import require_role
    from logistics.models import ClientPortalUser
    from ninja.errors import HttpError

    auth = getattr(request, "auth", None) or {}
    user_type = auth.get("user_type")
    client_id = auth.get("client_id")
    caller_role = str(auth.get("role", "")).lower()

    if user_type == "client_portal_user" or client_id:
        if caller_role not in ("lojista", "gestor", "gestor_loja"):
            raise HttpError(403, "Apenas o gestor da loja pode desativar membros da equipe.")
        if str(auth.get("sub")) == id:
            raise HttpError(403, "Não é permitido desativar o próprio acesso.")
        user = ClientPortalUser.objects.filter(id=id, client_id=client_id).first()
        if not user:
            raise HttpError(404, "Usuário não encontrado.")
        user.active = False
        user.save(update_fields=["active"])
        return {"success": True}

    actor = require_role(["ADMIN", "MANAGER"])(request)
    if str(actor.id) == id:
        raise HttpError(403, "Não é permitido revogar o próprio acesso.")
    is_platform_admin = bool(getattr(actor, "is_platform_admin", False))
    actor_role = getattr(actor, "role", None)

    staff_qs = StaffMember.objects.filter(id=id)
    client_qs = ClientPortalUser.objects.filter(id=id)
    if not is_platform_admin:
        staff_qs = staff_qs.filter(operator=actor.operator)
        client_qs = client_qs.filter(operator=actor.operator)

    user = staff_qs.first()
    if user:
        if actor_role == "MANAGER" and getattr(user, "role", None) in {"ADMIN", "MANAGER"}:
            raise HttpError(403, "Gestores não podem revogar usuários com nível igual ou superior.")
        user.active = False
        user.save(update_fields=["active"])
        return {"success": True}

    user = client_qs.first()
    if user:
        user.active = False
        user.save(update_fields=["active"])
        return {"success": True}

    if is_platform_admin and PlatformAdmin.objects.filter(id=id).exists():
        raise HttpError(422, "Administradores globais devem ser removidos por um fluxo soberano auditado.")
    raise HttpError(404, "Usuário não encontrado.")

class CompanyDriverPayload(BaseModel):
    driver_id: Optional[str] = None
    driverId: Optional[str] = None
    company_id: Optional[Any] = None
    companyId: Optional[Any] = None
    active: Optional[bool] = None
    # Editable fields
    nome: Optional[str] = None
    telefone: Optional[str] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    pixKeyType: Optional[str] = None
    pixKey: Optional[str] = None
    maxActiveOrders: Optional[int] = None


class DriverTransferPayload(BaseModel):
    targetCompanyId: str
    reason: str


def _digits(value: Optional[str]) -> str:
    return "".join(char for char in (value or "") if char.isdigit())

@router.patch("/company-drivers")
def update_company_driver(request, payload: CompanyDriverPayload):
    from accounts.auth import require_role
    from logistics.models import Driver
    from ninja.errors import HttpError

    staff = require_role(["ADMIN", "MANAGER"])(request)
    try:
        d_id = payload.driver_id or payload.driverId
        if not d_id:
            raise HttpError(422, "driver_id é obrigatório")

        drivers = Driver.objects.filter(id=d_id)
        if not getattr(staff, "is_platform_admin", False):
            drivers = drivers.filter(operator_id=staff.operator_id)
        driver = drivers.get()
        update_fields = ["updatedAt"]
        if payload.active is not None:
            driver.active = payload.active
            update_fields.append("active")
        name_val = payload.nome
        if name_val:
            driver.name = name_val
            update_fields.append("name")
        phone_val = payload.telefone or payload.phone
        if phone_val:
            driver.phone = phone_val
            update_fields.append("phone")
        if payload.document is not None:
            driver.document = payload.document
            update_fields.append("document")
        if payload.pixKeyType is not None:
            driver.pixKeyType = payload.pixKeyType
            update_fields.append("pixKeyType")
        if payload.pixKey is not None:
            driver.pixKey = payload.pixKey
            update_fields.append("pixKey")
        if payload.maxActiveOrders is not None:
            driver.maxActiveOrders = payload.maxActiveOrders
            update_fields.append("maxActiveOrders")
        driver.save(update_fields=update_fields)
        return {"success": True}
    except Driver.DoesNotExist:
        raise HttpError(404, "Motoboy não encontrado")

@router.get("/company-drivers")
def get_company_drivers(request, company_id: Optional[str] = None, active_only: int = 0):
    from accounts.auth import require_role
    from ninja.errors import HttpError

    try:
        from django.core.exceptions import ValidationError
        from logistics.models import Driver, StoreDriver

        auth = getattr(request, "auth", None) or {}
        if auth.get("user_type") == "client_portal_user" or auth.get("client_id"):
            from accounts.auth import get_client_portal_user
            client_user = get_client_portal_user(request)
            if not client_user:
                raise HttpError(401, "Usuário lojista não autenticado.")
            if client_user.operator_id and client_user.client_id:
                allowed_drivers = StoreDriver.objects.filter(
                    operator_id=client_user.operator_id,
                    store__client_id=client_user.client_id,
                    store__operator_id=client_user.operator_id,
                ).values("driver_id")
                drivers = Driver.objects.filter(
                    operator_id=client_user.operator_id, id__in=allowed_drivers
                )
            else:
                drivers = Driver.objects.none()
        else:
            staff = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
            is_admin = getattr(staff, "is_platform_admin", False)
            auth_op_id = staff.operator_id

            if not is_admin and auth_op_id:
                drivers = Driver.objects.filter(operator_id=auth_op_id)
            elif company_id and company_id != "global":
                try:
                    drivers = Driver.objects.filter(operator_id=company_id)
                except (ValidationError, ValueError):
                    drivers = Driver.objects.none()
            elif is_admin:
                drivers = Driver.objects.all()
            else:
                drivers = Driver.objects.none()

        if active_only:
            drivers = drivers.filter(active=True)

        is_client = bool(auth.get("user_type") == "client_portal_user" or auth.get("client_id"))
        res = []
        for d in drivers.order_by("-createdAt"):
            res.append({
                "id": str(d.id),
                "driverId": str(d.id),
                "nome": d.name,
                "phone": d.phone,
                "telefone": d.phone,
                "document": "" if is_client else (d.document or ""),
                "placa": "",
                "modelo": "",
                "status": "Ativo" if d.active else "Inativo",
                "active": d.active,
                "maxActiveOrders": d.maxActiveOrders,
                "pixKeyType": None if is_client else d.pixKeyType,
                "pixKey": None if is_client else d.pixKey,
            })
        return res
    except HttpError:
        raise
    except Exception as cause:
        logger.exception("Falha ao consultar motoboys autorizados.")
        raise HttpError(503, "Não foi possível consultar os motoboys agora.") from cause


class DriverCreateSchema(BaseModel):
    companyId: Optional[str] = None
    storeId: Optional[str] = None
    nome: str
    phone: Optional[str] = None
    telefone: Optional[str] = None
    email: str
    password: Optional[str] = None
    document: Optional[str] = None
    rg: Optional[str] = None
    birthDate: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    vehicleType: Optional[str] = "MOTORCYCLE"
    placa: Optional[str] = None
    modelo: Optional[str] = None
    marca: Optional[str] = None
    ano: Optional[str] = None
    cor: Optional[str] = None
    cnhNumero: Optional[str] = None
    cnhCategoria: Optional[str] = "A"
    cnhValidade: Optional[str] = None
    cnhPrimeiraHabilitacao: Optional[str] = None
    pixKeyType: str = "TELEFONE"
    pixKey: str = ""
    maxActiveOrders: int = 3
    tax_classification: str = "PESSOA_FISICA_AUTONOMO"

@router.post("/company-drivers")
def create_company_driver(request, payload: DriverCreateSchema):
    """
    Cadastra um novo motoboy de forma 100% nativa sem dependência de Supabase Auth.
    Persiste o Driver, dados do Veículo e Documentação vinculados ao Operador.
    """
    from accounts.auth import require_role
    from accounts.models import Operator
    from logistics.models import Driver, Store, StoreDriver, Vehicle, DriverDocument
    from accounts.security import hash_password
    from django.core.exceptions import ValidationError
    from django.db import IntegrityError, transaction
    from ninja.errors import HttpError
    import uuid

    staff = require_role(["ADMIN", "MANAGER"])(request)

    company_id = payload.companyId
    nome = payload.nome
    phone = _digits(payload.phone or payload.telefone)
    document = _digits(payload.document)
    email = payload.email
    password = payload.password or ""
    
    if not all([nome, phone, email]):
        return {"success": False, "error": "Nome, telefone e e-mail são obrigatórios"}
    if len(password) < 10:
        raise HttpError(422, "A senha inicial deve possuir ao menos 10 caracteres.")
    
    try:
        operator = None
        if not getattr(staff, "is_platform_admin", False):
            operator = staff.operator
        elif company_id and company_id != "global":
            try:
                operator = Operator.objects.filter(id=company_id).first()
            except (ValidationError, ValueError):
                operator = None
        if not operator:
            raise HttpError(422, "Operador logístico obrigatório não identificado.")

        store = None
        if payload.storeId:
            try:
                store = Store.objects.filter(id=payload.storeId, operator_id=operator.id).first()
            except (ValidationError, ValueError):
                store = None
            if store is None:
                raise HttpError(422, "A loja selecionada não pertence ao operador do motoboy.")

        duplicate = Driver.objects.filter(active=True, phone=phone)
        if document:
            duplicate = duplicate | Driver.objects.filter(active=True, document=document)
        existing = duplicate.distinct().first()
        if existing:
            if existing.operator_id == operator.id:
                raise HttpError(409, "Este motoboy já está cadastrado neste operador.")
            raise HttpError(
                409,
                "Este motoboy já pertence a outro operador. Somente o proprietário da plataforma pode transferi-lo.",
            )

        with transaction.atomic():
            # O operador vem sempre da identidade autenticada; apenas o
            # proprietário da plataforma pode escolher outro tenant.
            driver = Driver.objects.create(
                id=uuid.uuid4(),
                operator=operator,
                supabase_uid=uuid.uuid4(),
                name=nome,
                phone=phone,
                document=document or None,
                pixKeyType=payload.pixKeyType or "TELEFONE",
                pixKey=payload.pixKey or phone,
                maxActiveOrders=payload.maxActiveOrders or 3,
                tax_classification=payload.tax_classification or "PESSOA_FISICA_AUTONOMO",
                passwordHash=hash_password(password),
                active=True
            )
        
        # 2. Se placa foi informada, registrar veículo
            if payload.placa:
                clean_plate = payload.placa.strip().upper()
                if Vehicle.objects.filter(plate=clean_plate).exclude(operator=operator).exists():
                    raise HttpError(409, "Este veículo já pertence a outro operador.")
                v_type = (payload.vehicleType or "MOTORCYCLE").upper()
                if v_type not in ["MOTORCYCLE", "BICYCLE", "CAR"]:
                    v_type = "MOTORCYCLE"
                Vehicle.objects.update_or_create(
                    plate=clean_plate,
                    operator=operator,
                    defaults={
                        "type": v_type,
                        "active": True
                    }
                )

        # 3. Se CNH foi informada, registrar DriverDocument
            if payload.cnhNumero:
                DriverDocument.objects.create(
                    id=uuid.uuid4(),
                    operator=operator,
                    driver=driver,
                    name=f"CNH {payload.cnhCategoria or 'A'} - {payload.cnhNumero}",
                    fileUrl="",
                    document_type="CNH",
                    status="APPROVED"
                )

        # 4. Vincular somente à loja selecionada explicitamente.
            if store:
                StoreDriver.objects.get_or_create(
                    operator=operator,
                    store=store,
                    driver=driver
                )
            
        return {"success": True, "driverId": str(driver.id)}
    except HttpError:
        raise
    except IntegrityError as exc:
        raise HttpError(409, "Já existe um motoboy ativo com esta identidade.") from exc
    except Exception:
        logger.exception("Falha inesperada ao cadastrar motoboy.")
        raise HttpError(500, "Não foi possível cadastrar o motoboy.")


@router.post("/company-drivers/{driver_id}/transfer")
def transfer_company_driver(request, driver_id: str, payload: DriverTransferPayload):
    """Transfere a identidade ativa sem reescrever o histórico do tenant antigo."""

    import json
    import uuid

    from accounts.auth import platform_owner_required
    from accounts.models import Operator, OperatorAuditLog
    from django.db import transaction
    from django.db.models import Q
    from logistics.models import Driver, StoreDriver
    from ninja.errors import HttpError

    platform_admin = platform_owner_required(request)
    reason = payload.reason.strip()
    if len(reason) < 10:
        raise HttpError(422, "Informe uma justificativa com ao menos 10 caracteres.")

    with transaction.atomic():
        source = Driver.objects.select_for_update().filter(id=driver_id, active=True).first()
        target = Operator.objects.select_for_update().filter(id=payload.targetCompanyId).first()
        if not source or not target:
            raise HttpError(404, "Motoboy ou operador de destino não encontrado.")
        if source.operator_id == target.id:
            raise HttpError(409, "O motoboy já pertence ao operador de destino.")

        from logistics.models import Order, ScheduleEntry
        from django.utils import timezone
        if Order.objects.filter(driver=source).exclude(
            status__in=["COMPLETED", "CANCELED", "RETURNED"]
        ).exists():
            raise HttpError(409, "Encerre ou reatribua as corridas abertas antes de transferir o motoboy.")
        if ScheduleEntry.objects.filter(driver=source, date__gte=timezone.localdate()).exists():
            raise HttpError(409, "Cancele ou reatribua as escalas futuras antes de transferir o motoboy.")

        identity_filter = Q(phone=source.phone)
        if source.document:
            identity_filter |= Q(document=source.document)
        collision = Driver.objects.filter(
            identity_filter, active=True, operator=target
        ).exists()
        if collision:
            raise HttpError(409, "Já existe uma identidade ativa deste motoboy no destino.")

        previous_operator_id = source.operator_id
        previous_driver_id = source.id
        original_uid = source.supabase_uid
        source.active = False
        source.online = False
        source.supabase_uid = None
        source.save(update_fields=["active", "online", "supabase_uid", "updatedAt"])
        StoreDriver.objects.filter(driver=source).delete()

        transferred = Driver.objects.create(
            id=uuid.uuid4(),
            operator=target,
            supabase_uid=original_uid,
            name=source.name,
            phone=source.phone,
            document=source.document,
            pixKeyType=source.pixKeyType,
            pixKey=source.pixKey,
            passwordHash=source.passwordHash,
            active=True,
            online=False,
            operational_status="OFFLINE",
            maxActiveOrders=source.maxActiveOrders,
            onboarding_status=source.onboarding_status,
            tax_classification=source.tax_classification,
        )

        OperatorAuditLog.objects.create(
            id=uuid.uuid4(),
            operator=target,
            platformAdmin=platform_admin,
            action="DRIVER_OPERATOR_TRANSFER",
            reason=json.dumps(
                {
                    "reason": reason,
                    "source_operator_id": str(previous_operator_id),
                    "target_operator_id": str(target.id),
                    "source_driver_id": str(previous_driver_id),
                    "target_driver_id": str(transferred.id),
                },
                ensure_ascii=False,
            ),
        )

    return {
        "success": True,
        "previousDriverId": str(previous_driver_id),
        "driverId": str(transferred.id),
        "operatorId": str(target.id),
    }

class StoreCreateSchema(BaseModel):
    companyId: Optional[str] = None
    name: str
    documento: Optional[str] = ""
    endereco: Optional[str] = ""
    telefone: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    averagePrepTimeMinutes: int = 15
    taxaCorridaPerEntrega: Optional[float] = 1.6
    pisoFixo: Optional[float] = 350.0
    diaria_weekday: Optional[float] = 60.0
    # Gestor da Loja (Lojista) opcional no cadastro
    managerName: Optional[str] = None
    managerEmail: Optional[str] = None
    managerPassword: Optional[str] = None
    managerPhone: Optional[str] = None

@router.post("/companies")
def create_company_store(request, payload: StoreCreateSchema):
    """
    Cadastra uma nova Empresa/Loja (Store) para o Operador logístico.
    Opcionalmente cadastra e vincula o usuário Gestor da Loja (Lojista).
    """
    from accounts.models import Operator
    from logistics.models import Client, Store, ClientPortalUser
    from finance.models import Contract
    from django.core.exceptions import ValidationError
    from django.contrib.gis.geos import Point
    from accounts.auth import require_role
    from django.db import transaction
    from ninja.errors import HttpError
    import uuid

    _ensure_database_schema()

    actor = require_role(["ADMIN", "MANAGER"])(request)
    operator = actor.operator
    if getattr(actor, "is_platform_admin", False):
        operator = _operator_from_company_reference(payload.companyId)
    if not operator:
        raise HttpError(422, "Operador logístico obrigatório não identificado.")

    name = payload.name
    if not name:
        raise HttpError(422, "Nome da empresa é obrigatório.")

    try:
        lat = payload.lat
        lng = payload.lng
        if lat is None or lng is None:
            # Fallback seguro caso geocodificação web não tenha retornado coordenadas
            lat = -19.9227
            lng = -43.9451
        else:
            try:
                lat = float(lat)
                lng = float(lng)
            except (ValueError, TypeError):
                lat = -19.9227
                lng = -43.9451

        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            lat = -19.9227
            lng = -43.9451

        manager_id = None
        if payload.managerEmail and payload.managerName:
            mgr_email = payload.managerEmail.strip().lower()
            if _email_already_in_use(mgr_email):
                raise HttpError(409, f"O e-mail '{mgr_email}' já está em uso por outro usuário.")
            pwd = payload.managerPassword or "Mudar@123456"
            if len(pwd) < 6:
                raise HttpError(422, "A senha do gestor da loja deve ter no mínimo 6 caracteres.")

        with transaction.atomic():
            client = Client.objects.create(
                id=uuid.uuid4(), operator=operator, name=name.strip(),
                document=payload.documento or "", active=True,
            )
            store = Store.objects.create(
                id=uuid.uuid4(), operator=operator, client=client, name=name.strip(),
                geom=Point(lng, lat, srid=4326),
                averagePrepTimeMinutes=payload.averagePrepTimeMinutes or 15,
                operational=True,
            )
            Contract.objects.create(
                operator=operator, store=store,
                compensationMode=Contract.CompensationMode.GARANTIDA,
                rideFeePerDeliveryCents=int((payload.taxaCorridaPerEntrega or 1.6) * 100),
                minimumRidesFeeFloorCents=int((payload.pisoFixo or 350.0) * 100),
                minimumFloorBps=0, adminTaxThresholdCents=0,
                adminTaxFixedAmountCents=0, adminTaxBps=0,
                dailyRateWeekdayCents=int((payload.diaria_weekday or 60.0) * 100),
            )

            if payload.managerEmail and payload.managerName:
                mgr_email = payload.managerEmail.strip().lower()
                pwd = payload.managerPassword or "Mudar@123456"
                manager_user = ClientPortalUser(
                    id=uuid.uuid4(),
                    supabase_uid=uuid.uuid4(),
                    operator=operator,
                    client=client,
                    name=payload.managerName.strip(),
                    email=mgr_email,
                    role="lojista",
                    active=True,
                )
                manager_user.set_password(pwd)
                manager_user.save()
                manager_id = str(manager_user.id)

        res = {"success": True, "storeId": str(store.id)}
        if manager_id:
            res["managerId"] = manager_id
        return res
    except HttpError:
        raise
    except (ValueError, TypeError) as e:
        logger.warning(f"Dados inválidos ao cadastrar loja: {e}")
        raise HttpError(422, f"Dados da loja são inválidos: {e}")
    except Exception as e:
        logger.exception(f"Erro inesperado ao cadastrar empresa/loja: {e}")
        raise HttpError(400, f"Falha ao cadastrar empresa: {str(e)}")
@router.get("/configs")
def get_configs(request, company_id: Optional[str] = None, company_name: Optional[str] = None):
    from accounts.auth import get_client_portal_user, require_role
    from finance.models import Contract
    from logistics.models import Store
    from ninja.errors import HttpError

    auth = getattr(request, "auth", None) or {}
    if auth.get("user_type") == "client_portal_user" or auth.get("client_id"):
        client_user = get_client_portal_user(request)
        if not client_user:
            raise HttpError(401, "Usuário lojista não autenticado.")
        op = client_user.operator
        if not op:
            raise HttpError(404, "Operador da loja não encontrado.")

        store = None
        if company_id and company_id not in ("global", "NaN", "undefined"):
            try:
                store = Store.objects.filter(client=client_user.client, id=company_id).first()
            except Exception:
                store = None
        if not store and client_user.client:
            store = Store.objects.filter(client=client_user.client).first()
        if not store:
            store = Store.objects.filter(operator=op).first()

        contract = Contract.objects.filter(store=store).first() if store else Contract.objects.filter(operator=op).first()

        ride_fee = (contract.rideFeePerDeliveryCents / 100.0) if contract and contract.rideFeePerDeliveryCents is not None else 1.6
        piso_floor = (contract.minimumRidesFeeFloorCents / 100.0) if contract and contract.minimumRidesFeeFloorCents is not None else 350.0
        diaria_wd = (contract.dailyRateWeekdayCents / 100.0) if contract and contract.dailyRateWeekdayCents is not None else 60.0
        diaria_sat = (contract.dailyRateSaturdayCents / 100.0) if contract and contract.dailyRateSaturdayCents is not None else 70.0
        diaria_sun = (contract.dailyRateSundayCents / 100.0) if contract and contract.dailyRateSundayCents is not None else 80.0
        diaria_hol = (contract.dailyRateHolidayCents / 100.0) if contract and contract.dailyRateHolidayCents is not None else 80.0
        taxa_sup = (contract.supervisionFeePerWeekCents / 100.0) if contract and contract.supervisionFeePerWeekCents is not None else 10.0
        guaranteed = contract.compensationMode in ("GARANTIDA", "GARANTIDA_HORAS") if contract else True
        retencao = (contract.returnFeeBps > 0) if contract and contract.returnFeeBps is not None else True

        c_id = str(store.id) if store else (str(client_user.client_id) if client_user.client_id else str(op.id))
        c_name = store.name if store else (client_user.client.name if client_user.client else op.name)

        return {
            "id": c_id,
            "nome": c_name,
            "company_id": c_id,
            "company_name": c_name,
            "ride_fee_per_delivery": ride_fee,
            "minimum_rides_fee_floor": piso_floor,
            "daily_rate_weekday": diaria_wd,
            "daily_rate_saturday": diaria_sat,
            "daily_rate_sunday": diaria_sun,
            "daily_rate_holiday": diaria_hol,
            "taxa_supervisao": taxa_sup,
            "debito_pendente": 0.0,
            "guaranteed_mode_enabled": guaranteed,
            "retencao_devolucao": retencao,
            "bloquear_fatura": True,
            "features": {},
        }

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    op = None
    is_admin = bool(getattr(actor, "is_platform_admin", False))

    if is_admin:
        op = _operator_from_company_reference(company_id)
        if not op and (not company_id or company_id in ("global", "NaN", "undefined")):
            # PlatformAdmin sem operador específico selecionado ou consultando global:
            # Retorna configurações padrão globais da plataforma (200 OK)
            return {
                "id": "global",
                "nome": "Administração Global",
                "company_id": "global",
                "company_name": "Administração Global",
                "ride_fee_per_delivery": 1.6,
                "minimum_rides_fee_floor": 350.0,
                "daily_rate_weekday": 60.0,
                "daily_rate_saturday": 70.0,
                "daily_rate_sunday": 80.0,
                "daily_rate_holiday": 80.0,
                "taxa_supervisao": 10.0,
                "debito_pendente": 0.0,
                "guaranteed_mode_enabled": True,
                "retencao_devolucao": True,
                "bloquear_fatura": True,
                "features": {},
            }
    else:
        op = getattr(actor, "operator", None)

    if not op:
        if is_admin:
            raise HttpError(404, "Operador não encontrado.")
        raise HttpError(422, "Selecione um operador válido.")

    store = None
    if company_id and company_id not in ("global", "NaN", "undefined"):
        try:
            store = Store.objects.filter(operator=op, id=company_id).first()
        except Exception:
            store = None
    if not store and company_name:
        store = Store.objects.filter(operator=op, name__iexact=company_name).first()
    if not store:
        store = Store.objects.filter(operator=op).first()

    contract = Contract.objects.filter(store=store).first() if store else Contract.objects.filter(operator=op).first()

    ride_fee = (contract.rideFeePerDeliveryCents / 100.0) if contract and contract.rideFeePerDeliveryCents is not None else 1.6
    piso_floor = (contract.minimumRidesFeeFloorCents / 100.0) if contract and contract.minimumRidesFeeFloorCents is not None else 350.0
    diaria_wd = (contract.dailyRateWeekdayCents / 100.0) if contract and contract.dailyRateWeekdayCents is not None else 60.0
    diaria_sat = (contract.dailyRateSaturdayCents / 100.0) if contract and contract.dailyRateSaturdayCents is not None else 70.0
    diaria_sun = (contract.dailyRateSundayCents / 100.0) if contract and contract.dailyRateSundayCents is not None else 80.0
    diaria_hol = (contract.dailyRateHolidayCents / 100.0) if contract and contract.dailyRateHolidayCents is not None else 80.0
    taxa_sup = (contract.supervisionFeePerWeekCents / 100.0) if contract and contract.supervisionFeePerWeekCents is not None else 10.0
    guaranteed = contract.compensationMode in ("GARANTIDA", "GARANTIDA_HORAS") if contract else True
    retencao = (contract.returnFeeBps > 0) if contract and contract.returnFeeBps is not None else True

    c_id = str(store.id) if store else str(op.id)
    c_name = store.name if store else op.name

    return {
        "id": c_id,
        "nome": c_name,
        "company_id": c_id,
        "company_name": c_name,
        "ride_fee_per_delivery": ride_fee,
        "minimum_rides_fee_floor": piso_floor,
        "daily_rate_weekday": diaria_wd,
        "daily_rate_saturday": diaria_sat,
        "daily_rate_sunday": diaria_sun,
        "daily_rate_holiday": diaria_hol,
        "taxa_supervisao": taxa_sup,
        "debito_pendente": 0.0,
        "guaranteed_mode_enabled": guaranteed,
        "retencao_devolucao": retencao,
        "bloquear_fatura": True,
        "features": {},
    }


def _save_configs_internal(request, payload: dict):
    from accounts.auth import get_client_portal_user, require_role
    from finance.models import Contract
    from logistics.models import Store
    from ninja.errors import HttpError
    from django.db import transaction

    auth = getattr(request, "auth", None) or {}
    company_id = payload.get("company_id") or payload.get("companyId") or payload.get("id")

    op = None
    store = None

    if auth.get("user_type") == "client_portal_user" or auth.get("client_id"):
        client_user = get_client_portal_user(request)
        if not client_user:
            raise HttpError(401, "Usuário lojista não autenticado.")
        op = client_user.operator
        if company_id and company_id not in ("global", "NaN", "undefined"):
            try:
                store = Store.objects.filter(client=client_user.client, id=company_id).first()
            except Exception:
                store = None
        if not store and client_user.client:
            store = Store.objects.filter(client=client_user.client).first()
    else:
        actor = require_role(["ADMIN", "MANAGER"])(request)
        is_admin = bool(getattr(actor, "is_platform_admin", False))
        if is_admin:
            op = _operator_from_company_reference(company_id) or actor.operator
        else:
            op = actor.operator
        if not op:
            raise HttpError(422, "Operador logístico obrigatório não identificado.")

        if company_id and company_id not in ("global", "NaN", "undefined"):
            try:
                store = Store.objects.filter(operator=op, id=company_id).first()
            except Exception:
                store = None
        if not store:
            store = Store.objects.filter(operator=op).first()

    if not op:
        raise HttpError(422, "Operador logístico não identificado.")

    with transaction.atomic():
        if not store:
            store = Store.objects.create(
                operator=op,
                name=op.name,
                geom="POINT(-43.9451 -19.9227)",
                operational=True,
            )

        existing_contract = Contract.objects.filter(store=store).first()

        def _resolve_val(explicit_val, alt_val, current_cents, hard_default):
            target = explicit_val if explicit_val is not None else alt_val
            if target is not None:
                try:
                    return round(float(target) * 100)
                except (ValueError, TypeError):
                    pass
            if current_cents is not None:
                return current_cents
            return round(float(hard_default) * 100)

        diaria_data = payload.get("diaria") if isinstance(payload.get("diaria"), dict) else {}

        ride_fee_cents = _resolve_val(
            payload.get("taxaCorridaPerEntrega"),
            payload.get("ride_fee_per_delivery"),
            getattr(existing_contract, "rideFeePerDeliveryCents", None),
            1.6,
        )
        piso_cents = _resolve_val(
            payload.get("pisoFixo"),
            payload.get("minimum_rides_fee_floor"),
            getattr(existing_contract, "minimumRidesFeeFloorCents", None),
            350.0,
        )
        piso_pct_bps = _resolve_val(
            payload.get("pisoPercentual"),
            payload.get("minimum_floor_percent"),
            getattr(existing_contract, "minimumFloorBps", None),
            0.0,
        )
        taxa_sup_cents = _resolve_val(
            payload.get("taxaSupervisao"),
            payload.get("taxa_supervisao"),
            getattr(existing_contract, "supervisionFeePerWeekCents", None),
            10.0,
        )
        diaria_wd_cents = _resolve_val(
            payload.get("diaria_weekday"),
            diaria_data.get("weekday") or payload.get("daily_rate_weekday"),
            getattr(existing_contract, "dailyRateWeekdayCents", None),
            60.0,
        )
        diaria_sat_cents = _resolve_val(
            payload.get("diaria_saturday"),
            diaria_data.get("saturday") or payload.get("daily_rate_saturday"),
            getattr(existing_contract, "dailyRateSaturdayCents", None),
            70.0,
        )
        diaria_sun_cents = _resolve_val(
            payload.get("diaria_sunday"),
            diaria_data.get("sunday") or payload.get("daily_rate_sunday"),
            getattr(existing_contract, "dailyRateSundayCents", None),
            80.0,
        )
        diaria_hol_cents = _resolve_val(
            payload.get("diaria_holiday"),
            diaria_data.get("holiday") or payload.get("daily_rate_holiday"),
            getattr(existing_contract, "dailyRateHolidayCents", None),
            80.0,
        )

        if "garantia_empresa" in payload:
            is_guaranteed = bool(payload["garantia_empresa"])
        elif "guaranteed_mode_enabled" in payload:
            is_guaranteed = bool(payload["guaranteed_mode_enabled"])
        elif existing_contract:
            is_guaranteed = existing_contract.compensationMode in (
                Contract.CompensationMode.GARANTIDA,
                Contract.CompensationMode.GARANTIDA_HORAS,
            )
        else:
            is_guaranteed = True

        mode = Contract.CompensationMode.GARANTIDA if is_guaranteed else Contract.CompensationMode.PRODUCAO

        if "retencao_devolucao" in payload:
            retencao_enabled = bool(payload["retencao_devolucao"])
        elif existing_contract:
            retencao_enabled = existing_contract.returnFeeBps > 0
        else:
            retencao_enabled = True

        defaults = {
            "operator": op,
            "compensationMode": mode,
            "rideFeePerDeliveryCents": ride_fee_cents,
            "minimumRidesFeeFloorCents": piso_cents,
            "minimumFloorBps": piso_pct_bps,
            "adminTaxThresholdCents": getattr(existing_contract, "adminTaxThresholdCents", 0) or 0,
            "adminTaxFixedAmountCents": getattr(existing_contract, "adminTaxFixedAmountCents", 0) or 0,
            "adminTaxBps": getattr(existing_contract, "adminTaxBps", 0) or 0,
            "supervisionFeePerWeekCents": taxa_sup_cents,
            "dailyRateWeekdayCents": diaria_wd_cents,
            "dailyRateSaturdayCents": diaria_sat_cents,
            "dailyRateSundayCents": diaria_sun_cents,
            "dailyRateHolidayCents": diaria_hol_cents,
            "returnFeeBps": 5000 if retencao_enabled else 0,
        }

        contract, _ = Contract.objects.update_or_create(store=store, defaults=defaults)

    return {
        "success": True,
        "message": "Configurações salvas com sucesso.",
        "id": str(store.id),
        "nome": store.name,
        "company_id": str(store.id),
        "company_name": store.name,
        "ride_fee_per_delivery": float(contract.rideFeePerDeliveryCents or 0) / 100.0,
        "minimum_rides_fee_floor": float(contract.minimumRidesFeeFloorCents or 0) / 100.0,
        "daily_rate_weekday": float(contract.dailyRateWeekdayCents or 0) / 100.0,
        "daily_rate_saturday": float(contract.dailyRateSaturdayCents or 0) / 100.0,
        "daily_rate_sunday": float(contract.dailyRateSundayCents or 0) / 100.0,
        "daily_rate_holiday": float(contract.dailyRateHolidayCents or 0) / 100.0,
        "taxa_supervisao": float(contract.supervisionFeePerWeekCents or 0) / 100.0,
        "debito_pendente": 0.0,
        "guaranteed_mode_enabled": contract.compensationMode in ("GARANTIDA", "GARANTIDA_HORAS"),
        "retencao_devolucao": contract.returnFeeBps > 0,
        "bloquear_fatura": True,
        "features": {},
    }


class ConfigUpdatePayload(BaseModel):
    company_id: Optional[str] = None
    companyId: Optional[str] = None
    id: Optional[str] = None
    taxaCorridaPerEntrega: Optional[float] = None
    ride_fee_per_delivery: Optional[float] = None
    pisoFixo: Optional[float] = None
    minimum_rides_fee_floor: Optional[float] = None
    pisoPercentual: Optional[float] = None
    minimum_floor_percent: Optional[float] = None
    taxaSupervisao: Optional[float] = None
    taxa_supervisao: Optional[float] = None
    diaria_weekday: Optional[float] = None
    diaria_saturday: Optional[float] = None
    diaria_sunday: Optional[float] = None
    diaria_holiday: Optional[float] = None
    daily_rate_weekday: Optional[float] = None
    daily_rate_saturday: Optional[float] = None
    daily_rate_sunday: Optional[float] = None
    daily_rate_holiday: Optional[float] = None
    diaria: Optional[Dict[str, Any]] = None
    garantia_empresa: Optional[bool] = None
    guaranteed_mode_enabled: Optional[bool] = None
    retencao_devolucao: Optional[bool] = None
    bloquear_fatura: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


@router.post("/configs")
def create_config(request, payload: ConfigUpdatePayload):
    payload_dict = payload.model_dump()
    return _save_configs_internal(request, payload_dict)


@router.put("/configs")
def update_config(request, payload: ConfigUpdatePayload):
    payload_dict = payload.model_dump()
    return _save_configs_internal(request, payload_dict)


@router.get("/snapshots")
def get_snapshots(request, company_id: Optional[str] = None, limit: int = 50):
    from accounts.auth import get_client_portal_user, get_staff_member
    from finance.models import WeeklyStoreInvoice
    from ninja.errors import HttpError

    staff = get_staff_member(request)
    client_user = None
    if not staff:
        try:
            client_user = get_client_portal_user(request)
        except Exception:
            client_user = None
    if not client_user and not staff:
        raise HttpError(401, "Autenticação obrigatória.")

    op = None
    target_store_ids = []

    if client_user:
        op = getattr(client_user, "operator", None)
        if getattr(client_user, "client_id", None):
            from logistics.models import Store
            target_store_ids = list(Store.objects.filter(client_id=client_user.client_id).values_list("id", flat=True))
    elif staff:
        is_platform_admin = getattr(staff, "is_platform_admin", False) is True
        if is_platform_admin and company_id and company_id not in ("global", "NaN", "undefined"):
            op = _operator_from_company_reference(company_id) or getattr(staff, "operator", None)
        else:
            op = getattr(staff, "operator", None)
            if not is_platform_admin and not op:
                raise HttpError(403, "Membro da equipe sem operador associado.")

    qs = WeeklyStoreInvoice.objects.select_related("store", "operator")
    if op:
        qs = qs.filter(operator=op)
    if client_user:
        qs = qs.filter(store_id__in=target_store_ids)
    elif company_id and company_id not in ("global", "NaN", "undefined"):
        try:
            qs = qs.filter(store_id=company_id)
        except Exception:
            pass

    qs = qs.order_by("-startDate")[:limit]

    invoices = list(qs)
    if not invoices:
        return []

    inv_ids = [inv.id for inv in invoices]

    from django.db.models import Count, Q
    from collections import defaultdict
    from finance.models import WeeklyInvoiceLineItem

    # Agregação em lote de corridas para eliminar consultas N+1
    line_item_stats = (
        WeeklyInvoiceLineItem.objects.filter(invoice_id__in=inv_ids)
        .values("invoice_id")
        .annotate(
            rides_count=Count("id", filter=Q(order_id__isnull=False)),
        )
    )
    rides_count_map = {item["invoice_id"]: item["rides_count"] for item in line_item_stats}

    driver_rows = (
        WeeklyInvoiceLineItem.objects.filter(invoice_id__in=inv_ids, driver_id__isnull=False)
        .values_list("invoice_id", "driver_id")
        .distinct()
    )
    driver_map = defaultdict(list)
    for inv_id, drv_id in driver_rows:
        driver_map[inv_id].append(str(drv_id))

    results = []
    for inv in invoices:
        driver_ids = driver_map.get(inv.id, [])
        rides_count = rides_count_map.get(inv.id, 0)
        total_liquido = round(float(inv.totalCents or 0) / 100.0, 2)

        start_str = inv.startDate.strftime("%d/%m") if inv.startDate else ""
        end_str = inv.endDate.strftime("%d/%m") if inv.endDate else ""
        week_label = f"Semana {start_str} a {end_str}" if start_str and end_str else f"Fatura #{inv.id}"

        status_lower = (inv.status or "draft").lower()
        if status_lower in ("finalized", "paid"):
            ui_status = "finalized"
        elif status_lower == "locked":
            ui_status = "locked"
        else:
            ui_status = "draft"

        results.append({
            "id": str(inv.id),
            "weekLabel": week_label,
            "weekStart": inv.startDate.isoformat() if inv.startDate else None,
            "weekEnd": inv.endDate.isoformat() if inv.endDate else None,
            "week_start": inv.startDate.isoformat() if inv.startDate else None,
            "week_end": inv.endDate.isoformat() if inv.endDate else None,
            "status": ui_status,
            "totalGeral": total_liquido,
            "total_liquido": total_liquido,
            "total_corridas": rides_count,
            "total_motoboys": len(driver_ids),
            "drivers": [str(d) for d in driver_ids if d],
            "pdfUrl": inv.pdfUrl,
            "pdf_url": inv.pdfUrl,
            "store_name": inv.store.name if inv.store else "",
            "company_id": str(inv.store_id) if inv.store_id else (str(inv.operator_id) if inv.operator_id else ""),
            "created_at": inv.createdAt.isoformat() if hasattr(inv, "createdAt") and inv.createdAt else None,
        })
    return results


@router.get("/positions")
def get_positions(request, max_age_minutes: int = 720, limit: int = 1000):
    from accounts.auth import get_staff_member, get_client_portal_user
    from config.redis_client import get_redis
    from django.utils import timezone as django_tz
    from ninja.errors import HttpError

    staff = get_staff_member(request)
    client_user = None
    if not staff:
        try:
            client_user = get_client_portal_user(request)
        except Exception:
            client_user = None
    if not staff and not client_user:
        raise HttpError(401, "Autenticação obrigatória.")

    operator_id = None
    if staff and staff.operator_id:
        operator_id = str(staff.operator_id)
        if getattr(staff, "is_platform_admin", False) is True:
            override_op = None
            if hasattr(request, "headers") and isinstance(request.headers, dict):
                override_op = request.headers.get("X-Operator-Id")
            if not override_op and hasattr(request, "GET") and isinstance(request.GET, dict):
                override_op = request.GET.get("operator_id") or request.GET.get("company_id")
            if override_op:
                operator_id = str(override_op)
    elif client_user and client_user.operator_id:
        operator_id = str(client_user.operator_id)

    if not operator_id or operator_id in ("global", "NaN", "undefined"):
        return {"positions": [], "source": "redis_live"}

    r = get_redis()
    geo_key = f"driver_positions:{operator_id}"
    try:
        drivers = r.zrange(geo_key, 0, limit - 1)
        positions = []
        if drivers:
            drv_strs = [
                drv.decode("utf-8") if isinstance(drv, bytes) else str(drv)
                for drv in drivers
            ]
            all_coords = r.geopos(geo_key, *drv_strs)
            now_iso = django_tz.now().isoformat()
            for drv_str, coords in zip(drv_strs, all_coords):
                if coords:
                    lng, lat = coords
                    positions.append({
                        "machine_condutor_id": drv_str,
                        "latitude": lat,
                        "longitude": lng,
                        "speed": 0,
                        "heading": 0,
                        "received_at": now_iso,
                    })
        return {"positions": positions, "source": "redis_live"}
    except Exception as e:
        logger.warning(f"Falha ao ler posições ao vivo do Redis: {e}")
        return {"positions": [], "source": "redis_live", "error": str(e)}


class StoreUpdateSchema(BaseModel):
    name: Optional[str] = None
    nome: Optional[str] = None
    documento: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    averagePrepTimeMinutes: Optional[int] = None
    status: Optional[str] = None
    ride_fee_per_delivery: Optional[float] = None
    rideFeePerDeliveryCents: Optional[int] = None
    minimum_rides_fee_floor: Optional[float] = None
    minimumRidesFeeFloorCents: Optional[int] = None
    daily_rate_weekday: Optional[float] = None
    dailyRateWeekdayCents: Optional[int] = None
    daily_rate_saturday: Optional[float] = None
    daily_rate_sunday: Optional[float] = None
    daily_rate_holiday: Optional[float] = None

@router.put('/companies/{company_id}')
def update_company_store(request, company_id: str, payload: StoreUpdateSchema):
    from django.contrib.gis.geos import Point
    from finance.models import Contract
    from accounts.auth import require_role
    from ninja.errors import HttpError

    actor = require_role(["ADMIN", "MANAGER"])(request)
    try:
        stores = Store.objects.filter(id=company_id)
        if not getattr(actor, "is_platform_admin", False):
            stores = stores.filter(operator=actor.operator)
        store = stores.get()
        store_name = payload.nome or payload.name
        if store_name is not None:
            store.name = store_name
        if payload.averagePrepTimeMinutes is not None:
            store.averagePrepTimeMinutes = payload.averagePrepTimeMinutes
        if payload.lat is not None and payload.lng is not None:
            store.geom = Point(payload.lng, payload.lat, srid=4326)
        if payload.status is not None:
            store.operational = payload.status == 'Ativo'
        store.save()
        
        if payload.documento is not None and store.client:
            store.client.document = payload.documento
            store.client.save()

        # Update contract if any fee provided
        contract = Contract.objects.filter(store=store).first()
        if not contract:
            contract = Contract(
                operator=store.operator, 
                store=store, 
                compensationMode=Contract.CompensationMode.GARANTIDA,
                rideFeePerDeliveryCents=160,
                minimumRidesFeeFloorCents=35000,
                minimumFloorBps=0,
                adminTaxThresholdCents=0,
                adminTaxFixedAmountCents=0,
                adminTaxBps=0,
                dailyRateWeekdayCents=6000
            )

        if payload.rideFeePerDeliveryCents is not None:
            contract.rideFeePerDeliveryCents = payload.rideFeePerDeliveryCents
        elif payload.ride_fee_per_delivery is not None:
            contract.rideFeePerDeliveryCents = int(payload.ride_fee_per_delivery * 100)

        if payload.minimumRidesFeeFloorCents is not None:
            contract.minimumRidesFeeFloorCents = payload.minimumRidesFeeFloorCents
        elif payload.minimum_rides_fee_floor is not None:
            contract.minimumRidesFeeFloorCents = int(payload.minimum_rides_fee_floor * 100)

        if payload.dailyRateWeekdayCents is not None:
            contract.dailyRateWeekdayCents = payload.dailyRateWeekdayCents
        elif payload.daily_rate_weekday is not None:
            contract.dailyRateWeekdayCents = int(payload.daily_rate_weekday * 100)

        if payload.daily_rate_saturday is not None:
            contract.dailyRateSaturdayCents = int(payload.daily_rate_saturday * 100)
        if payload.daily_rate_sunday is not None:
            contract.dailyRateSundayCents = int(payload.daily_rate_sunday * 100)
        if payload.daily_rate_holiday is not None:
            contract.dailyRateHolidayCents = int(payload.daily_rate_holiday * 100)

        contract.save()
            
        return {'success': True}
    except Store.DoesNotExist:
        raise HttpError(404, "Loja não encontrada.")
    except (ValueError, TypeError):
        raise HttpError(422, "Dados da loja são inválidos.")

@router.delete('/companies/{company_id}')
def delete_company_store(request, company_id: str):
    from accounts.auth import require_role
    from ninja.errors import HttpError
    from django.db import transaction

    actor = require_role(["ADMIN"])(request)
    stores = Store.objects.filter(id=company_id)
    if not getattr(actor, "is_platform_admin", False):
        stores = stores.filter(operator=actor.operator)
    store = stores.first()
    if not store:
        raise HttpError(404, "Loja não encontrada.")

    try:
        with transaction.atomic():
            client = store.client
            store_id = str(store.id)
            store_id_clean = store_id.replace("-", "")
            try:
                store.delete()
            except Exception as del_err:
                logger.warning(f"Fallback para exclusão direta de Store {store_id}: {del_err}")
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute('DELETE FROM "Store" WHERE id = %s OR id = %s', [store_id, store_id_clean])

            # Se o cliente não possuir mais lojas cadastradas, remove também o cliente e seus acessos de portal
            if client and not Store.objects.filter(client=client).exists():
                from logistics.models import ClientPortalUser
                client_id_str = str(client.id)
                client_id_clean = client_id_str.replace("-", "")
                try:
                    ClientPortalUser.objects.filter(client=client).delete()
                except Exception:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute('DELETE FROM "ClientPortalUser" WHERE client_id = %s OR client_id = %s', [client_id_str, client_id_clean])
                try:
                    client.delete()
                except Exception:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute('DELETE FROM "Client" WHERE id = %s OR id = %s', [client_id_str, client_id_clean])
    except Exception as e:
        logger.exception(f"Erro ao excluir loja {company_id}: {e}")
        raise HttpError(400, f"Não foi possível excluir a loja: {e}")

    return {'success': True}

# ==============================================================================
# UNIFIED NATIVE ORDERS API (Replaces Legacy Taxi Machine Proxy)
# ==============================================================================

from typing import Optional

class OrderStopSchema(BaseModel):
    endereco_parada: str
    bairro_parada: str
    cidade_parada: str
    estado_parada: str
    lat_parada: str
    lng_parada: str
    cep_parada: str = ""
    numero_parada: str = ""
    complemento_parada: str = ""
    nome_cliente_parada: str = ""
    telefone_cliente_parada: str = ""
    observacao_parada: str = ""

class OrderCreateSchema(BaseModel):
    empresa_id: str
    endereco_partida: str
    bairro_partida: str
    cidade_partida: str
    estado_partida: str
    lat_partida: str
    lng_partida: str
    cep_partida: str = ""
    numero_partida: str = ""
    complemento_partida: str = ""
    nome_cliente_partida: str = ""
    telefone_cliente_partida: str = ""
    observacao_partida: str = ""
    pontos: List[OrderStopSchema]
    forma_pagamento: str = "DINHEIRO"
    tipo_veiculo: str = "MOTO"
    valor_estimado: Optional[float] = None
    distancia_estimada: Optional[float] = None
    tempo_estimado: Optional[int] = None


def _orders_visible_to_request(request):
    from accounts.auth import get_client_portal_user, require_role
    from logistics.models import Order

    auth = getattr(request, "auth", None) or {}
    if auth.get("client_id") or auth.get("user_type") == "client_portal_user":
        client_user = get_client_portal_user(request)
        return Order.objects.filter(
            store__client_id=client_user.client_id,
            operator_id=client_user.operator_id,
            store__operator_id=client_user.operator_id,
        ) if client_user else Order.objects.none()
    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    orders = Order.objects.all()
    if not getattr(actor, "is_platform_admin", False):
        orders = orders.filter(operator=actor.operator)
    elif actor.operator_id:
        orders = orders.filter(operator_id=actor.operator_id)
    return orders


def _notice_orders(request):
    return _orders_visible_to_request(request).filter(status__in=["COMPLETED", "CANCELED", "RETURNED"])


@router.get("/order-notices")
def list_order_notices(request):
    from accounts.models import OrderNoticeRead
    from django.db.models import Exists, OuterRef, F
    from django.db.models.functions import Coalesce

    actor_id = request.auth["sub"]
    recent = _notice_orders(request).annotate(
        event_date=Coalesce("completedAt", "canceledAt", "requestedAt"),
        read=Exists(OrderNoticeRead.objects.filter(actor_id=actor_id, order_id=OuterRef("pk"))),
    ).order_by(F("event_date").desc(nulls_last=True), "-pk")[:30]
    return [
        {"id": str(order.id), "status": order.status, "read": order.read,
         "date": order.event_date.isoformat() if order.event_date else None}
        for order in recent
    ]


@router.post("/order-notices/{order_id}/read")
def read_order_notice(request, order_id: str):
    from uuid import UUID
    from accounts.models import OrderNoticeRead
    from ninja.errors import HttpError

    try:
        order = get_object_or_404(_notice_orders(request), pk=UUID(order_id))
    except ValueError as exc:
        raise HttpError(404, "Notificação não encontrada.") from exc
    OrderNoticeRead.objects.get_or_create(actor_id=request.auth["sub"], order_id=order.id)
    return {"success": True}

@router.get("/orders")
def get_orders(
    request,
    empresa_id: Optional[str] = None,
    limite: int = 500,
    status_solicitacao: Optional[str] = None,
    data_hora_solicitacao_min: Optional[str] = None,
    data_hora_solicitacao_max: Optional[str] = None
):
    from logistics.models import Order
    from accounts.models import Operator
    from django.core.exceptions import ValidationError

    qs = _orders_visible_to_request(request).select_related('driver', 'store').order_by("-requestedAt")
    auth = getattr(request, "auth", None) or {}
    if auth.get("is_platform_admin") and empresa_id and empresa_id != "global":
        qs = qs.filter(operator_id=empresa_id)
        
    if status_solicitacao:
        status_map = {
            "F": Order.OrderStatus.COMPLETED,
            "C": Order.OrderStatus.CANCELED,
            "A": Order.OrderStatus.ACCEPTED,
            "E": Order.OrderStatus.STARTED
        }
        mapped_status = status_map.get(status_solicitacao)
        if mapped_status:
            qs = qs.filter(status=mapped_status)
            
    if data_hora_solicitacao_min:
        qs = qs.filter(requestedAt__gte=data_hora_solicitacao_min)
    if data_hora_solicitacao_max:
        qs = qs.filter(requestedAt__lte=data_hora_solicitacao_max)
        
    orders = qs[:limite]
    
    res = []
    for o in orders:
        try:
            drv_name = "Não atribuído"
            try:
                if o.driver_id and hasattr(o, 'driver') and o.driver:
                    drv_name = o.driver.name
            except Exception:
                pass
                
            store_name = "Expresso Neves"
            try:
                if o.store_id and hasattr(o, 'store') and o.store:
                    store_name = o.store.name
            except Exception:
                pass
                
            formatted_date = o.requestedAt.strftime("%Y-%m-%d %H:%M:%S") if getattr(o, 'requestedAt', None) and hasattr(o.requestedAt, 'strftime') else str(getattr(o, 'requestedAt', ''))
                
            res.append({
                "id": str(o.id),
                "driver_id": str(o.driver_id) if o.driver_id else None,
                "motorista": drv_name,
                "motoboy": drv_name,
                "empresa": store_name,
                "loja": store_name,
                "store_id": str(o.store_id) if o.store_id else "",
                "status": o.status,
                "price": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
                "valor_total": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
                "distance": (o.distanceMeters or 0) / 1000.0 if hasattr(o, 'distanceMeters') else 0,
                "data": formatted_date,
                "data_hora_solicitacao": formatted_date,
            })
        except Exception:
            continue
            
    return res

@router.post("/orders/create")
def create_order(request, payload: OrderCreateSchema):
    from logistics.models import Order, Stop, Store
    from django.contrib.gis.geos import Point
    from accounts.auth import get_client_portal_user, require_role
    from django.utils import timezone
    from django.db import transaction
    from finance.business_date import resolve_store_business_date
    from logistics.pricing import parse_coordinate, price_route_with_method
    from ninja.errors import HttpError
    
    auth = getattr(request, "auth", None) or {}
    if not payload.pontos or len(payload.pontos) == 0:
        raise HttpError(422, "Ao menos um ponto de entrega deve ser informado.")

    stores = Store.objects.filter(id=payload.empresa_id, operational=True)
    if auth.get("client_id") or auth.get("user_type") == "client_portal_user":
        client_user = get_client_portal_user(request)
        if not client_user:
            raise HttpError(401, "Usuário lojista não autenticado.")
        stores = stores.filter(client=client_user.client, operator=client_user.operator)
    else:
        actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
        if not getattr(actor, "is_platform_admin", False):
            stores = stores.filter(operator=actor.operator)
    store = stores.select_related("operator").first()
    if not store:
        raise HttpError(404, "Loja não encontrada no escopo autenticado.")

    def coordinates(lat_value, lng_value, prefix):
        lat = parse_coordinate(
            lat_value, field_name=f"{prefix}.latitude", minimum=-90, maximum=90
        )
        lng = parse_coordinate(
            lng_value, field_name=f"{prefix}.longitude", minimum=-180, maximum=180
        )
        return lat, lng

    def point(parsed_coordinates):
        lat, lng = parsed_coordinates
        return Point(lng, lat, srid=4326)

    try:
        pickup_coordinates = coordinates(
            payload.lat_partida, payload.lng_partida, "origem"
        )
        stop_coordinates = [
            coordinates(stop.lat_parada, stop.lng_parada, f"parada_{index}")
            for index, stop in enumerate(payload.pontos, start=1)
        ]
        distance_km, fare_cents, distance_method = price_route_with_method(
            store, [pickup_coordinates, *stop_coordinates]
        )
        with transaction.atomic():
            order = Order.objects.create(
                operator=store.operator,
                store=store,
                businessDate=resolve_store_business_date(store),
                status=Order.OrderStatus.OFFERED,
                fareValueCents=fare_cents,
                distanceMeters=int(distance_km * 1000),
                metadata={"distance_method": distance_method},
            )
            
            # Origin Stop
            Stop.objects.create(
                operator=store.operator,
                order=order,
                sequence=0,
                type=Stop.StopType.PICKUP,
                geom=point(pickup_coordinates),
                metadata={
                    "address": f"{payload.endereco_partida or ''}, {payload.numero_partida or ''} - {payload.bairro_partida or ''}",
                    "contact_name": payload.nome_cliente_partida or "Origem",
                    "contact_phone": payload.telefone_cliente_partida or "",
                },
            )
            
            # Destinations
            for idx, (stop, stop_coordinate) in enumerate(
                zip(payload.pontos, stop_coordinates), start=1
            ):
                Stop.objects.create(
                    operator=store.operator,
                    order=order,
                    sequence=idx,
                    type=Stop.StopType.DROPOFF,
                    geom=point(stop_coordinate),
                    metadata={
                        "address": f"{stop.endereco_parada or ''}, {stop.numero_parada or ''} - {stop.bairro_parada or ''}",
                        "contact_name": stop.nome_cliente_parada or "Destino",
                        "contact_phone": stop.telefone_cliente_parada or "",
                    },
                )
                
            return {"sucesso": True, "solicitacao_id": str(order.id), "msg": "Pedido criado localmente com sucesso"}
    except (ValueError, TypeError) as exc:
        raise HttpError(422, str(exc) or "Coordenadas ou preço inválidos.") from exc

class OrderCancelPayload(BaseModel):
    solicitacao_id: Optional[str] = None
    id_mch: Optional[str] = None
    motivo_id: Optional[int] = None

@router.post("/orders/cancel")
def cancel_order(request, payload: OrderCancelPayload):
    from logistics.models import Order
    from ninja.errors import HttpError
    order_id = payload.solicitacao_id or payload.id_mch
    if not order_id:
        raise HttpError(422, "ID da corrida obrigatório.")
    order = _orders_visible_to_request(request).filter(id=order_id).first()
    if not order:
        raise HttpError(404, "Corrida não encontrada.")
    order.status = Order.OrderStatus.CANCELED
    order.save()
    return {"sucesso": True, "msg": "Cancelado com sucesso"}

@router.get("/orders/estimate")
def estimate_order(
    request,
    empresa_id: str,
    lat_partida: str,
    lng_partida: str,
    lat_desejado: str,
    lng_desejado: str,
):
    from accounts.auth import get_client_portal_user, require_role
    from logistics.models import Store
    from logistics.pricing import parse_coordinate, price_route_with_method
    from ninja.errors import HttpError

    stores = Store.objects.filter(id=empresa_id, operational=True)
    auth = getattr(request, "auth", None) or {}
    if auth.get("client_id") or auth.get("user_type") == "client_portal_user":
        client_user = get_client_portal_user(request)
        if not client_user:
            raise HttpError(401, "Usuário do portal do cliente não identificado.")
        stores = stores.filter(
            client=client_user.client, operator=client_user.operator
        )
    else:
        actor = require_role(
            ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"]
        )(request)
        if not getattr(actor, "is_platform_admin", False):
            stores = stores.filter(operator=actor.operator)
    store = stores.first()
    if not store:
        raise HttpError(404, "Loja não encontrada no escopo autenticado.")

    try:
        pickup = (
            parse_coordinate(
                lat_partida, field_name="lat_partida", minimum=-90, maximum=90
            ),
            parse_coordinate(
                lng_partida, field_name="lng_partida", minimum=-180, maximum=180
            ),
        )
        destination = (
            parse_coordinate(
                lat_desejado, field_name="lat_desejado", minimum=-90, maximum=90
            ),
            parse_coordinate(
                lng_desejado, field_name="lng_desejado", minimum=-180, maximum=180
            ),
        )
        distance_km, fare_cents, distance_method = price_route_with_method(
            store, [pickup, destination]
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc

    return {
        "response": {
            "distancia": round(distance_km, 2),
            "valor": fare_cents / 100,
            "metodo_distancia": distance_method,
        }
    }

@router.get("/orders/tracking")
def get_order_tracking(request, id_mch: str):
    from ninja.errors import HttpError
    order = _orders_visible_to_request(request).filter(id=id_mch).first()
    if not order:
        raise HttpError(404, "Corrida não encontrada para rastreamento.")
    tracking_url = f"/rastreio/{order.id}"
    return {
        "success": True, "order_id": str(order.id), "status": order.status,
        "response": [{"link_rastreio": tracking_url}],
        "links": [{"link_rastreio": tracking_url}],
    }

@router.get("/orders/receipt")
def get_order_receipt(request, solicitacao_id: str):
    from logistics.models import Stop
    from ninja.errors import HttpError
    order = _orders_visible_to_request(request).select_related("store", "operator").filter(id=solicitacao_id).first()
    if not order:
        raise HttpError(404, "Recibo não encontrado.")
    stops = []
    for stop in Stop.objects.filter(order=order).order_by("sequence"):
        metadata = stop.metadata or {}
        stops.append({
            "sequence": stop.sequence, "type": stop.type,
            "address": metadata.get("address", ""),
            "contactName": metadata.get("contact_name", ""),
            "contactPhone": metadata.get("contact_phone", ""),
        })
    return {
            "id": str(order.id),
            "status": order.status,
            "empresa": order.store.name if order.store else (order.operator.name if order.operator else "Expresso Neves"),
            "data": order.createdAt.strftime("%d/%m/%Y %H:%M:%S") if getattr(order, "createdAt", None) else None,
            "valor_total": float(order.fareValueCents or 0) / 100.0,
            "distancia_km": float(order.distanceMeters or 0) / 1000.0,
            "paradas": stops,
    }

class CreditEntryPayload(BaseModel):
    companyId: Optional[Any] = None
    driverId: Optional[Any] = None
    date: Optional[str] = None
    amount: Optional[float] = 0.0
    breakdown: Optional[dict] = None
    status: Optional[str] = "COMPLETED"
    machineResponse: Optional[dict] = None
    error: Optional[str] = None
    processedBy: Optional[str] = None

@router.post("/entries/credit")
def save_credit_entry(request, payload: CreditEntryPayload):
    from finance.models import DailyCreditCalculation
    from accounts.models import Operator
    from logistics.models import Driver, Store
    from django.utils import timezone
    from accounts.auth import require_role
    from ninja.errors import HttpError
    import datetime

    actor = require_role(["ADMIN", "MANAGER"])(request)
    operator = actor.operator
    if getattr(actor, "is_platform_admin", False):
        operator = _operator_from_company_reference(str(payload.companyId) if payload.companyId else None)
    if not operator:
        raise HttpError(422, "Selecione um operador válido.")

    driver = Driver.objects.filter(id=payload.driverId, operator=operator).first() if payload.driverId else None
    if not driver:
        raise HttpError(404, "Motoboy não encontrado neste operador.")

    store = None
    if operator:
        store = Store.objects.filter(operator=operator).first()

    calc_date = timezone.now().date()
    if payload.date:
        try:
            calc_date = datetime.datetime.strptime(payload.date, "%Y-%m-%d").date()
        except ValueError:
            raise HttpError(422, "Data inválida; use AAAA-MM-DD.")

    amount_cents = int((payload.amount or 0) * 100)
    status_mapped = DailyCreditCalculation.CreditStatus.CREDITED if payload.status in ["COMPLETED", "CREDITED"] else DailyCreditCalculation.CreditStatus.PENDING

    if not store:
        raise HttpError(422, "O operador não possui loja para associar ao crédito.")
    entry = DailyCreditCalculation.objects.create(
            operator=operator,
            driver=driver,
            store=store,
            date=calc_date,
            status=status_mapped,
            netAmountCents=amount_cents,
            productionValueCents=amount_cents,
            failReason=payload.error,
    )
    return {"success": True, "id": str(entry.id)}

@router.get("/credit-queue")
def get_credit_queue(request, company_id: Optional[str] = None, status: Optional[str] = None):
    from finance.models import DailyCreditCalculation
    from accounts.auth import require_role
    from django.core.exceptions import ValidationError
    import uuid

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    qs = DailyCreditCalculation.objects.select_related("driver", "operator", "store").all()
    if not getattr(actor, "is_platform_admin", False):
        if getattr(actor, "operator", None):
            qs = qs.filter(operator=actor.operator)
        elif getattr(actor, "operator_id", None):
            qs = qs.filter(operator_id=actor.operator_id)
    elif company_id and company_id not in ("global", "NaN", "undefined"):
        try:
            op_uuid = uuid.UUID(company_id)
            qs = qs.filter(operator_id=op_uuid)
        except (ValidationError, ValueError, TypeError):
            pass

    if status:
        status_list = [s.strip().upper() for s in status.split(",")]
        mapped = set()
        for s in status_list:
            if s in ("ACTIVE", "PENDING"):
                mapped.add("PENDING")
            elif s in ("DEAD", "FAILED"):
                mapped.add("FAILED")
            elif s in ("CREDITED", "SKIPPED"):
                mapped.add(s)
            elif s == "PROCESSING":
                mapped.add("PENDING")
        if mapped:
            qs = qs.filter(status__in=list(mapped))

    items = []
    for item in qs[:100]:
        items.append({
            "id": str(item.id),
            "company_id": str(item.operator_id),
            "driver_id": str(item.driver_id),
            "machine_condutor_id": str(item.driver_id),
            "net_amount": float(item.netAmountCents or 0) / 100.0,
            "description": f"Crédito diário {item.date}",
            "status": item.status.lower() if item.status != "FAILED" else "dead",
            "attempt_count": 1,
            "max_attempts": 3,
            "last_error": item.failReason,
            "next_retry_at": item.updatedAt.isoformat() if getattr(item, "updatedAt", None) else "",
            "created_at": item.createdAt.isoformat() if getattr(item, "createdAt", None) else "",
            "updated_at": item.updatedAt.isoformat() if getattr(item, "updatedAt", None) else "",
            "completed_at": item.updatedAt.isoformat() if item.status == "CREDITED" else None,
            "driver_name": item.driver.name if item.driver else "Entregador",
            "company_name": item.operator.name if item.operator else "Operador",
        })
    return {"items": items}

class CreditQueueRetryPayload(BaseModel):
    queue_ids: List[str]

@router.post("/credit-queue/retry")
def retry_credit_queue(request, payload: CreditQueueRetryPayload):
    from finance.models import DailyCreditCalculation
    from accounts.auth import require_role

    actor = require_role(["ADMIN", "MANAGER"])(request)
    calculations = DailyCreditCalculation.objects.filter(id__in=payload.queue_ids)
    if not getattr(actor, "is_platform_admin", False):
        calculations = calculations.filter(operator=actor.operator)
    retried = calculations.update(
        status=DailyCreditCalculation.CreditStatus.PENDING,
        failReason=None
    )
    return {"success": True, "retried": retried}


class ProcessCreditsPayload(BaseModel):
    company_id: Optional[str] = None
    date: Optional[str] = None


@router.get("/operator/credit-stats")
def get_operator_credit_stats(
    request,
    company_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    from finance.models import DailyCreditCalculation
    from accounts.auth import require_role
    from django.db.models import Sum
    import uuid

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    qs = DailyCreditCalculation.objects.all()
    if not getattr(actor, "is_platform_admin", False):
        if getattr(actor, "operator", None):
            qs = qs.filter(operator=actor.operator)
        elif getattr(actor, "operator_id", None):
            qs = qs.filter(operator_id=actor.operator_id)
    elif company_id and company_id not in ("global", "NaN", "undefined"):
        try:
            op_uuid = uuid.UUID(company_id)
            qs = qs.filter(operator_id=op_uuid)
        except Exception:
            pass

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    total = qs.count()
    pending = qs.filter(status__in=[DailyCreditCalculation.CreditStatus.PENDING, "PROCESSING"]).count()
    credited = qs.filter(status=DailyCreditCalculation.CreditStatus.CREDITED).count()
    failed = qs.filter(status=DailyCreditCalculation.CreditStatus.FAILED).count()
    credited_cents = qs.filter(status=DailyCreditCalculation.CreditStatus.CREDITED).aggregate(s=Sum("netAmountCents"))["s"] or 0

    return {
        "total": total,
        "pending": pending,
        "credited": credited,
        "failed": failed,
        "credited_reais": round(credited_cents / 100.0, 2),
    }


@router.post("/operator/process-credits")
def process_operator_credits(request, payload: Optional[ProcessCreditsPayload] = None):
    from finance.models import DailyCreditCalculation
    from accounts.auth import require_role
    from finance.tasks import compute_daily_credit
    from typing import Any, cast

    actor = require_role(["ADMIN", "MANAGER"])(request)
    target_op_id = None
    if not getattr(actor, "is_platform_admin", False):
        target_op_id = getattr(actor, "operator_id", None)
    elif payload and payload.company_id and payload.company_id not in ("global", "NaN", "undefined"):
        target_op_id = payload.company_id

    try:
        cast(Any, compute_daily_credit)(target_cutoff_hour=None)
    except Exception as e:
        logger.error(f"Erro ao computar créditos diários: {e}")

    qs = DailyCreditCalculation.objects.select_related("driver", "store").all()
    if target_op_id:
        qs = qs.filter(operator_id=target_op_id)
    if payload and payload.date:
        qs = qs.filter(date=payload.date)

    results = []
    credited_count = 0
    skipped_count = 0
    failed_count = 0

    for item in qs.order_by("-updatedAt")[:50]:
        drv_name = item.driver.name if (item.driver and item.driver.name) else "Entregador"
        amt = float(item.netAmountCents or 0) / 100.0
        if item.status == DailyCreditCalculation.CreditStatus.CREDITED:
            credited_count += 1
            results.append({"driver": drv_name, "amount": amt, "status": "credited", "reason": None})
        elif item.status == DailyCreditCalculation.CreditStatus.SKIPPED:
            skipped_count += 1
            results.append({"driver": drv_name, "amount": amt, "status": "skipped", "reason": item.failReason or "sem pendência"})
        elif item.status == DailyCreditCalculation.CreditStatus.FAILED:
            failed_count += 1
            results.append({"driver": drv_name, "amount": amt, "status": "failed", "reason": item.failReason or "falha"})
        else:
            results.append({"driver": drv_name, "amount": amt, "status": "pending", "reason": "em processamento"})

    return {
        "success": True,
        "total_processed": len(results),
        "credited": credited_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "results": results,
    }


@router.get("/driver-balance")
def get_driver_balance(request, driver_id: Optional[str] = None, condutor_id: Optional[str] = None):
    from finance.models import Wallet
    from logistics.models import Driver
    from accounts.auth import require_role
    from ninja.errors import HttpError

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    d_id = driver_id or condutor_id
    if not d_id:
        raise HttpError(422, "Motoboy é obrigatório.")
    from django.core.exceptions import ValidationError
    try:
        drivers = Driver.objects.filter(id=d_id)
        if not getattr(actor, "is_platform_admin", False):
            drivers = drivers.filter(operator=actor.operator)
        if not drivers.exists():
            raise HttpError(404, "Motoboy não encontrado.")
    except (ValidationError, ValueError, TypeError):
        raise HttpError(404, "Motoboy não encontrado.")
    driver = drivers.first()
    if not driver:
        raise HttpError(404, "Motoboy não encontrado.")
    try:
        w = Wallet.objects.get(driver_id=d_id, operator_id=driver.operator_id)
        return {"saldo": w.balanceCents / 100.0}
    except Wallet.DoesNotExist:
        return {"saldo": 0.0}

# ==============================================================================
# MOTOR CONTÁBIL & FINANCEIRO — CRÉDITOS, RECARGAS, EXTRATO & SALDO DAS LOJAS
# ==============================================================================

def compute_store_balance(store):
    from finance.models import ManualEntry, WeeklyStoreInvoice
    from logistics.models import Order
    from django.db.models import Sum

    approved_credits = ManualEntry.objects.filter(
        store_id=store.id, status="APPROVED", amountCents__gt=0
    ).aggregate(s=Sum("amountCents"))["s"] or 0

    paid_invoices = WeeklyStoreInvoice.objects.filter(
        store_id=store.id, status="PAID"
    ).aggregate(s=Sum("totalCents"))["s"] or 0

    completed_orders_debit = Order.objects.filter(
        store_id=store.id, status="COMPLETED"
    ).aggregate(s=Sum("fareValueCents"))["s"] or 0

    manual_debits = ManualEntry.objects.filter(
        store_id=store.id, status="APPROVED", amountCents__lt=0
    ).aggregate(s=Sum("amountCents"))["s"] or 0

    total_credits = approved_credits + paid_invoices
    total_debits = completed_orders_debit + abs(manual_debits)
    balance_cents = total_credits - total_debits

    status = "DISPONIVEL" if balance_cents > 0 else ("ZERADO" if balance_cents == 0 else "DEVEDOR")

    client_name = ""
    if getattr(store, "client_id", None):
        try:
            client_name = store.client.name if store.client else ""
        except Exception:
            client_name = ""

    return {
        "store_id": str(store.id),
        "store_name": store.name,
        "client_name": client_name,
        "billing_mode": "PRE_PAGO",
        "balance_cents": balance_cents,
        "balance_reais": round(balance_cents / 100.0, 2),
        "status": status,
        "total_credits_cents": total_credits,
        "total_debits_cents": total_debits,
        "credit_limit_cents": 0,
    }


def _stores_visible_to_request(request):
    from accounts.auth import get_client_portal_user, require_role
    from logistics.models import Store

    auth = getattr(request, "auth", None) or {}
    client_user = get_client_portal_user(request)
    if client_user or auth.get("client_id") or auth.get("user_type") == "client_portal_user" or auth.get("role") == "lojista":
        if not client_user:
            client_user = get_client_portal_user(request)
        if client_user:
            qs = Store.objects.filter(client_id=client_user.client_id)
            if not qs.exists() and client_user.operator_id:
                qs = Store.objects.filter(operator_id=client_user.operator_id)
            return qs
        return Store.objects.none()

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    stores = Store.objects.all()
    if not getattr(actor, "is_platform_admin", False):
        stores = stores.filter(operator=actor.operator)
    elif actor.operator_id:
        stores = stores.filter(operator_id=actor.operator_id)
    return stores

@router.get("/client/balance")
def get_client_balance(request, store_id: Optional[str] = None):
    from logistics.models import Store

    stores = _stores_visible_to_request(request).select_related("client", "operator")
    if store_id:
        stores = stores.filter(id=store_id)
    store = stores.first()

    if not store:
        return {
            "store_id": "",
            "store_name": "Nenhuma loja vinculada",
            "client_name": "",
            "billing_mode": "PRE_PAGO",
            "balance_cents": 0,
            "balance_reais": 0.0,
            "status": "ZERADO",
            "total_credits_cents": 0,
            "total_debits_cents": 0,
            "credit_limit_cents": 0,
        }

    return compute_store_balance(store)

class ClientRechargePayload(BaseModel):
    store_id: Optional[str] = None
    amount_cents: int

@router.post("/client/recharge")
def client_recharge(request, payload: ClientRechargePayload):
    from django.conf import settings
    from logistics.models import Store
    from finance.models import WeeklyStoreInvoice
    from django.utils import timezone
    from datetime import timedelta
    import uuid

    if not settings.ALLOW_PAYMENT_SIMULATION:
        from ninja.errors import HttpError
        raise HttpError(
            503,
            "Recarga PIX indisponível até a ativação do provedor de cobrança homologado.",
        )

    if payload.amount_cents < 1000:
        return {"success": False, "error": "Valor mínimo para recarga é R$ 10,00"}

    stores = _stores_visible_to_request(request).select_related("operator")
    if payload.store_id:
        stores = stores.filter(id=payload.store_id)
    store = stores.first()
    if not store:
        return {"success": False, "error": "Nenhuma loja encontrada para a recarga"}

    reais = round(payload.amount_cents / 100.0, 2)
    today = timezone.now().date()
    recharge_id = uuid.uuid4()
    pix_code = f"00020126580014br.gov.bcb.pix01363598698000012852040000530398654{reais:.2f}5802BR5914EXPRESSO NEVES6008BRASILIA62070503{str(recharge_id)[:8]}6304ABCD"

    invoice = WeeklyStoreInvoice.objects.create(
        id=recharge_id,
        operator=store.operator,
        store=store,
        startDate=today,
        endDate=today,
        totalNetProducaoCents=0,
        totalNetGarantidaCents=0,
        administrativeFeeCents=0,
        supervisionFeeCents=0,
        pendingDebitCarriedCents=0,
        totalCents=payload.amount_cents,
        status=WeeklyStoreInvoice.InvoiceStatus.DRAFT,
        pixCopyPaste=pix_code,
        barcode="",
    )

    return {
        "success": True,
        "recharge_id": str(invoice.id),
        "simulation": True,
        "amount_cents": payload.amount_cents,
        "amount_reais": reais,
        "status": "PENDING",
        "pix_copy_paste": pix_code,
        "expires_at": (timezone.now() + timedelta(hours=2)).isoformat(),
    }

class ConfirmSimulationPayload(BaseModel):
    recharge_id: str

@router.post("/client/recharge/confirm-simulation")
def confirm_recharge_simulation(request, payload: ConfirmSimulationPayload):
    from django.conf import settings
    from ninja.errors import HttpError
    from finance.models import WeeklyStoreInvoice

    if not settings.ALLOW_PAYMENT_SIMULATION:
        raise HttpError(404, "Endpoint não disponível.")

    try:
        visible_store_ids = _stores_visible_to_request(request).values("id")
        invoices = WeeklyStoreInvoice.objects.filter(
            id=payload.recharge_id, store_id__in=visible_store_ids
        )
        invoice = invoices.get()
    except WeeklyStoreInvoice.DoesNotExist:
        return {"success": False, "error": "Recarga não encontrada"}

    invoice.status = WeeklyStoreInvoice.InvoiceStatus.PAID
    invoice.save(update_fields=["status"])

    bal = compute_store_balance(invoice.store)
    return {
        "success": True,
        "status": "PAID",
        "new_balance_cents": bal["balance_cents"],
        "new_balance_reais": bal["balance_reais"],
    }

@router.get("/client/financial-statement")
def get_financial_statement(
    request, 
    store_id: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    period: Optional[str] = None,
    type: Optional[str] = "ALL"
):
    from logistics.models import Store, Order
    from finance.models import ManualEntry, WeeklyStoreInvoice
    from datetime import datetime, date, timedelta
    from django.utils import timezone

    try:
        stores = _stores_visible_to_request(request)
        if store_id:
            stores = stores.filter(id=store_id)
        store = stores.first()

        if not store:
            return {"current_balance_cents": 0, "current_balance_reais": 0.0, "total_entries": 0, "items": []}

        if period and not start_date:
            today = timezone.localdate()
            if period == "hoje":
                start_date = today.isoformat()
                end_date = today.isoformat()
            elif period == "7d":
                start_date = (today - timedelta(days=7)).isoformat()
                end_date = today.isoformat()
            elif period == "30d":
                start_date = (today - timedelta(days=30)).isoformat()
                end_date = today.isoformat()
            elif period == "mes":
                start_date = today.replace(day=1).isoformat()
                end_date = today.isoformat()

        entries = []

        # 1. Manual entries
        me_qs = ManualEntry.objects.filter(store_id=store.id, status="APPROVED")
        if start_date:
            try:
                me_qs = me_qs.filter(createdAt__date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
            except Exception:
                pass
        if end_date:
            try:
                me_qs = me_qs.filter(createdAt__date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
            except Exception:
                pass

        for me in me_qs:
            item_type = "RECHARGE" if me.amountCents > 0 and "recarga" in (me.description or "").lower() else ("BONUS" if me.amountCents > 0 else "ADJUSTMENT")
            entries.append({
                "id": f"manual-{me.id}",
                "date": me.createdAt.isoformat() if me.createdAt else "",
                "datetime_sort": me.createdAt,
                "type": item_type,
                "description": me.description or "Ajuste de saldo",
                "amount_cents": me.amountCents,
                "amount_reais": round(me.amountCents / 100.0, 2),
            })

        # 2. Paid invoices / recharges
        try:
            inv_qs = WeeklyStoreInvoice.objects.filter(store_id=store.id, status="PAID")
            if start_date:
                try:
                    inv_qs = inv_qs.filter(startDate__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
                except Exception:
                    pass
            if end_date:
                try:
                    inv_qs = inv_qs.filter(endDate__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
                except Exception:
                    pass

            for inv in inv_qs:
                inv_date = getattr(inv, "createdAt", None) or getattr(inv, "startDate", None)
                entries.append({
                    "id": f"inv-{inv.id}",
                    "date": inv_date.isoformat() if inv_date else "",
                    "datetime_sort": inv_date,
                    "type": "RECHARGE",
                    "description": f"Recarga de Créditos — Fatura #{str(inv.id)[:8]}",
                    "amount_cents": inv.totalCents or 0,
                    "amount_reais": round((inv.totalCents or 0) / 100.0, 2),
                })
        except Exception as e:
            logger.warning(f"Erro ao buscar faturas pagas da loja no extrato: {e}")

        # 3. Completed Orders
        try:
            order_qs = Order.objects.filter(store_id=store.id, status=Order.OrderStatus.COMPLETED)
            if start_date:
                try:
                    order_qs = order_qs.filter(completedAt__date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
                except Exception:
                    pass
            if end_date:
                try:
                    order_qs = order_qs.filter(completedAt__date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
                except Exception:
                    pass

            for o in order_qs:
                order_date = o.completedAt or o.requestedAt
                debit = -abs(o.fareValueCents or 0)
                entries.append({
                    "id": f"order-{o.id}",
                    "date": order_date.isoformat() if order_date else "",
                    "datetime_sort": order_date,
                    "type": "RIDE",
                    "description": f"Entrega #{str(o.id)[:8]}",
                    "amount_cents": debit,
                    "amount_reais": round(debit / 100.0, 2),
                })
        except Exception as e:
            logger.warning(f"Erro ao buscar ordens completadas da loja no extrato: {e}")

        if type and type != "ALL":
            entries = [e for e in entries if e["type"] == type]

        def _to_timestamp(val):
            if not val:
                return 0.0
            if isinstance(val, (datetime, date)):
                if hasattr(val, "timestamp"):
                    return val.timestamp()
                import time
                return time.mktime(val.timetuple())
            try:
                return datetime.fromisoformat(str(val).replace("Z", "+00:00")).timestamp()
            except Exception:
                return 0.0

        entries.sort(key=lambda x: _to_timestamp(x.get("datetime_sort")))

        running_balance = 0
        for e in entries:
            running_balance += e["amount_cents"]
            e["running_balance_cents"] = running_balance
            e["running_balance_reais"] = round(running_balance / 100.0, 2)
            if "datetime_sort" in e:
                del e["datetime_sort"]

        entries.reverse()

        curr_bal = compute_store_balance(store)

        return {
            "current_balance_cents": curr_bal["balance_cents"],
            "current_balance_reais": curr_bal["balance_reais"],
            "total_entries": len(entries),
            "items": entries,
        }
    except Exception as e:
        logger.error(f"Erro ao calcular extrato financeiro da loja: {e}")
        return {"current_balance_cents": 0, "current_balance_reais": 0.0, "total_entries": 0, "items": []}

@router.get("/client/billing-history")
def get_billing_history(request, store_id: Optional[str] = None):
    from logistics.models import Store
    from finance.models import WeeklyStoreInvoice

    try:
        stores = _stores_visible_to_request(request)
        if store_id:
            stores = stores.filter(id=store_id)
        store = stores.first()

        if not store:
            return []

        try:
            invoices = list(WeeklyStoreInvoice.objects.filter(store_id=store.id).order_by("-createdAt"))
        except Exception:
            invoices = list(WeeklyStoreInvoice.objects.filter(store_id=store.id).order_by("-startDate"))

        res = []
        for inv in invoices:
            status_label = "Pendente" if inv.status == "DRAFT" else ("Pago" if inv.status == "PAID" else inv.status)
            created_str = ""
            if getattr(inv, "createdAt", None):
                created_str = inv.createdAt.isoformat()
            elif getattr(inv, "startDate", None):
                created_str = inv.startDate.isoformat()

            res.append({
                "id": str(inv.id),
                "date": created_str,
                "description": f"Recarga / Fatura #{str(inv.id)[:8]}",
                "amount_cents": inv.totalCents or 0,
                "amount_reais": round((inv.totalCents or 0) / 100.0, 2),
                "status": status_label,
                "pix_copy_paste": getattr(inv, "pixCopyPaste", "") or "",
            })
        return res
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de faturamento: {e}")
        return []

@router.get("/operator/store-balances")
def get_operator_store_balances(request):
    from accounts.auth import require_role
    from logistics.models import Store

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)

    qs = Store.objects.select_related("client", "operator").all()
    if not getattr(actor, "is_platform_admin", False):
        qs = qs.filter(operator=actor.operator)
    elif actor.operator_id:
        qs = qs.filter(operator_id=actor.operator_id)

    stores_list = []
    total_debito = 0
    total_credito = 0
    lojas_em_debito = 0

    for s in qs.order_by("name"):
        bal = compute_store_balance(s)
        balance_cents = bal["balance_cents"]
        if balance_cents < 0:
            total_debito += abs(balance_cents)
            lojas_em_debito += 1
            st_badge = "DEVEDOR"
        else:
            total_credito += balance_cents
            st_badge = "EM_DIA"

        stores_list.append({
            "id": str(s.id),
            "name": s.name,
            "client_name": s.client.name if s.client else "",
            "document": s.client.document if s.client else "",
            "city": "Brasília / DF",
            "responsible": s.name,
            "email": "",
            "billing_mode": "PRÉ-PAGO",
            "balance_cents": balance_cents,
            "balance_reais": round(balance_cents / 100.0, 2),
            "status": st_badge,
            "operational": s.operational,
        })

    return {
        "kpis": {
            "total_em_debito_cents": total_debito,
            "total_em_debito_reais": round(total_debito / 100.0, 2),
            "total_em_credito_cents": total_credito,
            "total_em_credito_reais": round(total_credito / 100.0, 2),
            "total_de_lojas": len(stores_list),
            "lojas_em_debito": lojas_em_debito,
        },
        "stores": stores_list,
    }

class AdjustStoreBalancePayload(BaseModel):
    store_id: str
    amount_cents: int
    direction: str = "CREDIT"  # "CREDIT" or "DEBIT"
    category: Optional[str] = "ADJUSTMENT"
    reason: str

@router.post("/operator/adjust-store-balance")
def adjust_store_balance(request, payload: AdjustStoreBalancePayload):
    from logistics.models import Store
    from finance.models import ManualEntry
    from accounts.auth import get_client_portal_user, require_role
    from ninja.errors import HttpError
    import uuid

    actor = require_role(["ADMIN", "MANAGER"])(request)
    if payload.amount_cents <= 0 or not payload.reason.strip():
        raise HttpError(422, "Valor positivo e justificativa são obrigatórios.")
    if payload.direction.upper() not in {"CREDIT", "DEBIT"}:
        raise HttpError(422, "Direção inválida.")

    stores = Store.objects.select_related("operator").filter(id=payload.store_id)
    if not getattr(actor, "is_platform_admin", False):
        stores = stores.filter(operator=actor.operator)
    store = stores.first()
    if not store:
        raise HttpError(404, "Loja não encontrada.")

    val_abs = abs(payload.amount_cents)
    signed_amount = val_abs if payload.direction.upper() == "CREDIT" else -val_abs

    from accounts.models import StaffMember
    staff_member = actor if not getattr(actor, "is_platform_admin", False) else None
    if not staff_member:
        staff_member = StaffMember.objects.filter(operator=store.operator).order_by("createdAt").first()

    entry = ManualEntry.objects.create(
        id=uuid.uuid4(),
        operator=store.operator,
        driver=None,
        store=store,
        created_by_staff=staff_member,
        amountCents=signed_amount,
        description=f"[PlatformAdmin: {actor.name}] {payload.reason}" if getattr(actor, "is_platform_admin", False) else payload.reason,
        visibleToStore=True,
        taxCategory="TAXABLE_INCOME",
        status=ManualEntry.EntryStatus.APPROVED,
        approvedBy=staff_member,
    )

    new_bal = compute_store_balance(store)
    return {
        "success": True,
        "entry_id": str(entry.id),
        "new_balance_cents": new_bal["balance_cents"],
        "new_balance_reais": new_bal["balance_reais"],
        "status": new_bal["status"],
    }

@router.get("/operator/financial-dashboard")
def get_operator_financial_dashboard(request, month: Optional[str] = None):
    from logistics.models import Order
    from finance.models import WithdrawalRequest
    from accounts.models import Operator
    from django.db.models import Sum, Count
    from django.utils import timezone
    from accounts.auth import require_role
    from ninja.errors import HttpError
    import datetime

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    is_platform_admin = bool(getattr(actor, "is_platform_admin", False))
    operator = getattr(actor, "operator", None)

    if is_platform_admin:
        target_op_id = request.GET.get("operator_id") or request.GET.get("company_id") or request.headers.get("X-Operator-Id")
        if target_op_id and str(target_op_id) not in ("global", "NaN", "undefined"):
            op = _operator_from_company_reference(target_op_id)
            if op:
                operator = op

    if not operator and not is_platform_admin:
        raise HttpError(422, "Selecione explicitamente um operador.")

    now = timezone.now()
    target_year = now.year
    target_month = now.month
    if month:
        try:
            dt = datetime.datetime.strptime(month, "%Y-%m")
            target_year = dt.year
            target_month = dt.month
        except ValueError:
            raise HttpError(422, "Mês inválido; use AAAA-MM.")

    month_names_pt = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    month_label = f"{month_names_pt[target_month]} de {target_year}"

    orders_qs = Order.objects.filter(status="COMPLETED")
    withdrawals_qs = WithdrawalRequest.objects.filter(status="PAID")

    if operator:
        orders_qs = orders_qs.filter(operator=operator)
        withdrawals_qs = withdrawals_qs.filter(operator=operator)

    import calendar
    _, last_day = calendar.monthrange(target_year, target_month)
    start_month_dt = datetime.datetime(target_year, target_month, 1, 0, 0, 0)
    end_month_dt = datetime.datetime(target_year, target_month, last_day, 23, 59, 59, 999999)
    if timezone.is_aware(timezone.now()):
        tz = timezone.get_current_timezone()
        start_month_dt = timezone.make_aware(start_month_dt, tz)
        end_month_dt = timezone.make_aware(end_month_dt, tz)

    orders_qs = orders_qs.filter(completedAt__gte=start_month_dt, completedAt__lte=end_month_dt)
    withdrawals_qs = withdrawals_qs.filter(createdAt__gte=start_month_dt, createdAt__lte=end_month_dt)

    orders_agg = orders_qs.aggregate(
        total_fare=Sum("fareValueCents"),
        count=Count("id")
    )
    receita_bruta_cents = orders_agg["total_fare"] or 0
    corridas_entregues = orders_agg["count"] or 0

    comissao_retida_cents = int(receita_bruta_cents * 0.20)
    margem = 20.0 if receita_bruta_cents > 0 else 0.0

    saques_pagos_cents = withdrawals_qs.aggregate(s=Sum("amountCents"))["s"] or 0

    # Cálculo da Taxa da Plataforma SaaS (Alex / Expresso Neves Platform)
    # Suporta taxa base de R$ 0,40/entrega com garantia de piso mínimo mensal de R$ 299,00 e faixas de volume
    if operator and hasattr(operator, "calculate_platform_fee"):
        platform_billing = operator.calculate_platform_fee(corridas_entregues)
    else:
        floor_c = 29900
        calc_c = corridas_entregues * 40
        final_c = max(calc_c, floor_c)
        platform_billing = {
            "deliveries_count": corridas_entregues,
            "calculated_cents": calc_c,
            "floor_cents": floor_c,
            "final_fee_cents": final_c,
            "final_fee_reais": round(final_c / 100.0, 2),
            "floor_reais": 299.00,
            "base_rate_reais": 0.40,
            "applied_floor": final_c == floor_c and calc_c < floor_c,
        }

    custo_plataforma_cents = platform_billing["final_fee_cents"]
    custo_plataforma_reais = platform_billing["final_fee_reais"]

    # Resultado Líquido Real = Comissão Retida - Saques Pagos aos Motoboys - Custo da Licença SaaS
    resultado_liquido_cents = comissao_retida_cents - saques_pagos_cents - custo_plataforma_cents

    ticket_medio_reais = round((receita_bruta_cents / corridas_entregues / 100.0), 2) if corridas_entregues > 0 else 0.0

    return {
        "month": f"{target_year:04d}-{target_month:02d}",
        "month_label": month_label,
        "receita_bruta_cents": receita_bruta_cents,
        "receita_bruta_reais": round(receita_bruta_cents / 100.0, 2),
        "comissao_retida_cents": comissao_retida_cents,
        "comissao_retida_reais": round(comissao_retida_cents / 100.0, 2),
        "margem_percentual": margem,
        "saques_pagos_cents": saques_pagos_cents,
        "saques_pagos_reais": round(saques_pagos_cents / 100.0, 2),
        "custo_plataforma_cents": custo_plataforma_cents,
        "custo_plataforma_reais": custo_plataforma_reais,
        "plataforma_billing": platform_billing,
        "resultado_liquido_cents": resultado_liquido_cents,
        "resultado_liquido_reais": round(resultado_liquido_cents / 100.0, 2),
        "corridas_entregues": corridas_entregues,
        "ticket_medio_reais": ticket_medio_reais,
    }


# ==============================================================================
# MÓDULO 19 MOTORK: CONFERÊNCIA DE DINHEIRO FÍSICO (RECONCILIAÇÃO)
# ==============================================================================

@router.get("/operator/cash-reconciliation")
def get_cash_reconciliation(request, date: Optional[str] = None):
    """
    Retorna a prestação de contas das corridas recebidas em dinheiro vivo pelos motoboys.
    Permite à central de despacho auditar o dinheiro em trânsito e realizar a baixa.
    """
    from logistics.models import Order, Driver
    from finance.models import ManualEntry
    from accounts.models import Operator
    from django.utils import timezone
    from accounts.auth import require_role
    from ninja.errors import HttpError
    from datetime import datetime

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    is_platform_admin = bool(getattr(actor, "is_platform_admin", False))
    operator = getattr(actor, "operator", None)

    if is_platform_admin:
        target_op_id = request.GET.get("operator_id") or request.GET.get("company_id") or request.headers.get("X-Operator-Id")
        if target_op_id and str(target_op_id) not in ("global", "NaN", "undefined"):
            op = _operator_from_company_reference(target_op_id)
            if op:
                operator = op

    if not operator and not is_platform_admin:
        raise HttpError(422, "Selecione explicitamente um operador.")

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else timezone.localdate()
    except ValueError:
        raise HttpError(422, "Data inválida; use AAAA-MM-DD.")

    orders_qs = Order.objects.select_related("driver", "store").filter(
        businessDate=target_date,
        status="COMPLETED"
    )
    if operator:
        orders_qs = orders_qs.filter(operator=operator)

    # Filtrar pedidos onde o cliente pagou em dinheiro
    drivers_map = {}

    for o in orders_qs:
        meta = o.metadata or {}
        forma_pgto = str(meta.get("forma_pagamento") or meta.get("payment_method") or "").upper()
        # Se foi pago em dinheiro ou tem valor em dinheiro explícito
        if "DINHEIRO" in forma_pgto or meta.get("valor_dinheiro_cents", 0) > 0:
            val_dinheiro = meta.get("valor_dinheiro_cents") or o.fareValueCents or 0
            taxa_motoboy = int(o.fareValueCents * 0.80) if o.fareValueCents else 0

            d_id = str(o.driver_id) if o.driver_id else "sem_motoboy"
            d_name = o.driver.name if o.driver else "Não atribuído"
            d_phone = o.driver.phone if o.driver else ""

            if d_id not in drivers_map:
                drivers_map[d_id] = {
                    "driver_id": d_id,
                    "driver_name": d_name,
                    "driver_phone": d_phone,
                    "total_corridas": 0,
                    "total_dinheiro_cents": 0,
                    "total_taxas_cents": 0,
                    "pedidos": [],
                    "status_acerto": "PENDENTE",
                }

            drivers_map[d_id]["total_corridas"] += 1
            drivers_map[d_id]["total_dinheiro_cents"] += val_dinheiro
            drivers_map[d_id]["total_taxas_cents"] += taxa_motoboy

            created_at_str = ""
            if getattr(o, "createdAt", None):
                created_at_str = o.createdAt.isoformat()
            elif getattr(o, "requestedAt", None):
                created_at_str = o.requestedAt.isoformat()
            elif getattr(o, "completedAt", None):
                created_at_str = o.completedAt.isoformat()

            drivers_map[d_id]["pedidos"].append({
                "order_id": str(o.id),
                "store_name": o.store.name if o.store else "",
                "cash_amount_cents": val_dinheiro,
                "cash_amount_reais": round(val_dinheiro / 100.0, 2),
                "valor_dinheiro_cents": val_dinheiro,
                "valor_dinheiro_reais": round(val_dinheiro / 100.0, 2),
                "taxa_motoboy_cents": taxa_motoboy,
                "taxa_motoboy_reais": round(taxa_motoboy / 100.0, 2),
                "created_at": created_at_str,
                "completed_at": o.completedAt.isoformat() if getattr(o, "completedAt", None) else "",
            })

    # Verificar acertos já realizados (ManualEntry com descrição ou categoria de acerto)
    settlements = ManualEntry.objects.filter(
        createdAt__date=target_date,
        description__contains="ACERTO_DINHEIRO:",
        status=ManualEntry.EntryStatus.APPROVED,
    )
    if operator:
        settlements = settlements.filter(operator=operator)
    settled_drivers = {str(s.driver_id): str(s.id) for s in settlements if s.driver_id}

    total_circulando = 0
    drivers_list = []

    for d_id, data in drivers_map.items():
        saldo_devido = data["total_dinheiro_cents"] - data["total_taxas_cents"]
        if d_id in settled_drivers:
            data["status_acerto"] = "ACERTADO"
        else:
            total_circulando += data["total_dinheiro_cents"]

        driver_item = {
            "driver_id": d_id,
            "driver_name": data["driver_name"],
            "driver_phone": data["driver_phone"],
            "orders_count": data["total_corridas"],
            "cash_collected_cents": data["total_dinheiro_cents"],
            "cash_collected_reais": round(data["total_dinheiro_cents"] / 100.0, 2),
            "driver_earnings_cents": data["total_taxas_cents"],
            "driver_earnings_reais": round(data["total_taxas_cents"] / 100.0, 2),
            "net_due_operator_cents": saldo_devido,
            "net_due_operator_reais": round(saldo_devido / 100.0, 2),
            "orders": data["pedidos"],
            "status_acerto": data["status_acerto"],
            "settlement_id": settled_drivers.get(d_id),
            # Campos legados mantidos para compatibilidade
            "total_corridas": data["total_corridas"],
            "total_dinheiro_cents": data["total_dinheiro_cents"],
            "total_dinheiro_reais": round(data["total_dinheiro_cents"] / 100.0, 2),
            "total_taxas_cents": data["total_taxas_cents"],
            "total_taxas_reais": round(data["total_taxas_cents"] / 100.0, 2),
            "saldo_devido_cents": saldo_devido,
            "saldo_devido_reais": round(saldo_devido / 100.0, 2),
            "pedidos": data["pedidos"],
        }
        drivers_list.append(driver_item)

    total_collected_cents = sum(d["cash_collected_cents"] for d in drivers_list)
    total_earnings_cents = sum(d["driver_earnings_cents"] for d in drivers_list)
    total_due_cents = sum(d["net_due_operator_cents"] for d in drivers_list)

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "summary": {
            "total_collected_cents": total_collected_cents,
            "total_collected_reais": round(total_collected_cents / 100.0, 2),
            "total_earnings_cents": total_earnings_cents,
            "total_earnings_reais": round(total_earnings_cents / 100.0, 2),
            "total_due_operator_cents": total_due_cents,
            "total_due_operator_reais": round(total_due_cents / 100.0, 2),
            "drivers_count": len(drivers_list),
        },
        "kpis": {
            "total_dinheiro_circulando_cents": total_circulando,
            "total_dinheiro_circulando_reais": round(total_circulando / 100.0, 2),
            "total_motoboys_com_pendencia": sum(1 for d in drivers_list if d["status_acerto"] == "PENDENTE"),
            "total_corridas_dinheiro": sum(d["orders_count"] for d in drivers_list),
        },
        "drivers": drivers_list,
    }

class SettleCashPayload(BaseModel):
    driver_id: str
    amount_cents: int
    notes: Optional[str] = "Acerto diário de dinheiro em espécie"

@router.post("/operator/settle-cash")
@transaction.atomic
def settle_cash_balance(request, payload: SettleCashPayload):
    """
    Registra a quitação e prestação de contas do dinheiro físico recebido pelo motoboy.
    Gera um lançamento auditado no banco de dados.
    """
    from logistics.models import Driver
    from finance.models import ManualEntry
    from accounts.auth import require_role
    from ninja.errors import HttpError
    import uuid

    actor = require_role(["ADMIN", "MANAGER"])(request)
    if payload.amount_cents <= 0:
        raise HttpError(422, "O valor do acerto deve ser positivo.")
    drivers = Driver.objects.select_for_update().filter(id=payload.driver_id)
    if not getattr(actor, "is_platform_admin", False):
        drivers = drivers.filter(operator=actor.operator)
    driver = drivers.first()
    if not driver:
        raise HttpError(404, "Motoboy não encontrado.")

    from django.utils import timezone
    previous = ManualEntry.objects.filter(
        operator=driver.operator, driver=driver,
        createdAt__date=timezone.localdate(),
        description__contains="ACERTO_DINHEIRO:",
        status=ManualEntry.EntryStatus.APPROVED,
    ).first()
    if previous:
        if previous.amountCents != -abs(payload.amount_cents):
            raise HttpError(409, "Este motoboy já possui um acerto nesta data. Confira o recibo antes de ajustar o valor.")
        return {
            "success": True, "entry_id": str(previous.id),
            "settled_amount_reais": round(payload.amount_cents / 100.0, 2),
            "driver_id": str(driver.id), "status": "ACERTADO",
        }

    from accounts.models import StaffMember
    staff_member = actor if not getattr(actor, "is_platform_admin", False) else None
    if not staff_member:
        staff_member = StaffMember.objects.filter(operator=driver.operator).order_by("createdAt").first()

    entry = ManualEntry.objects.create(
        id=uuid.uuid4(),
        operator=driver.operator,
        driver=driver,
        created_by_staff=staff_member,
        amountCents=-abs(payload.amount_cents),
        description=f"[PlatformAdmin: {actor.name}] ACERTO_DINHEIRO: {payload.notes}" if getattr(actor, "is_platform_admin", False) else f"ACERTO_DINHEIRO: {payload.notes}",
        visibleToStore=False,
        taxCategory="NON_TAXABLE_REIMBURSEMENT",
        status=ManualEntry.EntryStatus.APPROVED,
        approvedBy=staff_member,
    )

    return {
        "success": True,
        "entry_id": str(entry.id),
        "settled_amount_reais": round(payload.amount_cents / 100.0, 2),
        "driver_id": str(driver.id),
        "status": "ACERTADO"
    }


# ==============================================================================
# MÓDULO 03 MOTORK: LANÇAR CORRIDA PELA LOJA (DESPACHO CENTRALIZADO)
# ==============================================================================

class DeliveryStopItem(BaseModel):
    endereco: str
    numero: Optional[str] = ""
    complemento: Optional[str] = ""
    cliente: Optional[str] = ""
    telefone: Optional[str] = ""
    notas: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None

class DispatchStoreRidePayload(BaseModel):
    store_id: str
    driver_id: Optional[str] = None
    coleta_endereco: Optional[str] = None
    coleta_lat: Optional[float] = None
    coleta_lng: Optional[float] = None
    destinos: List[DeliveryStopItem]
    forma_pagamento: Optional[str] = "JA_PAGO"  # "DINHEIRO", "PIX", "CARTAO", "JA_PAGO"
    troco_para: Optional[float] = None
    valor_estimado_cents: Optional[int] = None
    distancia_metros: Optional[int] = None
    observacao: Optional[str] = ""

@router.post("/operator/dispatch-store-ride")
@idempotent(timeout=86400, required=False, allow_memory_fallback=True)
def dispatch_store_ride(request, payload: DispatchStoreRidePayload):
    """
    Permite à central de despacho lançar uma corrida em nome de uma loja parceira,
    validando o saldo (se pré-paga), aplicando a tabela de contrato e criando a corrida.
    """
    from logistics.models import Store, Driver, Order, Stop
    from django.contrib.gis.geos import Point
    from django.utils import timezone
    from accounts.auth import require_role
    from finance.business_date import resolve_store_business_date
    from logistics.pricing import parse_coordinate, price_route_with_method
    from ninja.errors import HttpError
    import uuid

    auth = getattr(request, "auth", None) or {}
    if auth.get("user_type") == "client_portal_user" or auth.get("client_id"):
        from accounts.auth import get_client_portal_user
        client_user = get_client_portal_user(request)
        if not client_user:
            raise HttpError(401, "Usuário lojista não autenticado.")
        stores = Store.objects.select_related("operator", "client").filter(
            id=payload.store_id, client=client_user.client, operational=True
        )
        store = stores.first()
    else:
        actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE"])(request)
        stores = Store.objects.select_related("operator", "client").filter(
            id=payload.store_id, operational=True
        )
        if not getattr(actor, "is_platform_admin", False):
            stores = stores.filter(operator=actor.operator)
        store = stores.first()
    if not store:
        raise HttpError(404, "Loja parceira não encontrada.")
    driver = None
    if payload.driver_id:
        driver = Driver.objects.filter(
            id=payload.driver_id, operator=store.operator, active=True
        ).first()
        if not driver:
            raise HttpError(404, "Motoboy não encontrado neste operador.")

    now = timezone.now()
    initial_status = "ACCEPTED" if driver else "OFFERED"

    metadata = {
        "forma_pagamento": payload.forma_pagamento,
        "troco_para": payload.troco_para,
        "observacao": payload.observacao,
        "coleta_endereco": payload.coleta_endereco,
        "origem": "CENTRAL_DESPACHO",
        "num_destinos": len(payload.destinos),
    }
    if payload.destinos:
        first_d = payload.destinos[0]
        metadata["cliente_nome"] = first_d.cliente
        metadata["cliente_telefone"] = first_d.telefone
        metadata["entrega_endereco"] = f"{first_d.endereco}, {first_d.numero}"

    if not payload.destinos:
        raise HttpError(422, "A corrida deve conter ao menos um destino.")

    def valid_point(lat, lng):
        from django.db import connection

        if lat is None or lng is None:
            raise HttpError(422, "Todos os destinos devem possuir latitude e longitude.")
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise HttpError(422, "Coordenadas de destino inválidas.")
        # The hermetic unit suite uses plain SQLite/TEXT instead of a spatial DB.
        if connection.vendor == "sqlite":
            return None
        return Point(lng, lat, srid=4326)

    if payload.coleta_lat is not None or payload.coleta_lng is not None:
        pickup_geom = valid_point(payload.coleta_lat, payload.coleta_lng)
        pickup_coordinates = (
            parse_coordinate(
                payload.coleta_lat, field_name="coleta_lat", minimum=-90, maximum=90
            ),
            parse_coordinate(
                payload.coleta_lng, field_name="coleta_lng", minimum=-180, maximum=180
            ),
        )
    else:
        pickup_geom = store.geom
        try:
            pickup_coordinates = (float(store.geom.y), float(store.geom.x))
        except (AttributeError, TypeError, ValueError) as exc:
            raise HttpError(
                422, "A loja não possui coordenadas de coleta configuradas."
            ) from exc
    from django.db import connection
    if pickup_geom is None and connection.vendor != "sqlite":
        raise HttpError(422, "A loja não possui coordenadas de coleta configuradas.")

    destination_coordinates = [
        (
            parse_coordinate(
                destination.lat,
                field_name=f"destinos[{index}].lat",
                minimum=-90,
                maximum=90,
            ),
            parse_coordinate(
                destination.lng,
                field_name=f"destinos[{index}].lng",
                minimum=-180,
                maximum=180,
            ),
        )
        for index, destination in enumerate(payload.destinos, start=1)
    ]
    try:
        distance_km, fare_cents, distance_method = price_route_with_method(
            store, [pickup_coordinates, *destination_coordinates]
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc

    from django.db import transaction

    with transaction.atomic():
        store_locked = Store.objects.select_for_update().get(pk=store.pk)
        bal = compute_store_balance(store_locked)
        mode = bal.get("billing_mode", "").upper()
        if mode in ("PRE_PAGO", "PRÉ-PAGO") and bal["balance_cents"] < fare_cents:
            raise HttpError(409, "Saldo insuficiente para esta entrega.")

        order = Order.objects.create(
            id=uuid.uuid4(),
            operator=store_locked.operator,
            store=store_locked,
            driver=driver,
            status=initial_status,
            fareValueCents=fare_cents,
            distanceMeters=int(distance_km * 1000),
            businessDate=resolve_store_business_date(store),
            requestedAt=now,
            acceptedAt=now if driver else None,
            metadata={
                **metadata,
                "distance_method": distance_method,
            },
        )

        Stop.objects.create(
            id=uuid.uuid4(),
            operator=store.operator,
            order=order,
            sequence=1,
            type="PICKUP",
            geom=pickup_geom,
            metadata={"endereco": payload.coleta_endereco or store.name},
        )

        # Criar Paradas de Entrega (DROPOFF)
        for seq, (d, destination_coordinate) in enumerate(
            zip(payload.destinos, destination_coordinates), start=2
        ):
            Stop.objects.create(
                id=uuid.uuid4(),
                operator=store.operator,
                order=order,
                sequence=seq,
                type="DROPOFF",
                geom=valid_point(*destination_coordinate),
                metadata={
                    "endereco": d.endereco,
                    "numero": d.numero,
                    "complemento": d.complemento,
                    "cliente": d.cliente,
                    "telefone": d.telefone,
                    "notas": d.notas,
                },
            )

    return {
        "success": True,
        "order_id": str(order.id),
        "status": order.status,
        "store_name": store.name,
        "driver_name": driver.name if driver else "Fila de Oferta",
        "fare_reais": round(fare_cents / 100.0, 2),
        "distance_km": round(distance_km, 2),
    }


class CreateCustomerPayload(BaseModel):
    name: str
    phone: Optional[str] = ""
    address: str
    number: Optional[str] = ""
    complement: Optional[str] = ""
    neighborhood: Optional[str] = ""
    city: Optional[str] = "São Paulo"
    notes: Optional[str] = ""


@router.get("/client/customers")
def list_client_customers(request, q: Optional[str] = None, store_id: Optional[str] = None):
    """
    Retorna o catálogo de clientes finais atendidos pela loja (Módulo Meus Clientes - C6 do MotorK).
    Agrupa pedidos e entregas com dados cadastrais, endereço padrão, pedidos e ticket médio.
    """
    from logistics.models import Order, Store
    qs = _orders_visible_to_request(request).select_related("store").order_by("-requestedAt")
    if store_id:
        qs = qs.filter(store_id=store_id)

    orders = qs[:300]
    customers_map = {}

    for ord in orders:
        meta = ord.metadata or {}
        name = meta.get("cliente_nome") or ""
        phone = meta.get("cliente_telefone") or ""
        address = meta.get("entrega_endereco") or ""

        if not name and not phone:
            continue

        key = phone.strip() if phone else name.strip().lower()
        if key not in customers_map:
            customers_map[key] = {
                "id": key,
                "name": name or "Cliente Sem Nome",
                "phone": phone or "",
                "address": address or "Endereço não informado",
                "orders_count": 0,
                "total_spent_cents": 0,
                "last_order_at": ord.requestedAt.isoformat() if ord.requestedAt else "",
                "store_name": ord.store.name if ord.store else "",
            }

        cust = customers_map[key]
        cust["orders_count"] += 1
        cust["total_spent_cents"] += (ord.fareValueCents or 0)
        if ord.requestedAt and (not cust["last_order_at"] or ord.requestedAt.isoformat() > cust["last_order_at"]):
            cust["last_order_at"] = ord.requestedAt.isoformat()
            if address:
                cust["address"] = address

    results = []
    for c in customers_map.values():
        total_reais = round(c["total_spent_cents"] / 100.0, 2)
        ticket_medio = round(total_reais / c["orders_count"], 2) if c["orders_count"] > 0 else 0.0
        item = {
            **c,
            "total_spent_reais": total_reais,
            "ticket_medio_reais": ticket_medio,
        }
        if q:
            query = q.lower()
            name_val = str(item.get("name") or "").lower()
            phone_val = str(item.get("phone") or "").lower()
            address_val = str(item.get("address") or "").lower()
            if query not in name_val and query not in phone_val and query not in address_val:
                continue
        results.append(item)

    results.sort(key=lambda x: x["orders_count"], reverse=True)

    return {
        "total": len(results),
        "customers": results,
    }


@router.post("/client/customers")
def create_client_customer(request, payload: CreateCustomerPayload):
    from ninja.errors import HttpError
    raise HttpError(501, "Cadastro persistente de clientes finais ainda não está implementado.")


@router.get("/dashboard-stats")
def get_dashboard_stats(
    request,
    range: Optional[str] = None,
    period: Optional[str] = None,
    company_id: Optional[str] = None
):
    """
    Consolidated Dashboard KPIs & Metrics:
    - Faturamento total do período
    - Faturamento por dia (gráfico de área)
    - Total de entregas
    - Entregas concluídas
    - Entregas em andamento
    - Entregas canceladas
    - Taxa de conclusão (%)
    - Ticket médio (R$)
    - Lojas parceiras ativas / total
    - Motoboys ativos / total
    - Ranking de Lojas Parceiras (Top lojas por receita e volume de corridas)
    - Radar de entregas recentes
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Sum
    from logistics.models import Order, Store, Driver
    from finance.models import ManualEntry
    from accounts.auth import get_client_portal_user, require_role
    
    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")
    is_admin = False
    auth_op_id = None
    client_user = None
    if client_id or auth.get("user_type") == "client_portal_user":
        client_user = get_client_portal_user(request)
        client_id = client_user.client_id if client_user else None
        if not client_id:
            from ninja.errors import HttpError
            raise HttpError(401, "Usuário lojista não autenticado.")
    else:
        actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
        is_admin = bool(getattr(actor, "is_platform_admin", False))
        auth_op_id = actor.operator_id
    
    selected_range = range or period or "last7"
    
    # Calculate date range
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if selected_range == "today":
        start_date = today_start
        end_date = now
        days_count = 1
    elif selected_range == "month":
        start_date = today_start.replace(day=1)
        end_date = now
        days_count = (now - start_date).days + 1
    elif selected_range == "all":
        start_date = today_start - timedelta(days=90)
        end_date = now
        days_count = 90
    else:  # "last7" default
        start_date = today_start - timedelta(days=6)
        end_date = now
        days_count = 7
        
    # Scoping for Orders & related models
    orders_qs = Order.objects.select_related("store", "driver").all()
    stores_qs = Store.objects.all()
    drivers_qs = Driver.objects.all()
    entries_qs = ManualEntry.objects.all()
    
    if client_id:
        orders_qs = orders_qs.filter(store__client_id=client_id)
        stores_qs = stores_qs.filter(client_id=client_id)
        if client_user and client_user.operator_id:
            drivers_qs = drivers_qs.filter(operator_id=client_user.operator_id)
        else:
            drivers_qs = drivers_qs.none()
        entries_qs = entries_qs.none()
    elif not is_admin and auth_op_id:
        orders_qs = orders_qs.filter(operator_id=auth_op_id)
        stores_qs = stores_qs.filter(operator_id=auth_op_id)
        drivers_qs = drivers_qs.filter(operator_id=auth_op_id)
        entries_qs = entries_qs.filter(operator_id=auth_op_id)
    elif company_id and company_id != "global":
        try:
            orders_qs = orders_qs.filter(operator_id=company_id)
            stores_qs = stores_qs.filter(operator_id=company_id)
            drivers_qs = drivers_qs.filter(operator_id=company_id)
            entries_qs = entries_qs.filter(operator_id=company_id)
        except Exception:
            pass
    elif not is_admin:
        orders_qs = orders_qs.none()
        stores_qs = stores_qs.none()
        drivers_qs = drivers_qs.none()
        entries_qs = entries_qs.none()

    # Filter period orders
    period_orders = orders_qs.filter(requestedAt__gte=start_date, requestedAt__lte=end_date)
    period_entries = entries_qs.filter(createdAt__gte=start_date, createdAt__lte=end_date)
    
    # Active orders (in progress right now)
    active_statuses = [
        Order.OrderStatus.STARTED,
        Order.OrderStatus.ACCEPTED,
        Order.OrderStatus.OFFERED,
        Order.OrderStatus.READY_FOR_DISPATCH,
        Order.OrderStatus.PREPARING,
        Order.OrderStatus.ARRIVED,
    ]
    active_orders_count = orders_qs.filter(status__in=active_statuses).count()
    
    # Period order statistics
    total_orders = period_orders.count()
    completed_orders = period_orders.filter(status=Order.OrderStatus.COMPLETED).count()
    canceled_orders = period_orders.filter(status__in=[
        Order.OrderStatus.CANCELED,
        Order.OrderStatus.CANCELED_IN_TRANSIT,
        Order.OrderStatus.RETURNED
    ]).count()
    
    completion_rate = 0.0
    if (completed_orders + canceled_orders) > 0:
        completion_rate = round((completed_orders / (completed_orders + canceled_orders)) * 100.0, 1)
    elif completed_orders > 0:
        completion_rate = 100.0
        
    # Revenue calculations
    orders_rev_cents = period_orders.filter(status=Order.OrderStatus.COMPLETED).aggregate(s=Sum("fareValueCents"))["s"] or 0
    orders_revenue = orders_rev_cents / 100.0
    
    entries_cents = period_entries.aggregate(s=Sum("amountCents"))["s"] or 0
    entries_net = entries_cents / 100.0
        
    faturamento_total = orders_revenue if orders_revenue > 0 else max(entries_net, 0.0)
    average_ticket = round(faturamento_total / completed_orders, 2) if completed_orders > 0 else 0.0
    
    active_stores = stores_qs.filter(operational=True).count()
    total_stores = stores_qs.count()
    active_drivers = drivers_qs.filter(active=True).count()
    total_drivers = drivers_qs.count()
    
    # Daily timeline: agregação única em lote via TruncDay (1 query SQL em vez de 180 queries)
    from django.db.models.functions import TruncDay
    from django.db.models import Count
    import builtins

    daily_aggregates = (
        period_orders.filter(status=Order.OrderStatus.COMPLETED)
        .annotate(day=TruncDay("requestedAt"))
        .values("day")
        .annotate(
            faturamento_cents=Sum("fareValueCents"),
            total_corridas=Count("id")
        )
        .order_by("day")
    )
    daily_map = {}
    for row in daily_aggregates:
        if row["day"]:
            d_val = row["day"]
            day_str = d_val.strftime("%Y-%m-%d") if hasattr(d_val, "strftime") else str(d_val)[:10]
            daily_map[day_str] = {
                "faturamento": (row["faturamento_cents"] or 0) / 100.0,
                "corridas": row["total_corridas"] or 0,
            }

    daily_data = []
    for day_idx in builtins.range(days_count):
        d_start = (start_date + timedelta(days=day_idx)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_label = d_start.strftime("%d/%m")
        day_iso = d_start.strftime("%Y-%m-%d")
        val = daily_map.get(day_iso, {"faturamento": 0.0, "corridas": 0})
        daily_data.append({
            "date": day_iso,
            "time": day_label,
            "faturamento": val["faturamento"],
            "corridas": val["corridas"],
        })
        
    # Ranking of Top Partner Stores
    top_stores = []
    store_map = {}
    for ord in period_orders.select_related("store"):
        s_id = str(ord.store_id) if ord.store_id else "unknown"
        s_name = ord.store.name if (ord.store and ord.store.name) else "Expresso Neves"
        if s_id not in store_map:
            store_map[s_id] = {"id": s_id, "nome": s_name, "corridas": 0, "faturamento": 0.0}
        store_map[s_id]["corridas"] += 1
        if ord.status == Order.OrderStatus.COMPLETED:
            store_map[s_id]["faturamento"] += (ord.fareValueCents or 0) / 100.0
            
    sorted_stores = sorted(store_map.values(), key=lambda x: (x["faturamento"], x["corridas"]), reverse=True)
    max_rides = max([s["corridas"] for s in sorted_stores], default=1) or 1
    for s in sorted_stores[:8]:
        s["percentual"] = round((s["corridas"] / max_rides) * 100, 1)
        s["ticket_medio"] = round(s["faturamento"] / s["corridas"], 2) if s["corridas"] > 0 else 0.0
        top_stores.append(s)
        
    # Recent / Active Orders for Real-Time Radar
    recent_qs = orders_qs.order_by("-requestedAt")[:12]
    recent_orders = []
    for o in recent_qs:
        drv_name = "Aguardando condutor"
        try:
            if o.driver_id and hasattr(o, "driver") and o.driver:
                drv_name = o.driver.name
        except Exception:
            pass
        st_name = "Expresso Neves"
        try:
            if o.store_id and hasattr(o, "store") and o.store:
                st_name = o.store.name
        except Exception:
            pass
            
        status_label = "Em andamento"
        if o.status == Order.OrderStatus.COMPLETED:
            status_label = "Finalizada"
        elif o.status in [Order.OrderStatus.STARTED, Order.OrderStatus.ARRIVED]:
            status_label = "Em trânsito"
        elif o.status == Order.OrderStatus.ACCEPTED:
            status_label = "Aceita"
        elif o.status == Order.OrderStatus.OFFERED:
            status_label = "Ofertada"
        elif o.status in [Order.OrderStatus.CANCELED, Order.OrderStatus.CANCELED_IN_TRANSIT]:
            status_label = "Cancelada"
            
        recent_orders.append({
            "id": f"#{str(o.id)[:8]}",
            "motoboy": drv_name,
            "empresa": st_name,
            "loja": st_name,
            "status": o.status,
            "status_label": status_label,
            "valor": (o.fareValueCents or 0) / 100.0 if hasattr(o, "fareValueCents") else 0.0,
            "time": o.requestedAt.strftime("%H:%M") if getattr(o, "requestedAt", None) and hasattr(o.requestedAt, "strftime") else "Agora",
            "date": o.requestedAt.strftime("%d/%m") if getattr(o, "requestedAt", None) and hasattr(o.requestedAt, "strftime") else "",
        })
        
    return {
        "range": selected_range,
        "faturamento_total": faturamento_total,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "active_orders": active_orders_count,
        "canceled_orders": canceled_orders,
        "completion_rate": completion_rate,
        "average_ticket": average_ticket,
        "active_stores": active_stores,
        "total_stores": total_stores,
        "active_drivers": active_drivers,
        "total_drivers": total_drivers,
        "chart_data": daily_data,
        "top_stores": top_stores,
        "recent_orders": recent_orders,
    }


# ==============================================================================
# GESTÃO DA CARTEIRA DOS MOTOBOYS (DUPLA-CONTRAPARTIDA, AUDITORIA & EXTRATO)
# ==============================================================================

class AdjustDriverWalletPayload(BaseModel):
    driver_id: str
    amount_cents: int
    direction: str = "CREDIT"  # "CREDIT" (Operador paga motoboy) ou "DEBIT" (Operador desconta do motoboy)
    category: Optional[str] = "ADJUSTMENT"  # "ADVANCE", "BONUS", "PENALTY", "ADJUSTMENT", "DAILY_SETTLEMENT"
    reason: str


@router.get("/operator/driver-wallets")
def get_operator_driver_wallets(request, company_id: Optional[str] = None):
    """
    Retorna a listagem de todos os motoboys e o saldo atual de suas carteiras (Wallet),
    além de indicadores (KPIs) agregados para o Operador Logístico ou Superadmin.
    """
    from logistics.models import Driver, Vehicle
    from finance.models import Wallet
    from django.core.exceptions import ValidationError
    from accounts.auth import require_role

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    is_admin = bool(getattr(actor, "is_platform_admin", False))
    auth_op_id = actor.operator_id

    if not is_admin and auth_op_id:
        drivers_qs = Driver.objects.filter(operator_id=auth_op_id)
    elif company_id and company_id != "global":
        try:
            drivers_qs = Driver.objects.filter(operator_id=company_id)
        except (ValidationError, ValueError):
            drivers_qs = Driver.objects.none()
    elif is_admin:
        drivers_qs = Driver.objects.all()
    else:
        drivers_qs = Driver.objects.none()

    drivers_list = []
    total_a_pagar_cents = 0
    total_em_debito_cents = 0
    motoboys_com_saldo = 0

    for d in drivers_qs.order_by("name"):
        wallet, _ = Wallet.objects.get_or_create(
            driver_id=d.id,
            defaults={"operator_id": d.operator_id, "balanceCents": 0}
        )
        bal_cents = wallet.balanceCents or 0
        bal_reais = round(bal_cents / 100.0, 2)

        if bal_cents > 0:
            total_a_pagar_cents += bal_cents
            motoboys_com_saldo += 1
            st_badge = "CREDOR"
        elif bal_cents < 0:
            total_em_debito_cents += abs(bal_cents)
            motoboys_com_saldo += 1
            st_badge = "DEVEDOR"
        else:
            st_badge = "ZERADO"

        veh = Vehicle.objects.filter(operator=d.operator).first()

        drivers_list.append({
            "id": str(d.id),
            "driver_id": str(d.id),
            "name": d.name,
            "phone": d.phone or "",
            "document": d.document or "",
            "plate": veh.plate if veh else "",
            "vehicle_type": veh.type if veh else "Motocicleta",
            "pixKey": d.pixKey or "",
            "pixKeyType": d.pixKeyType or "CPF",
            "balance_cents": bal_cents,
            "balance_reais": bal_reais,
            "status": st_badge,
            "active": d.active,
        })

    return {
        "kpis": {
            "total_a_pagar_cents": total_a_pagar_cents,
            "total_a_pagar_reais": round(total_a_pagar_cents / 100.0, 2),
            "total_em_debito_cents": total_em_debito_cents,
            "total_em_debito_reais": round(total_em_debito_cents / 100.0, 2),
            "total_motoboys": len(drivers_list),
            "motoboys_com_saldo": motoboys_com_saldo,
        },
        "drivers": drivers_list,
    }


@router.post("/operator/driver-wallet/adjust")
def adjust_driver_wallet(request, payload: AdjustDriverWalletPayload):
    """
    Realiza lançamento manual e auditado na carteira do motoboy.
    Suporta:
    - CREDIT: Bônus, Diária extra, Ajuste a favor do motoboy (Operador -> Motoboy).
    - DEBIT: Adiantamento (Vale), Penalidade/Avaria, Desconto (Motoboy -> Operador).
    Usa dupla-contrapartida contábil acionando trigger nativa no PostgreSQL.
    """
    from logistics.models import Driver
    from finance.models import Wallet, OperatorInternalWallet, WalletTransaction, ManualEntry
    from django.db import transaction
    from ninja.errors import HttpError
    from accounts.auth import require_role
    import uuid

    actor = require_role(["ADMIN", "MANAGER"])(request)
    is_admin = bool(getattr(actor, "is_platform_admin", False))
    auth_op_id = actor.operator_id
    staff_id = actor.id

    if payload.amount_cents <= 0:
        raise HttpError(400, "O valor do lançamento deve ser maior que zero.")

    if not payload.reason or not payload.reason.strip():
        raise HttpError(400, "A justificativa/motivo é obrigatória para fins de auditoria.")

    direction = payload.direction.upper()
    if direction not in ["CREDIT", "DEBIT"]:
        raise HttpError(400, "Direção inválida. Use 'CREDIT' ou 'DEBIT'.")

    category = (payload.category or "ADJUSTMENT").upper()
    valid_categories = ["ADVANCE", "BONUS", "PENALTY", "ADJUSTMENT", "DAILY_SETTLEMENT", "REFUND"]
    if category not in valid_categories:
        category = "ADJUSTMENT"

    try:
        driver = Driver.objects.select_related("operator").get(id=payload.driver_id)
    except Driver.DoesNotExist:
        raise HttpError(404, "Motoboy não encontrado.")

    # Verifica permissão de tenant
    if not is_admin and str(driver.operator_id) != str(auth_op_id):
        raise HttpError(404, "Motoboy não encontrado.")


    with transaction.atomic():
        # 1. Garante a Carteira do Motorista
        driver_wallet, _ = Wallet.objects.select_for_update().get_or_create(
            driver_id=driver.id,
            defaults={"operator_id": driver.operator_id, "balanceCents": 0}
        )

        # 2. Garante a Carteira Interna do Operador (Contrapartida)
        operator_wallet, _ = OperatorInternalWallet.objects.select_for_update().get_or_create(
            operator_id=driver.operator_id,
            defaults={"balanceCents": 0}
        )

        # 3. Mapeia fluxo de Dupla-Contrapartida
        if direction == "CREDIT":
            # Operador transfere dinheiro para o motoboy (crédito)
            src_drv = None
            dest_drv = driver_wallet
            src_op = operator_wallet
            dest_op = None
            tax_cat = "TAXABLE_INCOME"
        else:
            # Motoboy tem saldo debitado (adiantamento/desconto para o operador)
            src_drv = driver_wallet
            dest_drv = None
            src_op = None
            dest_op = operator_wallet
            tax_cat = "DEDUCTION"

        # 4. Criação da WalletTransaction (aciona a trigger no PostgreSQL)
        w_tx = WalletTransaction.objects.create(
            id=uuid.uuid4(),
            operator=driver.operator,
            source_driver_wallet=src_drv,
            destination_driver_wallet=dest_drv,
            source_operator_wallet=src_op,
            destination_operator_wallet=dest_op,
            amountCents=payload.amount_cents,
            category=category,
            taxCategory=tax_cat,
        )

        # 5. Registro complementar no ManualEntry para auditoria
        entry_amount = payload.amount_cents if direction == "CREDIT" else -payload.amount_cents
        try:
            ManualEntry.objects.create(
                id=uuid.uuid4(),
                operator=driver.operator,
                driver=driver,
                amountCents=entry_amount,
                category=category,
                status="APPROVED",
                notes=payload.reason.strip(),
                created_by_staff_id=staff_id if (staff_id and not is_admin) else None,
            )
        except Exception:
            pass

        # Recarrega o saldo atualizado pela trigger
        driver_wallet.refresh_from_db()

        return {
            "success": True,
            "transaction_id": str(w_tx.id),
            "driver_id": str(driver.id),
            "driver_name": driver.name,
            "direction": direction,
            "category": category,
            "amount_cents": payload.amount_cents,
            "amount_reais": round(payload.amount_cents / 100.0, 2),
            "new_balance_cents": driver_wallet.balanceCents,
            "new_balance_reais": round(driver_wallet.balanceCents / 100.0, 2),
            "message": f"Lançamento de R$ {payload.amount_cents / 100.0:.2f} registrado com sucesso na carteira de {driver.name}!",
        }


@router.get("/operator/driver-wallet/transactions")
def get_driver_wallet_transactions(request, driver_id: str, limit: int = 50):
    """
    Retorna o extrato cronológico detalhado de movimentações da carteira do motoboy.
    """
    from logistics.models import Driver
    from finance.models import Wallet, WalletTransaction, ManualEntry
    from django.db.models import Q
    from ninja.errors import HttpError
    from accounts.auth import require_role

    actor = require_role(["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])(request)
    is_admin = bool(getattr(actor, "is_platform_admin", False))
    auth_op_id = actor.operator_id

    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        raise HttpError(404, "Motoboy não encontrado.")

    if not is_admin and str(driver.operator_id) != str(auth_op_id):
        raise HttpError(404, "Motoboy não encontrado.")


    wallet, _ = Wallet.objects.get_or_create(
        driver_id=driver.id,
        defaults={"operator_id": driver.operator_id, "balanceCents": 0}
    )

    tx_qs = WalletTransaction.objects.filter(
        Q(source_driver_wallet=wallet) | Q(destination_driver_wallet=wallet)
    ).order_by("-createdAt")[:limit]

    # Mapeia justificativas de ManualEntry por data aproximada / categoria
    manual_entries = list(
        ManualEntry.objects.filter(driver=driver).order_by("-createdAt")[:limit]
    )

    transactions_list = []
    for tx in tx_qs:
        is_credit = tx.destination_driver_wallet_id == wallet.id
        direction = "CREDIT" if is_credit else "DEBIT"

        # Tenta correlacionar nota de ManualEntry
        matched_note = ""
        for me in manual_entries:
            if getattr(me, "taxCategory", None) == tx.taxCategory and abs(abs(me.amountCents) - tx.amountCents) < 5:
                matched_note = getattr(me, "description", "") or ""
                break

        transactions_list.append({
            "id": str(tx.id),
            "created_at": tx.createdAt.isoformat() if tx.createdAt else "",
            "category": tx.category,
            "tax_category": tx.taxCategory,
            "direction": direction,
            "amount_cents": tx.amountCents,
            "amount_reais": round(tx.amountCents / 100.0, 2),
            "description": matched_note or f"Lançamento {tx.category}",
        })

    return {
        "driver": {
            "id": str(driver.id),
            "name": driver.name,
            "phone": driver.phone or "",
            "balance_cents": wallet.balanceCents,
            "balance_reais": round(wallet.balanceCents / 100.0, 2),
        },
        "transactions": transactions_list,
    }





