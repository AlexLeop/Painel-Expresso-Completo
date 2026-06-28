from ninja import Router
from typing import List, Dict, Any, Optional
from django.shortcuts import get_object_or_404
from pydantic import BaseModel
from finance.models import ManualEntry
from logistics.models import Driver, Store
from accounts.models import Operator

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
    # This is a compatibility layer mapping legacy React queries to ManualEntry
    qs = ManualEntry.objects.all()
    if company_id:
        qs = qs.filter(operator_id=company_id)
    if start:
        qs = qs.filter(createdAt__gte=start)
    if end:
        qs = qs.filter(createdAt__lte=end)
        
    res = []
    for entry in qs:
        res.append({
            "id": str(entry.id),
            "driverName": entry.driver.name if entry.driver_id else "",
            "motoboy": entry.driver.name if entry.driver_id else "",
            "type": entry.description,
            "categoria": "Crédito" if entry.amountCents > 0 else "Débito",
            "valor": entry.amountCents / 100.0,
            "data": entry.createdAt.strftime("%Y-%m-%d"),
            "description": entry.description
        })
    return res

@router.post("/entries")
def create_entry(request, payload: EntryPayload):
    company_id = payload.company_id or payload.companyId
    operator = get_object_or_404(Operator, pk=company_id)
    
    driver = None
    if payload.driverId and payload.driverId != "9999":
        driver = Driver.objects.filter(id=payload.driverId).first()
        
    amt_cents = int((payload.amount or 0) * 100)
    
    entry = ManualEntry.objects.create(
        operator=operator,
        driver=driver,
        amountCents=amt_cents,
        description=payload.description or payload.type or "",
        status=ManualEntry.EntryStatus.APPROVED
    )
    return {"success": True, "id": str(entry.id)}

@router.put("/entries")
def update_entry(request, payload: EntryPayload):
    if not payload.id:
        return {"success": False, "error": "ID missing"}
    
    entry = get_object_or_404(ManualEntry, pk=payload.id)
    if payload.amount is not None:
        entry.amountCents = int(payload.amount * 100)
    if payload.description or payload.type:
        entry.description = payload.description or payload.type or entry.description
    entry.save()
    
    return {"success": True}

@router.delete("/entries")
def delete_entry(request, id: str):
    entry = get_object_or_404(ManualEntry, pk=id)
    entry.delete()
    return {"success": True}

@router.get("/companies")
def get_companies(request):
    ops = Operator.objects.all()
    return [{"id": str(o.id), "nome": o.name, "name": o.name} for o in ops]

@router.get("/users")
def get_users(request):
    from accounts.models import StaffMember
    users = StaffMember.objects.all()
    return [{"id": str(u.id), "nome": u.name, "email": u.email, "role": u.role} for u in users]

class CompanyDriverPayload(BaseModel):
    driver_id: Optional[str] = None
    company_id: Optional[int] = None
    active: Optional[bool] = None

@router.get("/company-drivers")
def get_company_drivers(request, company_id: Optional[int] = None, active_only: int = 0):
    from logistics.models import StoreDriver, Store
    qs = StoreDriver.objects.select_related('driver').all()
    if company_id:
        store = Store.objects.filter(operator_id=company_id).first()
        if store:
            qs = qs.filter(store=store)
        else:
            qs = qs.none()
    
    res = []
    for sd in qs:
        res.append({
            "id": sd.id,
            "driverId": str(sd.driver.id),
            "nome": sd.driver.name,
            "phone": sd.driver.phone,
            "active": sd.driver.active
        })
    return res

@router.patch("/company-drivers")
def update_company_driver(request, payload: CompanyDriverPayload):
    from logistics.models import Driver
    try:
        if not payload.driver_id:
            return {"success": False, "error": "driver_id is required"}
            
        driver = Driver.objects.get(id=payload.driver_id)
        if payload.active is not None:
            driver.active = payload.active
            driver.save()
        return {"success": True}
    except Driver.DoesNotExist:
        return {"success": False, "error": "Driver not found"}

class DriverCreateSchema(BaseModel):
    companyId: str
    nome: str
    phone: str
    email: str
    password: Optional[str] = "123456"
    document: Optional[str] = None
    pixKeyType: str = "TELEFONE"
    pixKey: str = ""
    maxActiveOrders: int = 3
    tax_classification: str = "PESSOA_FISICA_AUTONOMO"

