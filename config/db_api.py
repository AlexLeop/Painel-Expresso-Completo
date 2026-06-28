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
    from django.core.exceptions import ValidationError
    # This is a compatibility layer mapping legacy React queries to ManualEntry
    qs = ManualEntry.objects.all()
    if company_id and company_id != "global":
        try:
            qs = qs.filter(operator_id=company_id)
        except ValidationError:
            pass
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
    return [{"id": str(u.id), "nome": u.name, "name": u.name, "email": u.email, "role": u.role} for u in users]

class UserPayload(BaseModel):
    id: Optional[str] = None
    fullName: str
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    companyId: Optional[str] = None

@router.post("/users")
def create_user(request, payload: UserPayload):
    from accounts.models import StaffMember, Operator
    from config.supabase_client import get_supabase_admin
    try:
        if not payload.email:
            return {"success": False, "error": "Email is required"}
            
        supabase_admin = get_supabase_admin()
        user_res = supabase_admin.auth.admin.create_user({
            "email": payload.email,
            "password": payload.password or "123456",
            "email_confirm": True,
            "user_metadata": {"name": payload.fullName, "role": payload.role or "staff"}
        })
        operator = None
        if payload.companyId and payload.companyId != "global":
            operator = Operator.objects.filter(id=payload.companyId).first()
        StaffMember.objects.create(
            supabase_uid=user_res.user.id,
            name=payload.fullName,
            email=payload.email,
            role=payload.role or "staff",
            operator=operator,
            active=True
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.put("/users")
def update_user(request, payload: UserPayload):
    from accounts.models import StaffMember, PlatformAdmin
    try:
        staff = StaffMember.objects.get(id=payload.id)
        staff.name = payload.fullName
        if payload.role: staff.role = payload.role
        staff.save()
        return {"success": True}
    except StaffMember.DoesNotExist:
        try:
            admin = PlatformAdmin.objects.get(id=payload.id)
            admin.name = payload.fullName
            admin.save()
            return {"success": True}
        except PlatformAdmin.DoesNotExist:
            return {"success": False, "error": "User not found"}

@router.delete("/users")
def delete_user(request, id: str):
    from accounts.models import StaffMember, PlatformAdmin
    from config.supabase_client import get_supabase_admin
    try:
        try:
            user = StaffMember.objects.get(id=id)
        except StaffMember.DoesNotExist:
            user = PlatformAdmin.objects.get(id=id)
        
        # Delete from Supabase
        supabase_admin = get_supabase_admin()
        supabase_admin.auth.admin.delete_user(str(user.supabase_uid))
        
        # Delete local
        user.delete()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

class CompanyDriverPayload(BaseModel):
    driver_id: Optional[str] = None
    company_id: Optional[int] = None
    active: Optional[bool] = None

@router.get("/company-drivers")
def get_company_drivers(request, company_id: Optional[str] = None, active_only: int = 0):
    from django.core.exceptions import ValidationError
    from logistics.models import StoreDriver, Store
    qs = StoreDriver.objects.select_related('driver').all()
    if company_id and company_id != "global":
        try:
            store = Store.objects.filter(operator_id=company_id).first()
        except ValidationError:
            store = None
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
    phone: Optional[str] = None
    telefone: Optional[str] = None
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
    phone = payload.phone or payload.telefone
    email = payload.email
    password = payload.password
    
    if not all([company_id, nome, phone, email]):
        return {"success": False, "error": "Dados insuficientes (companyId, nome, phone/telefone, email são obrigatórios)"}
    
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
def get_configs(request, company_id: Optional[str] = None, company_name: Optional[str] = None):
    from django.core.exceptions import ValidationError
    from accounts.models import Operator
    if company_id and company_id != "global":
        try:
            op = Operator.objects.filter(id=company_id).first()
        except ValidationError:
            op = None
        if op:
            return {"id": str(op.id), "nome": op.name, "company_id": str(op.id), "features": {}}
    return {"company_id": company_id, "features": {}}

@router.post("/configs")
def create_config(request, payload: dict):
    return {"success": True}

@router.put("/configs")
def update_config(request, payload: dict):
    return {"success": True}

@router.get("/snapshots")
def get_snapshots(request, company_id: Optional[str] = None, limit: int = 50):
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

# ==============================================================================
# UNIFIED NATIVE ORDERS API (Replaces Legacy Taxi Machine Proxy)
# ==============================================================================

from typing import List, Optional

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
    
    qs = Order.objects.select_related('driver').all().order_by("-requestedAt")
    
    if empresa_id and empresa_id != "global":
        try:
            qs = qs.filter(operator_id=empresa_id)
        except ValidationError:
            qs = qs.none()
        
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
    
    return [
        {
            "id": str(o.id),
            "driver_id": str(o.driver_id) if o.driver_id else None,
            "motorista": o.driver.name if getattr(o, 'driver', None) else "Não atribuído",
            "status": o.status,
            "price": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
            "valor_total": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
            "distance": (o.distanceMeters or 0) / 1000.0 if hasattr(o, 'distanceMeters') else 0,
            "data": o.requestedAt.strftime("%Y-%m-%d %H:%M:%S") if getattr(o, 'requestedAt', None) else None
        }
        for o in orders
    ]

@router.post("/orders/create")
def create_order(request, payload: OrderCreateSchema):
    from logistics.models import Order, Stop
    from django.contrib.gis.geos import Point
    from accounts.models import Operator
    
    try:
        operator_id = payload.empresa_id if payload.empresa_id != "global" else None
        
        order = Order.objects.create(
            operator_id=operator_id,
            status=Order.OrderStatus.OFFERED,
            fareValueCents=int((payload.valor_estimado or 0) * 100),
            distanceMeters=int((payload.distancia_estimada or 0) * 1000)
        )
        
        # Origin Stop
        Stop.objects.create(
            order=order,
            sequence=0,
            type=Stop.StopType.PICKUP,
            geom=Point(float(payload.lng_partida), float(payload.lat_partida), srid=4326),
            address=f"{payload.endereco_partida}, {payload.numero_partida} - {payload.bairro_partida}",
            contactName=payload.nome_cliente_partida,
            contactPhone=payload.telefone_cliente_partida
        )
        
        # Destinations
        for idx, stop in enumerate(payload.pontos, start=1):
            Stop.objects.create(
                order=order,
                sequence=idx,
                type=Stop.StopType.DROPOFF,
                geom=Point(float(stop.lng_parada), float(stop.lat_parada), srid=4326),
                address=f"{stop.endereco_parada}, {stop.numero_parada} - {stop.bairro_parada}",
                contactName=stop.nome_cliente_parada,
                contactPhone=stop.telefone_cliente_parada
            )
            
        return {"sucesso": True, "solicitacao_id": str(order.id), "msg": "Pedido criado localmente com sucesso"}
    except Exception as e:
        return {"sucesso": False, "msg": str(e)}

class OrderCancelPayload(BaseModel):
    solicitacao_id: str

@router.post("/orders/cancel")
def cancel_order(request, payload: OrderCancelPayload):
    from logistics.models import Order
    try:
        order = Order.objects.get(id=payload.solicitacao_id)
        order.status = Order.OrderStatus.CANCELED
        order.save()
        return {"sucesso": True, "msg": "Cancelado com sucesso"}
    except Order.DoesNotExist:
        return {"sucesso": False, "msg": "Corrida não encontrada"}
    except Exception as e:
        return {"sucesso": False, "msg": str(e)}

@router.get("/orders/estimate")
def estimate_order(request, payload: Optional[dict] = None):
    # Native mock estimation for MVP phase
    return {
        "sucesso": True,
        "valor_total": 15.50,
        "distancia_total": 5.2,
        "tempo_total": 12,
        "msg": "Estimativa nativa"
    }

@router.get("/driver-balance")
def get_driver_balance(request, driver_id: str):
    from finance.models import Wallet
    try:
        w = Wallet.objects.get(driver_id=driver_id)
        return {"saldo": w.balanceCents / 100.0}
    except Wallet.DoesNotExist:
        return {"saldo": 0.0}
