import logging

from ninja import NinjaAPI, Router, Schema
from ninja.errors import HttpError
from typing import Optional
from logistics.models import Driver, Order
from accounts.models import Operator, StaffMember, PlatformAdmin
from accounts.auth import NativeJWTAuth, get_client_portal_user, require_role
from accounts.api import (
    LoginPayload,
    RefreshPayload,
    handle_me,
    login_endpoint,
    logout_endpoint,
    refresh_endpoint,
)

logger = logging.getLogger(__name__)


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
    managerPassword: str


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
    newPassword: str


panel_api = NinjaAPI(urls_namespace="panel_api", auth=NativeJWTAuth())

auth_bearer = NativeJWTAuth()


def _panel_actor(request, roles, *, allow_client: bool = False):
    auth = getattr(request, "auth", None) or {}
    if auth.get("client_id") or auth.get("user_type") == "client_portal_user":
        if not allow_client:
            raise HttpError(403, "Acesso não permitido para usuário lojista.")
        client_user = get_client_portal_user(request)
        if not client_user:
            raise HttpError(401, "Usuário lojista não autenticado ou revogado.")
        return "client", client_user
    return "staff", require_role(roles)(request)


def _operator_scope(request, requested_operator_id: Optional[str] = None) -> str:
    """Resolve o tenant exclusivamente a partir da identidade autenticada."""
    actor_kind, actor = _panel_actor(
        request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"], allow_client=True
    )
    if actor_kind == "client":
        if requested_operator_id and str(requested_operator_id) != str(actor.operator_id):
            raise HttpError(403, "Acesso negado ao operador solicitado.")
        return str(actor.operator_id)
    if getattr(actor, "is_platform_admin", False):
        target = (
            requested_operator_id
            or request.headers.get("X-Operator-Id")
            or actor.operator_id
        )
        if not target or target == "global" or not Operator.objects.filter(id=target).exists():
            raise HttpError(422, "Selecione um operador logístico válido.")
        return str(target)

    operator_id = actor.operator_id
    if not operator_id:
        raise HttpError(403, "Usuário sem operador logístico vinculado.")
    if requested_operator_id and str(requested_operator_id) != str(operator_id):
        raise HttpError(403, "Acesso negado ao operador solicitado.")
    return str(operator_id)

@panel_api.post("/auth/login", auth=None, tags=["Native Auth Panel"])
def panel_login(request, payload: LoginPayload):
    return login_endpoint(request, payload)

@panel_api.get("/auth/me", tags=["Native Auth Panel"])
def panel_me(request):
    return handle_me(request)

@panel_api.post("/auth/refresh", auth=None, tags=["Native Auth Panel"])
def panel_refresh(request, payload: RefreshPayload = None):
    return refresh_endpoint(request, payload)

@panel_api.post("/auth/logout", tags=["Native Auth Panel"])
def panel_logout(request):
    return logout_endpoint(request)

@panel_api.post("/auth/change-tenant")
def change_tenant(request, payload: dict):
    raise HttpError(
        410,
        "Endpoint removido. O contexto de operador é validado por requisição no header X-Operator-Id.",
    )




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

    actor_kind, actor = _panel_actor(
        request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"], allow_client=True
    )
    is_admin = actor_kind == "staff" and bool(getattr(actor, "is_platform_admin", False))
    auth_op_id = actor.operator_id
    client_id = actor.client_id if actor_kind == "client" else None
    
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

    _, actor = _panel_actor(request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])
    is_admin = bool(getattr(actor, "is_platform_admin", False))
    auth_op_id = actor.operator_id

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

    actor_kind, actor = _panel_actor(
        request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"], allow_client=True
    )
    if actor_kind == "staff" and getattr(actor, "is_platform_admin", False):
        ops = Operator.objects.all()
        return {"companies": [{"id": str(o.id), "nome": o.name} for o in ops]}
    stores = Store.objects.filter(operator_id=actor.operator_id)
    if actor_kind == "client":
        stores = stores.filter(client_id=actor.client_id)
    return {"companies": [{"id": str(s.id), "nome": s.name} for s in stores]}

