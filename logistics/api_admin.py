from ninja import Router, Schema
from typing import List, Optional
from datetime import time
from django.contrib.gis.geos import Point
import uuid
from ninja.errors import HttpError

from logistics.models import Driver, Vehicle, Client, Store, Turno, ScheduleEntry
from accounts.models import Operator
from config.core_models import tenant_context

router = Router(tags=["Admin - Logistics"])

# Schemas
class DriverSchema(Schema):
    id: str
    name: str
    active: bool
    onboarding_status: str

class UpdateDriverStatusSchema(Schema):
    active: bool

class CreateClientSchema(Schema):
    name: str
    document: str

class CreateStoreSchema(Schema):
    client_id: str
    name: str
    latitude: float
    longitude: float

class CreateTurnoSchema(Schema):
    store_id: str
    name: str
    start_time: time
    end_time: time

class CreateDriverSchema(Schema):
    name: str
    phone: str
    pixKeyType: str
    pixKey: str
    tax_classification: str
    document: str

class CreateVehicleSchema(Schema):
    plate: str
    type: str

# Flow 3.1: Client
@router.post("/clients")
def create_client(request, data: CreateClientSchema):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        client = Client.objects.create(
            operator=operator,
            name=data.name,
            document=data.document
        )
        return {"id": str(client.id), "name": client.name}

# Flow 3.2: Store
@router.post("/stores")
def create_store(request, data: CreateStoreSchema):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        client = Client.objects.get(id=data.client_id, operator_id=operator_id)
        store = Store.objects.create(
            operator=operator,
            client=client,
            name=data.name,
            geom=Point(data.longitude, data.latitude, srid=4326)
        )
        return {"id": str(store.id), "name": store.name}

# Flow 3.4: Turno e Operational flag
@router.post("/turnos")
def create_turno(request, data: CreateTurnoSchema):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        store = Store.objects.get(id=data.store_id, operator_id=operator_id)
        
        turno = Turno.objects.create(
            operator=operator,
            store=store,
            name=data.name,
            startTime=data.start_time,
            endTime=data.end_time
        )
        
        # O store agora está operacional
        if not store.operational:
            store.operational = True
            store.save(update_fields=['operational'])
            
        return {"id": str(turno.id), "name": turno.name}

# Flow 4.1: Driver (Base Creation)
@router.post("/drivers", response=DriverSchema)
def create_driver(request, data: CreateDriverSchema):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        
        supabase_uid = uuid.uuid4() # TODO: Supabase Admin Invite Driver App
        
        driver = Driver.objects.create(
            operator=operator,
            name=data.name,
            phone=data.phone,
            pixKeyType=data.pixKeyType,
            pixKey=data.pixKey,
            tax_classification=data.tax_classification,
            document=data.document,
            supabase_uid=supabase_uid,
            onboarding_status='INVITED'
        )
        return driver

# Flow 5: Vehicle
@router.post("/vehicles")
def create_vehicle(request, data: CreateVehicleSchema):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        vehicle = Vehicle.objects.create(
            operator=operator,
            plate=data.plate,
            type=data.type
        )
        return {"id": str(vehicle.id), "plate": vehicle.plate}


class CreateScheduleSchema(Schema):
    driver_id: str
    store_id: str
    turno_id: str
    date: str # YYYY-MM-DD
    minGuaranteedOverrideCents: Optional[int] = None

@router.post("/schedules")
def create_schedule(request, data: CreateScheduleSchema):
    """
    [Flow 4.4] Gate de Scheduling.
    Regra: Apenas Driver Ativo, Aprovado, sem docs vencidos, e fora de Deny-list.
    """
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        driver = Driver.objects.get(id=data.driver_id, operator_id=operator_id)
        
        # 1. Validação de Status Ativo
        if not driver.active:
            raise HttpError(422, "Motorista inativo.")
            
        # 2. Validação de Onboarding
        if driver.onboarding_status != 'APPROVED':
            raise HttpError(422, f"Motorista não está aprovado (Status atual: {driver.onboarding_status}).")
            
        # 3. Validação de CNH Vencida (simulação, pois SecurityDenylist e ExpiredDocs fariam o status ir para BLOCKED, mas checamos ativamente aqui por precaução)
        from logistics.models import DriverDocument
        from datetime import date
        today = date.today()
        vencidos = DriverDocument.objects.filter(
            driver=driver,
            expiresAt__lt=today
        ).exists()
        if vencidos:
            raise HttpError(422, "Motorista possui documentos vencidos.")
            
        # TODO: Validação na SecurityDenylist (mesmo estando ativo)
        
        # Passou no Gate -> Criação da Escala
        store = Store.objects.get(id=data.store_id, operator_id=operator_id)
        turno = Turno.objects.get(id=data.turno_id, operator_id=operator_id)
        
        schedule = ScheduleEntry.objects.create(
            operator=operator,
            driver=driver,
            store=store,
            turno=turno,
            date=data.date,
            minGuaranteedOverrideCents=data.minGuaranteedOverrideCents
        )
        return {"id": str(schedule.id), "date": str(schedule.date)}

@router.get("/drivers", response=List[DriverSchema])
def list_drivers(request):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        return Driver.objects.filter(operator_id=operator_id)

@router.put("/drivers/{driver_id}/status", response=DriverSchema)
def update_driver_status(request, driver_id: str, data: UpdateDriverStatusSchema):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        driver = Driver.objects.get(operator_id=operator_id, id=driver_id)
        driver.active = data.active
        driver.save(update_fields=['active'])
        return driver
