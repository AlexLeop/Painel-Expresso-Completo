import uuid
import secrets
from ninja import Router, Schema
from typing import List, Optional
from accounts.models import StaffMember, Operator
from config.core_models import tenant_context
from ninja.errors import HttpError

router = Router(tags=["Admin - Accounts"])


class OperatorSchemaOut(Schema):
    id: str
    name: str
    status: str


class StaffMemberSchemaOut(Schema):
    id: str
    name: str
    email: str
    role: str
    active: bool


class CreateOperatorSchema(Schema):
    name: str
    subdomain: str
    admin_name: str
    admin_email: str
    admin_password: Optional[str] = None


class CreateStaffSchema(Schema):
    name: str
    email: str
    role: str
    password: Optional[str] = None


@router.post("/operator", response=OperatorSchemaOut)
def create_operator(request, data: CreateOperatorSchema):
    """
    [Flow 1] PlatformAdmin cria Operator e seu primeiro StaffMember(ADMIN).
    Acessível APENAS por token JWT com claim role='platform_admin' ou 'superadmin'
    """
    role = request.auth.get("role")
    if role not in ["platform_admin", "superadmin"] and not request.auth.get("is_platform_admin"):
        raise HttpError(
            403, "Acesso negado. Apenas PlatformAdmin pode criar Operadores."
        )

    # 1. Criar Operator no PostgreSQL
    operator = Operator.objects.create(id=uuid.uuid4(), name=data.name, status="TRIAL")

    # 2. Criar Staff Admin nativo com PBKDF2
    admin_pass = data.admin_password or secrets.token_urlsafe(12)
    with tenant_context(operator.id):
        staff = StaffMember(
            id=uuid.uuid4(),
            operator=operator,
            name=data.admin_name,
            email=data.admin_email.strip().lower(),
            role="ADMIN",
            active=True,
        )
        staff.set_password(admin_pass)
        staff.save()
    return operator


@router.post("/staff", response=StaffMemberSchemaOut)
def create_staff(request, data: CreateStaffSchema):
    """
    [Flow 2] Criação de StaffMember com hierarquia de regras nativa:
    - ADMIN cria ADMIN, MANAGER, OPERATOR_ROLE, VIEWER
    - MANAGER cria OPERATOR_ROLE, VIEWER
    - OPERATOR_ROLE / VIEWER não cria ninguém
    """
    operator_id = request.auth.get("operator_id")
    creator_role = request.auth.get("role")  # Lemos a role do JWT validado nativo

    if creator_role not in ["ADMIN", "MANAGER", "operador_admin"]:
        raise HttpError(403, "Permissão insuficiente para criar Staff.")

    if creator_role == "MANAGER" and data.role in ["ADMIN", "MANAGER"]:
        raise HttpError(403, "MANAGER não pode criar níveis iguais ou superiores.")

    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)

        staff_pass = data.password or secrets.token_urlsafe(12)
        staff = StaffMember(
            id=uuid.uuid4(),
            operator=operator,
            name=data.name,
            email=data.email.strip().lower(),
            role=data.role,
            active=True,
        )
        staff.set_password(staff_pass)
        staff.save()
        return staff


@router.get("/staff", response=List[StaffMemberSchemaOut])
def list_staff(request):
    """Lista todos os membros da equipe do Operador logado."""
    operator_id = request.auth.get("operator_id")
    with tenant_context(operator_id):
        return StaffMember.objects.filter(operator_id=operator_id)