@panel_api.get("/machine/drivers")
def get_machine_drivers(request, company_id: Optional[str] = None):
    from django.core.exceptions import ValidationError

    _, actor = _panel_actor(request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])
    is_admin = bool(getattr(actor, "is_platform_admin", False))
    auth_op_id = actor.operator_id

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
    _panel_actor(request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"])
    operator_id = _operator_scope(request)
    try:
        w = Wallet.objects.get(driver_id=condutor_id, operator_id=operator_id)
        return {"saldo": w.balanceCents / 100.0}
    except Wallet.DoesNotExist:
        return {"saldo": 0.0}

@panel_api.get("/machine/rides/tracking")
def get_machine_ride_tracking(request, id_mch: str):
    operator_id = _operator_scope(request)
    orders = Order.objects.filter(id=id_mch, operator_id=operator_id)
    auth = getattr(request, "auth", None) or {}
    if auth.get("client_id"):
        client_user = get_client_portal_user(request)
        orders = orders.filter(store__client=client_user.client)
    order = orders.first()
    if not order:
        raise HttpError(404, "Corrida não encontrada.")
    return {"link_rastreamento": f"/rastreio/{order.id}"}

from pydantic import BaseModel, Field
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
    paradas: List[StopPayload] = Field(default_factory=list)
    retorno: bool = False


def _parse_coordinate(value: str, *, field_name: str, minimum: float, maximum: float) -> float:
    try:
        from logistics.pricing import parse_coordinate

        return parse_coordinate(
            value, field_name=field_name, minimum=minimum, maximum=maximum
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc


def _estimated_route_distance_km(points) -> float:
    """Estimativa conservadora; o método é exposto na resposta e não finge roteamento viário."""
    from logistics.pricing import estimate_route_distance_km

    return estimate_route_distance_km(points)


def _configured_fare_cents(store, distance_km: float) -> int:
    from logistics.pricing import configured_fare_cents

    try:
        return configured_fare_cents(store, distance_km)
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc


@panel_api.post("/machine/rides/create")
def post_machine_ride_create(request, payload: RideCreatePayload):
    from logistics.models import Store, Order, Stop
    from django.contrib.gis.geos import Point
    from django.db import transaction
    from finance.business_date import resolve_store_business_date
    
    _panel_actor(
        request, ["ADMIN", "MANAGER", "OPERATOR_ROLE"], allow_client=True
    )
    operator_id = _operator_scope(request)
    operator = Operator.objects.get(id=operator_id)

    stores = Store.objects.filter(operator=operator, id=payload.empresa_id, operational=True)
    client_id = (getattr(request, "auth", None) or {}).get("client_id")
    if client_id:
        client_user = get_client_portal_user(request)
        stores = stores.filter(client=client_user.client)
    store = stores.first()
    if not store:
        raise HttpError(422, "Nenhuma loja autorizada está disponível para a corrida.")

    if not payload.paradas:
        raise HttpError(422, "Informe ao menos uma parada de entrega.")

    pickup = (
        _parse_coordinate(
            payload.lat_partida, field_name="lat_partida", minimum=-90, maximum=90
        ),
        _parse_coordinate(
            payload.lng_partida, field_name="lng_partida", minimum=-180, maximum=180
        ),
    )
    parsed_stops = []
    for index, parada in enumerate(payload.paradas, start=1):
        parsed_stops.append(
            (
                _parse_coordinate(
                    parada.lat_parada,
                    field_name=f"paradas[{index}].lat_parada",
                    minimum=-90,
                    maximum=90,
                ),
                _parse_coordinate(
                    parada.lng_parada,
                    field_name=f"paradas[{index}].lng_parada",
                    minimum=-180,
                    maximum=180,
                ),
            )
        )

    distancia_km = _estimated_route_distance_km([pickup, *parsed_stops])
    distance_meters = int(distancia_km * 1000)
    valor_cents = _configured_fare_cents(store, distancia_km)

    metadata = {
        "payment_method_id": payload.forma_pagamento_id,
        "vehicle_type_id": payload.tipo_veiculo_id,
        "return_required": payload.retorno
    }

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
    
    with transaction.atomic():
        order = Order.objects.create(
            operator=operator,
            store=store,
            status=Order.OrderStatus.PREPARING,
            fareValueCents=valor_cents,
            distanceMeters=distance_meters,
            businessDate=resolve_store_business_date(store),
            metadata={**metadata, "distance_method": "HAVERSINE_BUFFERED_30_PERCENT"},
        )

        Stop.objects.create(
            operator=operator,
            order=order,
            sequence=1,
            type=Stop.StopType.PICKUP,
            geom=Point(pickup[1], pickup[0]),
            metadata=pickup_meta,
        )

        for seq, (parada, (p_lat, p_lon)) in enumerate(
            zip(payload.paradas, parsed_stops), start=2
        ):
            dropoff_meta = {
                "address": f"{parada.endereco_parada}, {parada.numero_parada}",
                "neighborhood": parada.bairro_parada,
                "city": parada.cidade_parada,
                "state": parada.estado_parada,
                "zipcode": parada.cep_parada,
                "complement": parada.complemento_parada,
                "customer_name": parada.nome_cliente_parada,
                "customer_phone": parada.telefone_cliente_parada,
                "observation": parada.observacao_parada,
            }
            Stop.objects.create(
                operator=operator,
                order=order,
                sequence=seq,
                type=Stop.StopType.DROPOFF,
                geom=Point(p_lon, p_lat),
                metadata=dropoff_meta,
            )
        
    return {"response": {"id": str(order.id)}}

class RideCancelPayload(BaseModel):
    id_mch: str

@panel_api.post("/machine/rides/cancel")
def post_machine_ride_cancel(request, payload: RideCancelPayload):
    from django.core.exceptions import ValidationError
    try:
        _panel_actor(request, ["ADMIN", "MANAGER", "OPERATOR_ROLE"], allow_client=True)
        operator_id = _operator_scope(request)
        order = Order.objects.get(id=payload.id_mch, operator_id=operator_id)
        client_id = (getattr(request, "auth", None) or {}).get("client_id")
        if client_id and str(order.store.client_id) != str(client_id):
            raise Order.DoesNotExist
        order.status = Order.OrderStatus.CANCELED
        order.save()
        return {"success": True}
    except (Order.DoesNotExist, ValidationError):
        return panel_api.create_response(request, {"error": "Order not found"}, status=404)

@panel_api.get("/machine/rides/estimate", auth=auth_bearer)
def get_machine_rides_estimate(
    request, 
    empresa_id: str,
    endereco_partida: str = "", 
    bairro_partida: str = "", 
    cidade_partida: str = "", 
    estado_partida: str = "",
    lat_partida: str = "",
    lng_partida: str = "",
    endereco_desejado: str = "", 
    bairro_desejado: str = "", 
    cidade_desejado: str = "", 
    estado_desejado: str = "",
    lat_desejado: str = "",
    lng_desejado: str = "",
):
    from logistics.models import Store

    _panel_actor(request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"], allow_client=True)

    pickup = (
        _parse_coordinate(lat_partida, field_name="lat_partida", minimum=-90, maximum=90),
        _parse_coordinate(lng_partida, field_name="lng_partida", minimum=-180, maximum=180),
    )
    destination = (
        _parse_coordinate(lat_desejado, field_name="lat_desejado", minimum=-90, maximum=90),
        _parse_coordinate(lng_desejado, field_name="lng_desejado", minimum=-180, maximum=180),
    )
    distancia = _estimated_route_distance_km([pickup, destination])
    operator_id = _operator_scope(request)
    stores = Store.objects.filter(id=empresa_id, operator_id=operator_id, operational=True)
    client_id = (getattr(request, "auth", None) or {}).get("client_id")
    if client_id:
        stores = stores.filter(client_id=client_id)
    store = stores.first()
    if not store:
        raise HttpError(404, "Loja não encontrada no escopo autenticado.")
    valor_cents = _configured_fare_cents(store, distancia)

    return {
        "response": {
            "distancia": round(distancia, 2),
            "valor": valor_cents / 100.0,
            "metodo_distancia": "HAVERSINE_BUFFERED_30_PERCENT",
        }
    }

@panel_api.get("/machine/rides/receipt")
def get_machine_rides_receipt(request, solicitacao_id: str):
    from django.core.exceptions import ValidationError
    try:
        _panel_actor(request, ["ADMIN", "MANAGER", "OPERATOR_ROLE", "VIEWER"], allow_client=True)
        operator_id = _operator_scope(request)
        order = Order.objects.select_related("store", "driver").get(
            id=solicitacao_id, operator_id=operator_id
        )
        client_id = (getattr(request, "auth", None) or {}).get("client_id")
        if client_id and str(order.store.client_id) != str(client_id):
            raise Order.DoesNotExist
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
    from django.core.exceptions import ValidationError

    uid = request.auth.get("sub")
    try:
        exists = PlatformAdmin.objects.filter(id=uid).exists() or PlatformAdmin.objects.filter(supabase_uid=uid).exists()
    except (ValidationError, ValueError, TypeError):
        exists = False
    if not exists and request.auth.get("email"):
        exists = PlatformAdmin.objects.filter(email__iexact=request.auth["email"]).exists()
    return bool(request.auth.get("is_platform_admin") and exists)


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
    from django.db import transaction

    if not is_request_platform_admin(request):
        return panel_api.create_response(request, {"error": "Acesso Negado: requer privilégios de Superadmin."}, status=403)

    if not payload.name or not payload.managerName or not payload.managerEmail:
        return panel_api.create_response(request, {"error": "Dados obrigatórios faltando"}, status=400)
    if len(payload.managerPassword) < 10:
        raise HttpError(422, "A senha inicial deve possuir ao menos 10 caracteres.")
    if StaffMember.objects.filter(email__iexact=payload.managerEmail.strip()).exists():
        raise HttpError(409, "Já existe um usuário com este e-mail.")

    try:
        with transaction.atomic():
            initial_status = Operator.OperatorStatus.TRIAL if payload.trialDays > 0 else Operator.OperatorStatus.ACTIVE
            operator = Operator.objects.create(
                id=uuid.uuid4(), name=payload.name, cnpj=payload.cnpj or "",
                phone=payload.phone or "", city=payload.city or "", state=payload.state or "",
                billingPlanType=payload.billingPlanType or "PERCENT_PER_DELIVERY",
                billingRateValue=payload.billingRateValue or 0.0,
                billingCycle=payload.billingCycle or "MENSAL", dueDay=payload.dueDay or 10,
                trialDays=payload.trialDays if payload.trialDays is not None else 14,
                gracePeriodDays=payload.gracePeriodDays if payload.gracePeriodDays is not None else 5,
                notes=payload.notes or "", status=initial_status,
            )
            staff = StaffMember(
                id=uuid.uuid4(), operator=operator, name=payload.managerName,
                email=payload.managerEmail.strip().lower(), role=StaffMember.RoleType.ADMIN,
                active=True,
            )
            staff.set_password(payload.managerPassword)
            staff.save()

        return {"success": True, "operatorId": str(operator.id), "staffId": str(staff.id)}
    except Exception:
        logger.exception("Falha ao criar operador logístico.")
        return panel_api.create_response(
            request,
            {"success": False, "error": "Não foi possível criar o operador."},
            status=500,
        )


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

    if not payload.newPassword or len(payload.newPassword) < 10:
        return panel_api.create_response(request, {"error": "A senha deve ter pelo menos 10 caracteres"}, status=400)

    manager.set_password(payload.newPassword)
    manager.save(update_fields=["passwordHash"])
    return {"success": True, "managerEmail": manager.email, "message": "Senha redefinida com sucesso!"}




# Catch-all
@panel_api.api_operation(['GET', 'POST', 'PUT', 'DELETE'], '/{path:path}', auth=None)
def catch_all(request, path: str):
    return {}
