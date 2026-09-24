import uuid
from ninja import Router, Schema
from typing import List, Optional
from accounts.models import PlatformAdmin, StaffMember, Operator
from accounts.auth import platform_admin_required, require_role
from logistics.models import ClientPortalUser
from django.db import IntegrityError, transaction
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
    platform_admin_required(request)
    if not data.admin_password or len(data.admin_password) < 10:
        raise HttpError(422, "A senha inicial deve ter pelo menos 10 caracteres.")
    email = data.admin_email.strip().lower()
    if (
        PlatformAdmin.objects.filter(email__iexact=email).exists()
        or StaffMember.objects.filter(email__iexact=email).exists()
        or ClientPortalUser.objects.filter(email__iexact=email).exists()
    ):
        raise HttpError(409, "Já existe um usuário com este e-mail.")

    try:
        with transaction.atomic():
            operator = Operator.objects.create(id=uuid.uuid4(), name=data.name, status="TRIAL")
            with tenant_context(operator.id):
                staff = StaffMember(
                    id=uuid.uuid4(), operator=operator, name=data.admin_name,
                    email=email, role="ADMIN", active=True,
                )
                staff.set_password(data.admin_password)
                staff.save()
            return operator
    except IntegrityError:
        raise HttpError(409, "Não foi possível criar o operador porque os dados já estão em uso.")


@router.post("/staff", response=StaffMemberSchemaOut)
def create_staff(request, data: CreateStaffSchema):
    """
    [Flow 2] Criação de StaffMember com hierarquia de regras nativa:
    - ADMIN cria ADMIN, MANAGER, OPERATOR_ROLE, VIEWER
    - MANAGER cria OPERATOR_ROLE, VIEWER
    - OPERATOR_ROLE / VIEWER não cria ninguém
    """
    actor = require_role(["ADMIN", "MANAGER"])(request)
    operator_id = actor.operator_id
    creator_role = actor.role
    requested_role = data.role.strip().upper()
    if requested_role not in StaffMember.RoleType.values:
        raise HttpError(422, "Papel de usuário inválido.")

    if creator_role == "MANAGER" and requested_role in ["ADMIN", "MANAGER"]:
        raise HttpError(403, "MANAGER não pode criar níveis iguais ou superiores.")
    if not data.password or len(data.password) < 10:
        raise HttpError(422, "A senha inicial deve ter pelo menos 10 caracteres.")
    email = data.email.strip().lower()
    if (
        PlatformAdmin.objects.filter(email__iexact=email).exists()
        or StaffMember.objects.filter(email__iexact=email).exists()
        or ClientPortalUser.objects.filter(email__iexact=email).exists()
    ):
        raise HttpError(409, "Já existe um usuário com este e-mail.")

    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)

        staff = StaffMember(
            id=uuid.uuid4(),
            operator=operator,
            name=data.name,
            email=data.email.strip().lower(),
            role=requested_role,
            active=True,
        )
        staff.set_password(data.password)
        try:
            staff.save()
            return staff
        except IntegrityError:
            raise HttpError(409, "Não foi possível criar o usuário porque os dados já estão em uso.")


@router.get("/staff", response=List[StaffMemberSchemaOut])
def list_staff(request):
    """Lista todos os membros da equipe do Operador logado."""
    operator_id = request.auth.get("operator_id")
    with tenant_context(operator_id):
        return StaffMember.objects.filter(operator_id=operator_id)
