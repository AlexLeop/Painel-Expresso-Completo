from ninja import NinjaAPI, Router, Schema
from typing import Optional
from logistics.models import Driver, Order
from accounts.models import Operator, StaffMember, PlatformAdmin
from accounts.auth import NativeJWTAuth
from accounts.api import handle_login, handle_me, handle_refresh, handle_logout, LoginPayload, RefreshPayload


class OperatorCreateSchema(Schema):
    name: str
    cnpj: Optional[str] = ""
    phone: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    billingPlanType: str = "PERCENT_PER_DELIVERY"
    billingRateValue: float = 0.0
    billingCycle: str = "MENSAL"
    dueDay: int = 10
    trialDays: int = 14
    gracePeriodDays: int = 5
    notes: Optional[str] = ""
    managerName: str
    managerEmail: str
    managerPassword: str = "123456"


class OperatorUpdateSchema(Schema):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    billingPlanType: Optional[str] = None
    billingRateValue: Optional[float] = None
    billingCycle: Optional[str] = None
    dueDay: Optional[int] = None
    trialDays: Optional[int] = None
    gracePeriodDays: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class OperatorStatusSchema(Schema):
    status: str


class OperatorPasswordResetSchema(Schema):
    newPassword: str = "123456"


panel_api = NinjaAPI(urls_namespace="panel_api", auth=NativeJWTAuth())

auth_bearer = NativeJWTAuth()

@panel_api.post("/auth/login", auth=None, tags=["Native Auth Panel"])
def panel_login(request, payload: LoginPayload):
    return handle_login(request, payload)

@panel_api.get("/auth/me", tags=["Native Auth Panel"])
def panel_me(request):
    return handle_me(request)

@panel_api.post("/auth/refresh", auth=None, tags=["Native Auth Panel"])
def panel_refresh(request, payload: RefreshPayload):
    return handle_refresh(request, payload)

@panel_api.post("/auth/logout", tags=["Native Auth Panel"])
def panel_logout(request):
    return handle_logout(request)

@panel_api.post("/auth/change-tenant")
def change_tenant(request, payload: dict):
    # Endpoint to allow Superadmin switching active tenant header/context
    return {"success": True, "selected_tenant": payload.get("tenant_id")}




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
    from django.core.exceptions import ValidationError

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    auth_op_id = auth.get("operator_id")
    client_id = auth.get("client_id")
    
    qs = Order.objects.select_related('driver', 'store').all().order_by("-requestedAt")
    if client_id:
        qs = qs.filter(store__client_id=client_id)
    elif not is_admin and auth_op_id:
        qs = qs.filter(operator_id=auth_op_id)
    elif empresa_id and empresa_id != "global":
        try:
            qs = qs.filter(operator_id=empresa_id)
        except ValidationError:
            qs = qs.none()
    elif not is_admin:
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

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    auth_op_id = auth.get("operator_id")

    qs = ScheduleEntry.objects.all()
    if not is_admin and auth_op_id:
        qs = qs.filter(operator_id=auth_op_id)
    elif company_id and company_id != "global":
        try:
            qs = qs.filter(operator_id=company_id)
        except ValidationError:
            return []
    elif not is_admin:
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
    from logistics.models import Store
    
    is_admin = request.auth.get("is_platform_admin", False)
    if is_admin:
        ops = Operator.objects.all()
        return {"companies": [{"id": str(o.id), "nome": o.name} for o in ops]}

    uid = request.auth.get("sub")
    staff = StaffMember.objects.filter(id=uid).first() or StaffMember.objects.filter(supabase_uid=uid).first()
    
    if staff and staff.operator_id:
        stores = Store.objects.filter(operator_id=staff.operator_id)
        return {"companies": [{"id": str(s.id), "nome": s.name} for s in stores]}
    return {"companies": []}

@panel_api.get("/machine/drivers")
def get_machine_drivers(request, company_id: Optional[str] = None):
    from django.core.exceptions import ValidationError

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    auth_op_id = auth.get("operator_id")

    qs = Driver.objects.filter(active=True)
    if not is_admin and auth_op_id:
        qs = qs.filter(operator_id=auth_op_id)
    elif company_id and company_id != "global":
        try:
            qs = qs.filter(operator_id=company_id)
        except ValidationError:
            return {"drivers": []}
    elif not is_admin:
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
    staff = StaffMember.objects.filter(id=uid).first() or StaffMember.objects.filter(supabase_uid=uid).first()
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


def is_request_platform_admin(request):
    is_admin = request.auth.get("is_platform_admin", False)
    uid = request.auth.get("sub")
    if is_admin:
        return True
    if PlatformAdmin.objects.filter(id=uid).exists() or PlatformAdmin.objects.filter(supabase_uid=uid).exists():
        return True
    return False


