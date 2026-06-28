import os

filepath = os.path.join("config", "panel_api.py")

code_to_append = """

@panel_api.get("/machine/companies")
def get_machine_companies(request):
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
    return {"saldo": 0}

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
    from logistics.models import Store
    from django.core.exceptions import ValidationError
    
    try:
        operator = Operator.objects.get(id=payload.empresa_id)
    except (Operator.DoesNotExist, ValidationError):
        return panel_api.create_response(request, {"error": "Empresa inválida"}, status=400)
    
    store = Store.objects.filter(operator=operator).first()
    if not store:
        store = Store.objects.create(operator=operator, name="Store Default")
        
    order = Order.objects.create(
        operator=operator,
        store=store,
        status=Order.OrderStatus.PREPARING
    )
    
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

@panel_api.get("/machine/rides/estimate")
def get_machine_rides_estimate(
    request, 
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
    lng_desejado: str = ""
):
    return {
        "response": {
            "distancia": 5.0,
            "valor": 12.0
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
                "valor_total": 15.0,
                "status": order.status
            }
        }
    except (Order.DoesNotExist, ValidationError):
        return panel_api.create_response(request, {"error": "Order not found"}, status=404)

"""

with open(filepath, "a", encoding="utf-8") as f:
    f.write(code_to_append)

print("Done appending")
