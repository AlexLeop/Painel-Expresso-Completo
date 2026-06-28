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
    Procura em StaffMember e PlatformAdmin e injeta as 'companies' (Store/Lojas) vinculadas.
    """
    uid = request.auth.get("sub")
    
    from accounts.models import PlatformAdmin, StaffMember
    from logistics.models import Store
    
    try:
        admin = PlatformAdmin.objects.get(supabase_uid=uid)
        
        # Puxa todos os operadores logísticos para que o Admin Master possa alternar no dropdown do frontend
        from accounts.models import Operator
        all_ops = Operator.objects.all()
        companies_list = [{"id": "global", "nome": "Administração Global"}]
        for op in all_ops:
            companies_list.append({
                "id": str(op.id),
                "nome": op.name
            })
            
        return {
            "authenticated": True,
            "user": {
                "id": str(admin.id),
                "email": admin.email,
                "name": admin.name,
                "role": "admin",
                "company_id": "global",
                "machine_empresa_id": "global",
                "companies": companies_list
            }
        }
    except PlatformAdmin.DoesNotExist:
        pass

    try:
        staff = StaffMember.objects.get(supabase_uid=uid, active=True)
        
        # Puxar todas as lojas (companies/clientes) atreladas ao Operador logístico deste funcionário
        stores = Store.objects.filter(operator_id=staff.operator_id)
        companies_list = [
            {
                "id": str(s.id),
                "nome": s.name,
                "documento": s.document if hasattr(s, 'document') else "",
            }
            for s in stores
        ]
        
        return {
            "authenticated": True,
            "user": {
                "id": str(staff.id),
                "email": staff.email,
                "name": staff.name,
                "role": staff.role.lower(),
                "company_id": str(staff.operator_id),
                "machine_empresa_id": str(staff.operator_id),
                "companies": companies_list if companies_list else [{"id": str(staff.operator_id), "nome": "Matriz Operador"}]
            }
        }
    except StaffMember.DoesNotExist:
        return panel_api.create_response(request, {"authenticated": False, "error": "Sua conta do Supabase não possui vínculos de permissões (Operador ou Admin) no sistema Logístico."}, status=403)

@panel_api.post("/auth/change-tenant")
def change_tenant(request, payload: dict):
    # Mock endpoint to prevent 404 from frontend
    return {"success": True}




@panel_api.get("/machine/rides")
def get_rides(
    request, 
    empresa_id: Optional[str] = None, 
    limite: int = 50, 
    pagina: int = 1, 
    status_solicitacao: Optional[str] = None,
    data_hora_solicitacao_min: Optional[str] = None,
    data_hora_solicitacao_max: Optional[str] = None
):
    from logistics.models import Order
    from accounts.models import Operator
    
    qs = Order.objects.select_related('driver').all().order_by("-requestedAt")
    
    if empresa_id and empresa_id != "global":
        from django.core.exceptions import ValidationError
        try:
            qs = qs.filter(operator_id=empresa_id)
        except ValidationError:
            qs = qs.none()
        
    if status_solicitacao:
        # Mapeamento basico do Taxi Machine status para o OrderStatus local
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

    # Paginação manual
    offset = (pagina - 1) * limite
    orders = qs[offset:offset + limite]
    
    return [
        {
            "id": str(o.id),
            "driver_id": str(o.driver_id) if o.driver_id else None,
            "motorista": o.driver.name if o.driver else "Não atribuído",
            "status": o.status,
            "price": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
            "valor_total": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
            "distance": (o.distanceMeters or 0) / 1000.0 if hasattr(o, 'distanceMeters') else 0,
            "data": o.requestedAt.strftime("%Y-%m-%d %H:%M:%S") if getattr(o, 'requestedAt', None) else None
        }
        for o in orders
    ]



@panel_api.get("/schedules")
def get_schedules(request, company_id: Optional[str] = None):
    from django.core.exceptions import ValidationError
    from logistics.models import ScheduleEntry
    qs = ScheduleEntry.objects.all()
    if company_id:
        try:
            qs = qs.filter(operator_id=company_id)
        except ValidationError:
            return []
    # Limita pra não explodir
    entries = qs.order_by("-date")[:100]
    return [
        {
            "id": str(e.id),
            "driverId": str(e.driver_id),
            "storeId": str(e.store_id),
            "turnoId": str(e.turno_id),
            "date": str(e.date),
            "minGuaranteedOverrideCents": e.minGuaranteedOverrideCents
        }
        for e in entries
    ]






@panel_api.get("/machine/companies", auth=auth_bearer)
def get_machine_companies(request):
    from accounts.models import StaffMember, Operator
    from logistics.models import Store
    
    uid = request.auth.get("sub")
    staff = StaffMember.objects.filter(supabase_uid=uid).first()
    
    if staff and staff.operator_id:
        stores = Store.objects.filter(operator_id=staff.operator_id)
        return {"companies": [{"id": str(s.id), "nome": s.name} for s in stores]}
    else:
        ops = Operator.objects.all()
        return {"companies": [{"id": str(o.id), "nome": o.name} for o in ops]}

@panel_api.get("/machine/drivers")
def get_machine_drivers(request, company_id: Optional[str] = None):
    from django.core.exceptions import ValidationError
    qs = Driver.objects.filter(active=True)
    if company_id:
        try:
            qs = qs.filter(operator_id=company_id)
        except ValidationError:
            return {"drivers": []}
    return {"drivers": [
        {
            "id": str(d.id),
            "nome": d.name,
            "telefone": getattr(d, 'phone', ''),
            "status": "Aprovado" if getattr(d, 'active', True) else "Bloqueado"
        }
        for d in qs
    ]}

@panel_api.get("/machine/credits/driver/balance")
def get_machine_driver_balance(request, condutor_id: str):
    from finance.models import Wallet
    try:
        w = Wallet.objects.get(driver_id=condutor_id)
        return {"saldo": w.balanceCents / 100.0}
    except Wallet.DoesNotExist:
        return {"saldo": 0.0}

@panel_api.get("/machine/rides/tracking")
def get_machine_ride_tracking(request, id_mch: str):
    return {"link_rastreamento": f"https://tracking.expressoneves.com/{id_mch}"}

from pydantic import BaseModel
from typing import List, Optional, Any

class StopPayload(BaseModel):
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

class RideCreatePayload(BaseModel):
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
    forma_pagamento_id: int = 1
    tipo_veiculo_id: int = 1
    paradas: List[StopPayload] = []
    retorno: bool = False

@panel_api.post("/machine/rides/create")
def post_machine_ride_create(request, payload: RideCreatePayload):
    from logistics.models import Store, Order, Stop
    from accounts.models import Operator
    from finance.models import KmFaixa
    from django.core.exceptions import ValidationError
    from django.contrib.gis.geos import Point
    import math
    from datetime import date
    
    try:
        operator = Operator.objects.get(id=payload.empresa_id)
    except (Operator.DoesNotExist, ValidationError):
        return panel_api.create_response(request, {"error": "Empresa inválida"}, status=400)
    
    store = Store.objects.filter(operator=operator).first()
    if not store:
        store = Store.objects.create(operator=operator, name="Store Default")
        
    lat1, lon1 = 0.0, 0.0
    try:
        lat1, lon1 = float(payload.lat_partida), float(payload.lng_partida)
    except (ValueError, TypeError):
        pass

    lat2, lon2 = lat1, lon1
    if payload.paradas and len(payload.paradas) > 0:
        try:
            lat2, lon2 = float(payload.paradas[-1].lat_parada), float(payload.paradas[-1].lng_parada)
        except (ValueError, TypeError):
            pass

    R = 6371.0
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distancia_km = (R * c) * 1.3
    distance_meters = int(distancia_km * 1000)

    valor_cents = 1000
    faixa = KmFaixa.objects.filter(operator=operator, kmStart__lte=distancia_km, kmEnd__gt=distancia_km).first()
    if faixa:
        valor_cents = faixa.priceCents
    else:
        faixa_max = KmFaixa.objects.filter(operator=operator).order_by('-kmEnd').first()
        if faixa_max and distancia_km >= faixa_max.kmEnd:
            valor_cents = faixa_max.priceCents
        elif KmFaixa.objects.filter(operator=operator).exists():
            faixa_min = KmFaixa.objects.filter(operator=operator).order_by('kmStart').first()
            if faixa_min:
                valor_cents = faixa_min.priceCents

    metadata = {
        "payment_method_id": payload.forma_pagamento_id,
        "vehicle_type_id": payload.tipo_veiculo_id,
        "return_required": payload.retorno
    }

    order = Order.objects.create(
        operator=operator,
        store=store,
        status=Order.OrderStatus.PREPARING,
        fareValueCents=valor_cents,
        distanceMeters=distance_meters,
        businessDate=date.today(),
        metadata=metadata
    )
    
    pickup_meta = {
        "address": f"{payload.endereco_partida}, {payload.numero_partida}",
        "neighborhood": payload.bairro_partida,
        "city": payload.cidade_partida,
        "state": payload.estado_partida,
        "zipcode": payload.cep_partida,
        "complement": payload.complemento_partida,
        "customer_name": payload.nome_cliente_partida,
        "customer_phone": payload.telefone_cliente_partida
    }
    
    Stop.objects.create(
        operator=operator,
        order=order,
        sequence=1,
        type=Stop.StopType.PICKUP,
        geom=Point(lon1, lat1),
        metadata=pickup_meta
    )
    
    seq = 2
    for parada in payload.paradas:
        p_lat, p_lon = 0.0, 0.0
        try:
            p_lat, p_lon = float(parada.lat_parada), float(parada.lng_parada)
        except (ValueError, TypeError):
            pass
            
        dropoff_meta = {
            "address": f"{parada.endereco_parada}, {parada.numero_parada}",
            "neighborhood": parada.bairro_parada,
            "city": parada.cidade_parada,
            "state": parada.estado_parada,
            "zipcode": parada.cep_parada,
            "complement": parada.complemento_parada,
            "customer_name": parada.nome_cliente_parada,
            "customer_phone": parada.telefone_cliente_parada,
            "observation": parada.observacao_parada
        }
        Stop.objects.create(
            operator=operator,
            order=order,
            sequence=seq,
            type=Stop.StopType.DROPOFF,
            geom=Point(p_lon, p_lat),
            metadata=dropoff_meta
        )
        seq += 1
        
    return {"response": {"id": str(order.id)}}

class RideCancelPayload(BaseModel):
    id_mch: str

@panel_api.post("/machine/rides/cancel")
def post_machine_ride_cancel(request, payload: RideCancelPayload):
    from django.core.exceptions import ValidationError
    try:
        order = Order.objects.get(id=payload.id_mch)
        order.status = Order.OrderStatus.CANCELED
        order.save()
        return {"success": True}
    except (Order.DoesNotExist, ValidationError):
        return panel_api.create_response(request, {"error": "Order not found"}, status=404)

@panel_api.get("/machine/rides/estimate", auth=auth_bearer)
def get_machine_rides_estimate(
    request, 
    endereco_partida: str = "", 
    bairro_partida: str = "", 
    cidade_partida: str = "", 
    estado_partida: str = "",
    lat_partida: str = "0", 
    lng_partida: str = "0", 
    endereco_desejado: str = "", 
    bairro_desejado: str = "", 
    cidade_desejado: str = "", 
    estado_desejado: str = "",
    lat_desejado: str = "0", 
    lng_desejado: str = "0"
):
    import math
    from finance.models import KmFaixa
    from accounts.models import StaffMember, Operator
    
    try:
        lat1, lon1 = float(lat_partida), float(lng_partida)
        lat2, lon2 = float(lat_desejado), float(lng_desejado)
        R = 6371.0
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distancia = R * c
    except (ValueError, TypeError):
        distancia = 0.0

    # Increase distance by 30% for street routing approximation
    distancia = distancia * 1.3
    
    uid = request.auth.get("sub")
    staff = StaffMember.objects.filter(supabase_uid=uid).first()
    operator_id = staff.operator_id if staff else None

    valor_cents = 1000 # default fallback R$ 10.00
    if operator_id:
        faixa = KmFaixa.objects.filter(operator_id=operator_id, kmStart__lte=distancia, kmEnd__gt=distancia).first()
        if faixa:
            valor_cents = faixa.priceCents
        else:
            faixa_max = KmFaixa.objects.filter(operator_id=operator_id).order_by('-kmEnd').first()
            if faixa_max and distancia >= faixa_max.kmEnd:
                valor_cents = faixa_max.priceCents
            elif KmFaixa.objects.filter(operator_id=operator_id).exists():
                faixa_min = KmFaixa.objects.filter(operator_id=operator_id).order_by('kmStart').first()
                if faixa_min:
                    valor_cents = faixa_min.priceCents

    return {
        "response": {
            "distancia": round(distancia, 2),
            "valor": valor_cents / 100.0
        }
    }

@panel_api.get("/machine/rides/receipt")
def get_machine_rides_receipt(request, solicitacao_id: str):
    from django.core.exceptions import ValidationError
    try:
        order = Order.objects.get(id=solicitacao_id)
        return {
            "recibo": {
                "id": str(order.id),
                "motorista": order.driver.name if order.driver else "Não atribuído",
                "valor_total": (order.fareValueCents / 100.0) if hasattr(order, 'fareValueCents') else 0.0,
                "status": order.status
            }
        }
    except (Order.DoesNotExist, ValidationError):
        return panel_api.create_response(request, {"error": "Order not found"}, status=404)


@panel_api.get("/admin/operators", auth=auth_bearer)
def get_operators(request):
    """
    Retorna a lista de Operadores (apenas para PlatformAdmin).
    """
    from accounts.models import PlatformAdmin, Operator
    uid = request.auth.get("sub")
    if not PlatformAdmin.objects.filter(supabase_uid=uid).exists():
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)
        
    ops = Operator.objects.all().order_by("-createdAt")
    res = []
    for o in ops:
        res.append({
            "id": str(o.id),
            "name": o.name,
            "cnpj": o.cnpj,
            "status": o.status
        })
    return res

@panel_api.post("/admin/operators", auth=auth_bearer)
def create_operator(request, payload: dict):
    """
    Cria um novo Operador Logístico e o seu primeiro Gerente (Owner).
    Payload: name, cnpj, managerName, managerEmail, managerPassword
    """
    from accounts.models import PlatformAdmin, Operator, StaffMember
    from config.supabase_client import get_supabase_admin
    import uuid
    
    uid = request.auth.get("sub")
    if not PlatformAdmin.objects.filter(supabase_uid=uid).exists():
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)
        
    name = payload.get("name")
    cnpj = payload.get("cnpj", "")
    manager_name = payload.get("managerName")
    manager_email = payload.get("managerEmail")
    manager_pwd = payload.get("managerPassword", "123456")
    
    if not name or not manager_name or not manager_email:
        return panel_api.create_response(request, {"error": "Dados obrigatórios faltando"}, status=400)
        
    try:
        # 1. Create Operator
        operator = Operator.objects.create(
            name=name,
            cnpj=cnpj,
            status=Operator.OperatorStatus.ACTIVE
        )
        
        # 2. Create Auth User for Manager in Supabase
        supabase_admin = get_supabase_admin()
        user_res = supabase_admin.auth.admin.create_user({
            "email": manager_email,
            "password": manager_pwd,
            "email_confirm": True,
            "user_metadata": {"name": manager_name, "role": "operator_owner"}
        })
        
        # 3. Create StaffMember
        StaffMember.objects.create(
            operator=operator,
            supabase_uid=user_res.user.id,
            name=manager_name,
            email=manager_email,
            role=StaffMember.RoleType.ADMIN,
            active=True
        )
        
        return {"success": True, "operatorId": str(operator.id)}
    except Exception as e:
        return panel_api.create_response(request, {"success": False, "error": str(e)}, status=500)



# Catch-all
@panel_api.api_operation(['GET', 'POST', 'PUT', 'DELETE'], '/{path:path}')
def catch_all(request, path: str):
    return {}