@panel_api.get("/admin/operators", auth=auth_bearer)
def get_operators(request):
    """
    Retorna a lista de Operadores (apenas para PlatformAdmin).
    """
    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)
        
    ops = Operator.objects.all().order_by("-createdAt")
    res = []
    from logistics.models import Store, Driver
    for o in ops:
        manager = StaffMember.objects.filter(operator=o, role=StaffMember.RoleType.ADMIN).order_by("createdAt").first()
        try:
            stores_count = Store.objects.filter(operator_id=o.id).count()
        except Exception:
            stores_count = 0
        try:
            drivers_count = Driver.objects.filter(operator_id=o.id).count()
        except Exception:
            drivers_count = 0

        res.append({
            "id": str(o.id),
            "name": o.name,
            "cnpj": o.cnpj or "",
            "phone": getattr(o, "phone", "") or "",
            "city": getattr(o, "city", "") or "",
            "state": getattr(o, "state", "") or "",
            "billingPlanType": getattr(o, "billingPlanType", "PERCENT_PER_DELIVERY"),
            "billingRateValue": float(getattr(o, "billingRateValue", 0.0) or 0.0),
            "billingCycle": getattr(o, "billingCycle", "MENSAL"),
            "dueDay": getattr(o, "dueDay", 10) or 10,
            "trialDays": getattr(o, "trialDays", 14) or 14,
            "gracePeriodDays": getattr(o, "gracePeriodDays", 5) or 5,
            "notes": getattr(o, "notes", "") or "",
            "status": o.status,
            "createdAt": o.createdAt.isoformat() if hasattr(o, "createdAt") and o.createdAt else None,
            "managerName": manager.name if manager else None,
            "managerEmail": manager.email if manager else None,
            "storesCount": stores_count,
            "driversCount": drivers_count,
        })
    return res


@panel_api.get("/admin/operators/{operator_id}", auth=auth_bearer)
def get_operator_detail(request, operator_id: str):
    """
    Retorna os detalhes completos de um Operador específico.
    """
    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)

    try:
        o = Operator.objects.get(id=operator_id)
    except Operator.DoesNotExist:
        return panel_api.create_response(request, {"error": "Operador não encontrado"}, status=404)

    manager = StaffMember.objects.filter(operator=o, role=StaffMember.RoleType.ADMIN).order_by("createdAt").first()
    from logistics.models import Store, Driver
    try:
        stores_count = Store.objects.filter(operator_id=o.id).count()
    except Exception:
        stores_count = 0
    try:
        drivers_count = Driver.objects.filter(operator_id=o.id).count()
    except Exception:
        drivers_count = 0

    return {
        "id": str(o.id),
        "name": o.name,
        "cnpj": o.cnpj or "",
        "phone": getattr(o, "phone", "") or "",
        "city": getattr(o, "city", "") or "",
        "state": getattr(o, "state", "") or "",
        "billingPlanType": getattr(o, "billingPlanType", "PERCENT_PER_DELIVERY"),
        "billingRateValue": float(getattr(o, "billingRateValue", 0.0) or 0.0),
        "billingCycle": getattr(o, "billingCycle", "MENSAL"),
        "dueDay": getattr(o, "dueDay", 10) or 10,
        "trialDays": getattr(o, "trialDays", 14) or 14,
        "gracePeriodDays": getattr(o, "gracePeriodDays", 5) or 5,
        "notes": getattr(o, "notes", "") or "",
        "status": o.status,
        "createdAt": o.createdAt.isoformat() if hasattr(o, "createdAt") and o.createdAt else None,
        "updatedAt": o.updatedAt.isoformat() if hasattr(o, "updatedAt") and o.updatedAt else None,
        "managerName": manager.name if manager else None,
        "managerEmail": manager.email if manager else None,
        "storesCount": stores_count,
        "driversCount": drivers_count,
    }


