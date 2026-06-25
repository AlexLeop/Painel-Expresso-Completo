from ninja import Router
from typing import List
from accounts.models import StaffMember, Operator
from ninja import Schema
from config.core_models import tenant_context
from ninja.errors import HttpError
import uuid

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

class CreateStaffSchema(Schema):
    name: str
    email: str
    role: str

@router.post("/operator", response=OperatorSchemaOut)
def create_operator(request, data: CreateOperatorSchema):
    """
    [Flow 1] PlatformAdmin cria Operator e seu primeiro StaffMember(ADMIN).
    Acessível APENAS por token JWT com claim role='platform_admin'
    """
    if request.auth.get('role') != 'platform_admin':
        raise HttpError(403, "Acesso negado. Apenas PlatformAdmin pode criar Operadores.")
    
    # Validação de Subdomínio seria inserida aqui para Nginx proxy pass
    
    # Criar Operator
    operator = Operator.objects.create(name=data.name, status='TRIAL')
    
    # A integração com Supabase.inviteUserByEmail ocorre aqui
    supabase_uid = uuid.uuid4() # TODO: Supabase Admin Client invite_user_by_email()
    
    # Criar Staff Admin
    with tenant_context(operator.id):
        StaffMember.objects.create(
            operator=operator,
            name=data.admin_name,
            email=data.admin_email,
            role='ADMIN',
            supabase_uid=supabase_uid
        )
    return operator

@router.post("/staff", response=StaffMemberSchemaOut)
def create_staff(request, data: CreateStaffSchema):
    """
    [Flow 2] Criação de StaffMember com hierarquia de regras:
    - ADMIN cria ADMIN, MANAGER, OPERATOR_ROLE, VIEWER
    - MANAGER cria OPERATOR_ROLE, VIEWER
    - OPERATOR_ROLE / VIEWER não cria ninguém
    """
    operator_id = request.auth.get('operator_id')
    creator_role = request.auth.get('role') # Lemos a role do JWT validado pelo gateway
    
    if creator_role not in ['ADMIN', 'MANAGER']:
        raise HttpError(403, "Permissão insuficiente para criar Staff.")
        
    if creator_role == 'MANAGER' and data.role in ['ADMIN', 'MANAGER']:
        raise HttpError(403, "MANAGER não pode criar níveis iguais ou superiores.")
        
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        
        supabase_uid = uuid.uuid4() # TODO: Supabase Admin Client invite_user_by_email()
        
        staff = StaffMember.objects.create(
            operator=operator,
            name=data.name,
            email=data.email,
            role=data.role,
            supabase_uid=supabase_uid
        )
        return staff

@router.get("/staff", response=List[StaffMemberSchemaOut])
def list_staff(request):
    """Lista todos os membros da equipe do Operador logado."""
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        return StaffMember.objects.filter(operator_id=operator_id)