@router.post("/company-drivers")
def create_company_driver(request, payload: DriverCreateSchema):
    """
    Cadastra um novo motoboy. Cria usuário no Supabase Auth usando o Admin SDK,
    e persiste o Driver no BD.
    Payload expected: companyId (str), nome (str), phone (str), email (str), password (opt)
    """
    from accounts.models import Operator
    from logistics.models import Driver, Store, StoreDriver
    from config.supabase_client import get_supabase_admin
    import uuid

    company_id = payload.companyId
    nome = payload.nome
    phone = payload.phone
    email = payload.email
    password = payload.password
    
    if not all([company_id, nome, phone, email]):
        return {"success": False, "error": "Dados insuficientes (companyId, nome, phone, email são obrigatórios)"}
    
    try:
        operator = Operator.objects.get(id=company_id)
        
        # 1. Criar Auth User no Supabase
        supabase_admin = get_supabase_admin()
        user_res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password or "123456",
            "email_confirm": True,
            "user_metadata": {"name": nome, "role": "driver"}
        })
        
        supa_uid = user_res.user.id
        
        # 2. Criar Driver record
        driver = Driver.objects.create(
            operator=operator,
            supabase_uid=supa_uid,
            name=nome,
            phone=phone,
            document=payload.document,
            pixKeyType=payload.pixKeyType,
            pixKey=payload.pixKey or phone,
            maxActiveOrders=payload.maxActiveOrders,
            tax_classification=payload.tax_classification
        )
        
        # 3. Vincular a uma Store do operador (primeira Store encontrada ou criar genérica)
        store = Store.objects.filter(operator_id=operator.id).first()
        if store:
            StoreDriver.objects.create(
                store=store,
                driver=driver,
                active=True
            )
            
        return {"success": True, "driverId": str(driver.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}

class StoreCreateSchema(BaseModel):
    companyId: str
    name: str
    documento: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    averagePrepTimeMinutes: int = 15

@router.post("/companies")
def create_company_store(request, payload: StoreCreateSchema):
    """
    Cadastra uma nova Empresa/Loja (Store) para o Operador logístico.
    Payload expected: companyId (operator), name, documento, endereco, lat, lng
    """
    from accounts.models import Operator
    from logistics.models import Store, Client
    import uuid

    operator_id = payload.companyId
    name = payload.name
    
    if not operator_id or not name:
        return {"success": False, "error": "operator_id (companyId) e name obrigatórios"}
        
    try:
        operator = Operator.objects.get(id=operator_id)
        # Criar um Client base para a Store
        client = Client.objects.create(
            operator=operator,
            name=name,
            document=payload.documento or ""
        )
        
        # Criar Store
        lat = payload.lat
        lng = payload.lng
        geom = None
        if lat and lng:
            from django.contrib.gis.geos import Point
            geom = Point(lng, lat, srid=4326)
            
        store = Store.objects.create(
            operator=operator,
            client=client,
            name=name,
            geom=geom,
            averagePrepTimeMinutes=payload.averagePrepTimeMinutes
        )
        
        return {"success": True, "storeId": str(store.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}
@router.get("/configs")
def get_configs(request, company_id: Optional[int] = None):
    # Return mock config to prevent frontend crash
    return [{"id": 1, "company_id": company_id or 1, "chave": "tema", "valor": "light"}]

@router.post("/configs")
def create_config(request, payload: dict):
    return {"success": True}

@router.put("/configs")
def update_config(request, payload: dict):
    return {"success": True}

@router.get("/snapshots")
def get_snapshots(request, company_id: Optional[int] = None, limit: int = 50):
    # Mock snapshot to prevent crash in dashboards
    return []

@router.get("/positions")
def get_positions(request, max_age_minutes: int = 720, limit: int = 1000):
    # Return empty positions array
    return []


class StoreUpdateSchema(BaseModel):
    name: Optional[str] = None
    documento: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    averagePrepTimeMinutes: Optional[int] = None
    status: Optional[str] = None

@router.put('/companies/{company_id}')
def update_company_store(request, company_id: str, payload: StoreUpdateSchema):
    from logistics.models import Store
    from django.contrib.gis.geos import Point
    try:
        store = Store.objects.get(id=company_id)
        if payload.name is not None:
            store.name = payload.name
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
            
        return {'success': True}
    except Store.DoesNotExist:
        return {'success': False, 'error': 'Store not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.delete('/companies/{company_id}')
def delete_company_store(request, company_id: str):
    from logistics.models import Store
    try:
        store = Store.objects.get(id=company_id)
        store.delete()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}