@panel_api.post("/admin/operators", auth=auth_bearer)
def create_operator(request, payload: OperatorCreateSchema):
    """
    Cria um novo Operador Logístico com plano SaaS e o seu primeiro Gerente (Owner) de forma 100% nativa.
    """
    import uuid
    
    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado: requer privilégios de Superadmin."}, status=403)
        
    if not payload.name or not payload.managerName or not payload.managerEmail:
        return panel_api.create_response(request, {"error": "Dados obrigatórios faltando"}, status=400)
        
    try:
        initial_status = Operator.OperatorStatus.TRIAL if payload.trialDays > 0 else Operator.OperatorStatus.ACTIVE
        operator = Operator.objects.create(
            id=uuid.uuid4(),
            name=payload.name,
            cnpj=payload.cnpj or "",
            phone=payload.phone or "",
            city=payload.city or "",
            state=payload.state or "",
            billingPlanType=payload.billingPlanType or "PERCENT_PER_DELIVERY",
            billingRateValue=payload.billingRateValue or 0.0,
            billingCycle=payload.billingCycle or "MENSAL",
            dueDay=payload.dueDay or 10,
            trialDays=payload.trialDays if payload.trialDays is not None else 14,
            gracePeriodDays=payload.gracePeriodDays if payload.gracePeriodDays is not None else 5,
            notes=payload.notes or "",
            status=initial_status
        )
        
        staff = StaffMember(
            id=uuid.uuid4(),
            operator=operator,
            name=payload.managerName,
            email=payload.managerEmail.strip().lower(),
            role=StaffMember.RoleType.ADMIN,
            active=True
        )
        staff.set_password(payload.managerPassword or "123456")
        staff.save()
        
        return {"success": True, "operatorId": str(operator.id), "staffId": str(staff.id)}
    except Exception as e:
        return panel_api.create_response(request, {"success": False, "error": str(e)}, status=500)


@panel_api.put("/admin/operators/{operator_id}", auth=auth_bearer)
def update_operator(request, operator_id: str, payload: OperatorUpdateSchema):
    """
    Atualiza os dados cadastrais e as configurações de faturamento SaaS de um Operador.
    """
    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)

    try:
        o = Operator.objects.get(id=operator_id)
    except Operator.DoesNotExist:
        return panel_api.create_response(request, {"error": "Operador não encontrado"}, status=404)

    try:
        if payload.name is not None:
            o.name = payload.name
        if payload.cnpj is not None:
            o.cnpj = payload.cnpj
        if payload.phone is not None:
            o.phone = payload.phone
        if payload.city is not None:
            o.city = payload.city
        if payload.state is not None:
            o.state = payload.state
        if payload.billingPlanType is not None:
            o.billingPlanType = payload.billingPlanType
        if payload.billingRateValue is not None:
            o.billingRateValue = payload.billingRateValue
        if payload.billingCycle is not None:
            o.billingCycle = payload.billingCycle
        if payload.dueDay is not None:
            o.dueDay = payload.dueDay
        if payload.trialDays is not None:
            o.trialDays = payload.trialDays
        if payload.gracePeriodDays is not None:
            o.gracePeriodDays = payload.gracePeriodDays
        if payload.notes is not None:
            o.notes = payload.notes
        if payload.status is not None:
            o.status = payload.status
        o.save()
        return {"success": True, "operatorId": str(o.id)}
    except Exception as e:
        return panel_api.create_response(request, {"success": False, "error": str(e)}, status=500)


@panel_api.patch("/admin/operators/{operator_id}/status", auth=auth_bearer)
def update_operator_status(request, operator_id: str, payload: OperatorStatusSchema):
    """
    Atualiza o status de assinatura/operação de um Operador (ACTIVE, TRIAL, SUSPENDED, CANCELED).
    """
    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)

    try:
        o = Operator.objects.get(id=operator_id)
    except Operator.DoesNotExist:
        return panel_api.create_response(request, {"error": "Operador não encontrado"}, status=404)

    valid_statuses = [c[0] for c in Operator.OperatorStatus.choices]
    if payload.status not in valid_statuses:
        return panel_api.create_response(request, {"error": f"Status inválido. Escolha entre: {valid_statuses}"}, status=400)

    o.status = payload.status
    o.save(update_fields=["status"])
    return {"success": True, "operatorId": str(o.id), "newStatus": o.status}


@panel_api.post("/admin/operators/{operator_id}/reset-password", auth=auth_bearer)
def reset_operator_manager_password(request, operator_id: str, payload: OperatorPasswordResetSchema):
    """
    Redefine a senha do Gerente Master do Operador Logístico.
    """
    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado"}, status=403)

    try:
        o = Operator.objects.get(id=operator_id)
    except Operator.DoesNotExist:
        return panel_api.create_response(request, {"error": "Operador não encontrado"}, status=404)

    manager = StaffMember.objects.filter(operator=o, role=StaffMember.RoleType.ADMIN).order_by("createdAt").first()
    if not manager:
        return panel_api.create_response(request, {"error": "Nenhum gerente administrativo encontrado para este operador"}, status=404)

    if not payload.newPassword or len(payload.newPassword) < 4:
        return panel_api.create_response(request, {"error": "A senha deve ter pelo menos 4 caracteres"}, status=400)

    manager.set_password(payload.newPassword)
    manager.save(update_fields=["passwordHash"])
    return {"success": True, "managerEmail": manager.email, "message": "Senha redefinida com sucesso!"}




# Catch-all
@panel_api.api_operation(['GET', 'POST', 'PUT', 'DELETE'], '/{path:path}', auth=None)
def catch_all(request, path: str):
    return {}
