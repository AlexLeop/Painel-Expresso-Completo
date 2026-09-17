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
    try:
        from django.core.exceptions import ValidationError
        auth = getattr(request, "auth", None) or {}
        is_admin = auth.get("is_platform_admin", False)
        auth_op_id = auth.get("operator_id")

        qs = ManualEntry.objects.all()
        if not is_admin and auth_op_id:
            qs = qs.filter(operator_id=auth_op_id)
        elif company_id and company_id != "global":
            try:
                qs = qs.filter(operator_id=company_id)
            except ValidationError:
                pass
        elif not is_admin:
            return []

        if start:
            qs = qs.filter(createdAt__gte=start)
        if end:
            qs = qs.filter(createdAt__lte=end)
            
        res = []
        for entry in qs:
            try:
                drv_name = entry.driver.name if entry.driver_id else ""
            except Exception:
                drv_name = ""
            res.append({
                "id": str(entry.id),
                "driverName": drv_name,
                "motoboy": drv_name,
                "type": entry.description or "",
                "categoria": "Crédito" if (entry.amountCents or 0) > 0 else "Débito",
                "valor": (entry.amountCents or 0) / 100.0,
                "data": entry.createdAt.strftime("%Y-%m-%d") if hasattr(entry.createdAt, 'strftime') else str(entry.createdAt),
                "description": entry.description or ""
            })
        return res
    except Exception:
        import traceback
        traceback.print_exc()
        return []

@router.post("/entries")
def create_entry(request, payload: EntryPayload):
    auth = getattr(request, "auth", None) or {}
    auth_op_id = auth.get("operator_id")
    company_id = auth_op_id or payload.company_id or payload.companyId
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
        status=ManualEntry.EntryStatus.APPROVED,
        taxCategory="NON_TAXABLE_REIMBURSEMENT" if amt_cents >= 0 else "DEDUCTION"
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
    from accounts.models import Operator
    from logistics.models import Store
    from finance.models import Contract

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    op_id = auth.get("operator_id")
    client_id = auth.get("client_id")

    qs = Store.objects.select_related("operator", "client").all()
    if client_id:
        qs = qs.filter(client_id=client_id)
    elif op_id and not is_admin:
        qs = qs.filter(operator_id=op_id)

    res = []
    for s in qs:
        contract = Contract.objects.filter(store=s).first()
        lat = None
        lng = None
        if getattr(s, "geom", None):
            try:
                lat = float(s.geom.y)
                lng = float(s.geom.x)
            except Exception:
                pass

        bal = compute_store_balance(s)

        res.append({
            "id": str(s.id),
            "nome": s.name,
            "name": s.name,
            "documento": s.client.document if s.client else "",
            "telefone": "",
            "endereco": s.name,
            "lat": lat,
            "lng": lng,
            "active": s.operational if hasattr(s, "operational") else True,
            "ride_fee_per_delivery": (contract.rideFeePerDeliveryCents / 100.0) if (contract and contract.rideFeePerDeliveryCents) else 1.6,
            "minimum_rides_fee_floor": (contract.minimumRidesFeeFloorCents / 100.0) if (contract and contract.minimumRidesFeeFloorCents) else 350.0,
            "daily_rate_weekday": (contract.dailyRateWeekdayCents / 100.0) if (contract and contract.dailyRateWeekdayCents) else 60.0,
            "daily_rate_saturday": (contract.dailyRateSaturdayCents / 100.0) if (contract and contract.dailyRateSaturdayCents) else 70.0,
            "daily_rate_sunday": (contract.dailyRateSundayCents / 100.0) if (contract and contract.dailyRateSundayCents) else 80.0,
            "daily_rate_holiday": (contract.dailyRateHolidayCents / 100.0) if (contract and contract.dailyRateHolidayCents) else 80.0,
            "operator_id": str(s.operator_id),
            "operator_name": s.operator.name if s.operator else "",
            "billing_mode": bal.get("billing_mode", "PRE_PAGO"),
            "balance_cents": bal.get("balance_cents", 0),
            "balance_reais": bal.get("balance_reais", 0.0),
        })

    return res

@router.get("/users")
def get_users(request):
    from accounts.models import StaffMember, PlatformAdmin
    from logistics.models import ClientPortalUser
    
    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    op_id = auth.get("operator_id")
    client_id = auth.get("client_id")
    
    if client_id:
        return []

    res = []
    if is_admin:
        # PlatformAdmin vê toda a hierarquia
        for p in PlatformAdmin.objects.all().order_by("-createdAt"):
            res.append({
                "id": str(p.id),
                "nome": p.name,
                "name": p.name,
                "email": p.email,
                "role": "superadmin",
                "active": True,
                "companies": [{"id": "global", "name": "Administração Global"}],
            })
        for u in StaffMember.objects.select_related("operator").all().order_by("-createdAt"):
            res.append({
                "id": str(u.id),
                "nome": u.name,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "active": u.active,
                "companies": [{"id": str(u.operator_id), "name": u.operator.name}] if u.operator else [],
            })
        for c in ClientPortalUser.objects.select_related("client").all().order_by("-createdAt"):
            res.append({
                "id": str(c.id),
                "nome": c.name,
                "name": c.name,
                "email": c.email,
                "role": "lojista",
                "active": True,
                "companies": [{"id": str(c.client_id), "name": c.client.name}] if c.client else [],
            })
    elif op_id:
        # Staff do operador vê seus colaboradores e lojistas
        for u in StaffMember.objects.filter(operator_id=op_id).select_related("operator").order_by("-createdAt"):
            res.append({
                "id": str(u.id),
                "nome": u.name,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "active": u.active,
                "companies": [{"id": str(u.operator_id), "name": u.operator.name}] if u.operator else [],
            })
        for c in ClientPortalUser.objects.filter(operator_id=op_id).select_related("client").order_by("-createdAt"):
            res.append({
                "id": str(c.id),
                "nome": c.name,
                "name": c.name,
                "email": c.email,
                "role": "lojista",
                "active": True,
                "companies": [{"id": str(c.client_id), "name": c.client.name}] if c.client else [],
            })
    else:
        for u in StaffMember.objects.all().order_by("-createdAt"):
            res.append({"id": str(u.id), "nome": u.name, "name": u.name, "email": u.email, "role": u.role, "active": u.active})

    return res

class UserPayload(BaseModel):
    id: Optional[str] = None
    fullName: str
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    companyId: Optional[str] = None
    companyIds: Optional[list] = None

@router.post("/users")
def create_user(request, payload: UserPayload):
    from accounts.models import StaffMember, Operator, PlatformAdmin
    from logistics.models import ClientPortalUser, Client
    import uuid
    try:
        if not payload.email:
            return {"success": False, "error": "Email é obrigatório."}

        auth = getattr(request, "auth", None) or {}
        is_admin = auth.get("is_platform_admin", False)
        auth_op_id = auth.get("operator_id")

        c_id = payload.companyId
        if not c_id and payload.companyIds and len(payload.companyIds) > 0:
            c_id = payload.companyIds[0]

        if not is_admin and auth_op_id:
            target_operator_id = auth_op_id
        else:
            target_operator_id = c_id if (c_id and c_id != "global") else None

        role = (payload.role or "OPERATOR_ROLE").upper()
        raw_password = payload.password or "123456"

        if role == "LOJISTA":
            client = None
            if c_id:
                from logistics.models import Store
                try:
                    store = Store.objects.filter(id=c_id).first()
                    if store and store.client:
                        client = store.client
                except Exception:
                    pass
                if not client:
                    try:
                        client = Client.objects.filter(id=c_id).first()
                    except Exception:
                        pass
            if not client and target_operator_id:
                client = Client.objects.filter(operator_id=target_operator_id).first()
            if not client:
                client = Client.objects.first()
            if not client:
                return {"success": False, "error": "Nenhum cliente/loja cadastrado para vincular o lojista."}

            c_user = ClientPortalUser(
                id=uuid.uuid4(),
                operator=client.operator,
                client=client,
                name=payload.fullName,
                email=payload.email.strip().lower(),
            )
            c_user.set_password(raw_password)
            c_user.save()
            return {"success": True}

        operator = None
        if target_operator_id:
            operator = Operator.objects.filter(id=target_operator_id).first()

        if operator:
            staff = StaffMember(
                id=uuid.uuid4(),
                operator=operator,
                name=payload.fullName,
                email=payload.email.strip().lower(),
                role=payload.role or "OPERATOR_ROLE",
                active=True,
            )
            staff.set_password(raw_password)
            staff.save()
            return {"success": True}

        if is_admin:
            p_admin = PlatformAdmin(
                id=uuid.uuid4(),
                name=payload.fullName,
                email=payload.email.strip().lower(),
            )
            p_admin.set_password(raw_password)
            p_admin.save()
            return {"success": True}
        else:
            return {"success": False, "error": "Operador inválido ou não informado."}

    except Exception as e:
        return {"success": False, "error": str(e)}

@router.put("/users")
def update_user(request, payload: UserPayload):
    from accounts.models import StaffMember, PlatformAdmin
    try:
        staff = StaffMember.objects.get(id=payload.id)
        staff.name = payload.fullName
        if payload.role:
            staff.role = payload.role
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
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.delete("/users")
def delete_user(request, id: str):
    from accounts.models import StaffMember, PlatformAdmin
    from logistics.models import ClientPortalUser
    try:
        user = None
        for model in [StaffMember, PlatformAdmin, ClientPortalUser]:
            try:
                user = model.objects.get(id=id)
                break
            except (model.DoesNotExist, Exception):
                pass
        
        if not user:
            return {"success": False, "error": "Usuário não encontrado"}
            
        if getattr(user, "supabase_uid", None):
            try:
                from config.supabase_client import get_supabase_admin
                supabase_admin = get_supabase_admin()
                if supabase_admin:
                    supabase_admin.auth.admin.delete_user(str(user.supabase_uid))
            except Exception:
                pass
                
        user.delete()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

class CompanyDriverPayload(BaseModel):
    driver_id: Optional[str] = None
    driverId: Optional[str] = None
    company_id: Optional[Any] = None
    companyId: Optional[Any] = None
    active: Optional[bool] = None

@router.patch("/company-drivers")
def update_company_driver(request, payload: CompanyDriverPayload):
    from logistics.models import Driver
    try:
        d_id = payload.driver_id or payload.driverId
        if not d_id:
            return {"success": False, "error": "driver_id is required"}
            
        driver = Driver.objects.get(id=d_id)
        if payload.active is not None:
            driver.active = payload.active
            driver.save()
        return {"success": True}
    except Driver.DoesNotExist:
        return {"success": False, "error": "Driver not found"}

@router.get("/company-drivers")
def get_company_drivers(request, company_id: Optional[str] = None, active_only: int = 0):
    try:
        from django.core.exceptions import ValidationError
        from logistics.models import Driver, Vehicle

        auth = getattr(request, "auth", None) or {}
        is_admin = auth.get("is_platform_admin", False)
        auth_op_id = auth.get("operator_id")

        if not is_admin and auth_op_id:
            drivers = Driver.objects.filter(operator_id=auth_op_id)
        elif company_id and company_id != "global":
            try:
                drivers = Driver.objects.filter(operator_id=company_id)
            except (ValidationError, ValueError):
                drivers = Driver.objects.none()
        elif is_admin:
            drivers = Driver.objects.all()
        else:
            drivers = Driver.objects.none()

        if active_only:
            drivers = drivers.filter(active=True)

        res = []
        for d in drivers.order_by("-createdAt"):
            veh = Vehicle.objects.filter(operator=d.operator).first()
            res.append({
                "id": str(d.id),
                "driverId": str(d.id),
                "nome": d.name,
                "phone": d.phone,
                "telefone": d.phone,
                "document": d.document or "",
                "placa": veh.plate if veh else "",
                "modelo": "Motocicleta" if (veh and veh.type == "MOTORCYCLE") else (veh.type if veh else "Motocicleta"),
                "status": "Ativo" if d.active else "Inativo",
                "active": d.active,
                "maxActiveOrders": d.maxActiveOrders,
                "pixKeyType": d.pixKeyType,
                "pixKey": d.pixKey,
            })
        return res
    except Exception:
        import traceback
        traceback.print_exc()
        return []


class DriverCreateSchema(BaseModel):
    companyId: Optional[str] = None
    nome: str
    phone: Optional[str] = None
    telefone: Optional[str] = None
    email: str
    password: Optional[str] = "123456"
    document: Optional[str] = None
    rg: Optional[str] = None
    birthDate: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    vehicleType: Optional[str] = "MOTORCYCLE"
    placa: Optional[str] = None
    modelo: Optional[str] = None
    marca: Optional[str] = None
    ano: Optional[str] = None
    cor: Optional[str] = None
    cnhNumero: Optional[str] = None
    cnhCategoria: Optional[str] = "A"
    cnhValidade: Optional[str] = None
    cnhPrimeiraHabilitacao: Optional[str] = None
    pixKeyType: str = "TELEFONE"
    pixKey: str = ""
    maxActiveOrders: int = 3
    tax_classification: str = "PESSOA_FISICA_AUTONOMO"

@router.post("/company-drivers")
def create_company_driver(request, payload: DriverCreateSchema):
    """
    Cadastra um novo motoboy de forma 100% nativa sem dependência de Supabase Auth.
    Persiste o Driver, dados do Veículo e Documentação vinculados ao Operador.
    """
    from accounts.models import Operator
    from logistics.models import Driver, Store, StoreDriver, Vehicle, DriverDocument
    from accounts.security import hash_password
    from django.core.exceptions import ValidationError
    import uuid

    company_id = payload.companyId
    nome = payload.nome
    phone = payload.phone or payload.telefone
    email = payload.email
    password = payload.password or "123456"
    
    if not all([nome, phone, email]):
        return {"success": False, "error": "Nome, telefone e e-mail são obrigatórios"}
    
    try:
        auth = getattr(request, "auth", None) or {}
        auth_op_id = auth.get("operator_id")
        
        operator = None
        if auth_op_id:
            operator = Operator.objects.filter(id=auth_op_id).first()
        elif company_id and company_id != "global":
            try:
                operator = Operator.objects.filter(id=company_id).first()
            except (ValidationError, ValueError):
                operator = None
        if not operator:
            operator = Operator.objects.first()

        if not operator:
            return {"success": False, "error": "Nenhum operador logístico encontrado no sistema."}
        
        # 1. Criar Driver record de forma 100% nativa
        driver = Driver.objects.create(
            id=uuid.uuid4(),
            operator=operator,
            supabase_uid=uuid.uuid4(),
            name=nome,
            phone=phone,
            document=payload.document,
            pixKeyType=payload.pixKeyType or "TELEFONE",
            pixKey=payload.pixKey or phone,
            maxActiveOrders=payload.maxActiveOrders or 3,
            tax_classification=payload.tax_classification or "PESSOA_FISICA_AUTONOMO",
            passwordHash=hash_password(password),
            active=True
        )
        
        # 2. Se placa foi informada, registrar veículo
        if payload.placa:
            clean_plate = payload.placa.strip().upper()
            try:
                v_type = (payload.vehicleType or "MOTORCYCLE").upper()
                if v_type not in ["MOTORCYCLE", "BICYCLE", "CAR"]:
                    v_type = "MOTORCYCLE"
                Vehicle.objects.update_or_create(
                    plate=clean_plate,
                    defaults={
                        "operator": operator,
                        "type": v_type,
                        "active": True
                    }
                )
            except Exception:
                pass

        # 3. Se CNH foi informada, registrar DriverDocument
        if payload.cnhNumero:
            try:
                DriverDocument.objects.create(
                    id=uuid.uuid4(),
                    operator=operator,
                    driver=driver,
                    name=f"CNH {payload.cnhCategoria or 'A'} - {payload.cnhNumero}",
                    fileUrl="",
                    document_type="CNH",
                    status="APPROVED"
                )
            except Exception:
                pass

        # 4. Vincular a uma Store do operador (primeira Store encontrada)
        store = Store.objects.filter(operator_id=operator.id).first()
        if store:
            StoreDriver.objects.get_or_create(
                operator=operator,
                store=store,
                driver=driver
            )
            
        return {"success": True, "driverId": str(driver.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}

class StoreCreateSchema(BaseModel):
    companyId: Optional[str] = None
    name: str
    documento: Optional[str] = ""
    endereco: Optional[str] = ""
    telefone: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    averagePrepTimeMinutes: int = 15
    taxaCorridaPerEntrega: Optional[float] = 1.6
    pisoFixo: Optional[float] = 350.0
    diaria_weekday: Optional[float] = 60.0

@router.post("/companies")
def create_company_store(request, payload: StoreCreateSchema):
    """
    Cadastra uma nova Empresa/Loja (Store) para o Operador logístico.
    """
    from accounts.models import Operator
    from logistics.models import Client, Store
    from finance.models import Contract
    from django.core.exceptions import ValidationError
    from django.contrib.gis.geos import Point
    import uuid

    operator = None
    # 1. Tentar resolver via JWT auth (operator_id do token ou staff logado)
    auth = getattr(request, "auth", None)
    if auth:
        op_id = auth.get("operator_id")
        if op_id:
            try:
                operator = Operator.objects.filter(id=op_id).first()
            except (ValidationError, ValueError):
                pass

    # 2. Tentar via companyId no payload
    if not operator and payload.companyId and payload.companyId != "global":
        try:
            operator = Operator.objects.filter(id=payload.companyId).first()
        except (ValidationError, ValueError):
            operator = None

    # 3. Fallback: primeiro operador do sistema
    if not operator:
        operator = Operator.objects.first()

    if not operator:
        return {"success": False, "error": "Nenhum operador logístico cadastrado. Cadastre um operador antes de criar empresas."}

    name = payload.name
    if not name:
        return {"success": False, "error": "Nome da empresa é obrigatório."}

    try:
        # 1. Criar Client
        client = Client.objects.create(
            id=uuid.uuid4(),
            operator=operator,
            name=name,
            document=payload.documento or "",
            active=True
        )

        # 2. Criar Store
        if payload.lat and payload.lng:
            geom = Point(payload.lng, payload.lat, srid=4326)
        else:
            geom = Point(-43.1729, -22.9068, srid=4326)

        store = Store.objects.create(
            id=uuid.uuid4(),
            operator=operator,
            client=client,
            name=name,
            geom=geom,
            averagePrepTimeMinutes=payload.averagePrepTimeMinutes or 15,
            operational=True
        )

        # 3. Criar Contrato financeiro padrão
        Contract.objects.get_or_create(
            operator=operator,
            store=store,
            defaults={
                "compensationMode": Contract.CompensationMode.GARANTIDA,
                "rideFeePerDeliveryCents": int((payload.taxaCorridaPerEntrega or 1.6) * 100),
                "minimumRidesFeeFloorCents": int((payload.pisoFixo or 350.0) * 100),
                "minimumFloorBps": 0,
                "adminTaxThresholdCents": 0,
                "adminTaxFixedAmountCents": 0,
                "adminTaxBps": 0,
                "dailyRateWeekdayCents": int((payload.diaria_weekday or 60.0) * 100),
            }
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
    nome: Optional[str] = None
    documento: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    averagePrepTimeMinutes: Optional[int] = None
    status: Optional[str] = None
    ride_fee_per_delivery: Optional[float] = None
    rideFeePerDeliveryCents: Optional[int] = None
    minimum_rides_fee_floor: Optional[float] = None
    minimumRidesFeeFloorCents: Optional[int] = None
    daily_rate_weekday: Optional[float] = None
    dailyRateWeekdayCents: Optional[int] = None
    daily_rate_saturday: Optional[float] = None
    daily_rate_sunday: Optional[float] = None
    daily_rate_holiday: Optional[float] = None

@router.put('/companies/{company_id}')
def update_company_store(request, company_id: str, payload: StoreUpdateSchema):
    from django.contrib.gis.geos import Point
    from finance.models import Contract
    try:
        store = Store.objects.get(id=company_id)
        store_name = payload.nome or payload.name
        if store_name is not None:
            store.name = store_name
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

        # Update contract if any fee provided
        contract = Contract.objects.filter(store=store).first()
        if not contract:
            contract = Contract(
                operator=store.operator, 
                store=store, 
                compensationMode=Contract.CompensationMode.GARANTIDA,
                rideFeePerDeliveryCents=160,
                minimumRidesFeeFloorCents=35000,
                minimumFloorBps=0,
                adminTaxThresholdCents=0,
                adminTaxFixedAmountCents=0,
                adminTaxBps=0,
                dailyRateWeekdayCents=6000
            )

        if payload.rideFeePerDeliveryCents is not None:
            contract.rideFeePerDeliveryCents = payload.rideFeePerDeliveryCents
        elif payload.ride_fee_per_delivery is not None:
            contract.rideFeePerDeliveryCents = int(payload.ride_fee_per_delivery * 100)

        if payload.minimumRidesFeeFloorCents is not None:
            contract.minimumRidesFeeFloorCents = payload.minimumRidesFeeFloorCents
        elif payload.minimum_rides_fee_floor is not None:
            contract.minimumRidesFeeFloorCents = int(payload.minimum_rides_fee_floor * 100)

        if payload.dailyRateWeekdayCents is not None:
            contract.dailyRateWeekdayCents = payload.dailyRateWeekdayCents
        elif payload.daily_rate_weekday is not None:
            contract.dailyRateWeekdayCents = int(payload.daily_rate_weekday * 100)

        if payload.daily_rate_saturday is not None:
            contract.dailyRateSaturdayCents = int(payload.daily_rate_saturday * 100)
        if payload.daily_rate_sunday is not None:
            contract.dailyRateSundayCents = int(payload.daily_rate_sunday * 100)
        if payload.daily_rate_holiday is not None:
            contract.dailyRateHolidayCents = int(payload.daily_rate_holiday * 100)

        contract.save()
            
        return {'success': True}
    except Store.DoesNotExist:
        return {'success': False, 'error': 'Store not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.delete('/companies/{company_id}')
def delete_company_store(request, company_id: str):
    try:
        store = Store.objects.get(id=company_id)
        store.delete()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ==============================================================================
# UNIFIED NATIVE ORDERS API (Replaces Legacy Taxi Machine Proxy)
# ==============================================================================

from typing import Optional

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
    
    res = []
    for o in orders:
        try:
            drv_name = "Não atribuído"
            try:
                if o.driver_id and hasattr(o, 'driver') and o.driver:
                    drv_name = o.driver.name
            except Exception:
                pass
                
            res.append({
                "id": str(o.id),
                "driver_id": str(o.driver_id) if o.driver_id else None,
                "motorista": drv_name,
                "status": o.status,
                "price": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
                "valor_total": (o.fareValueCents or 0) / 100.0 if hasattr(o, 'fareValueCents') else 0,
                "distance": (o.distanceMeters or 0) / 1000.0 if hasattr(o, 'distanceMeters') else 0,
                "data": o.requestedAt.strftime("%Y-%m-%d %H:%M:%S") if getattr(o, 'requestedAt', None) and hasattr(o.requestedAt, 'strftime') else str(getattr(o, 'requestedAt', ''))
            })
        except Exception:
            continue
            
    return res

@router.post("/orders/create")
def create_order(request, payload: OrderCreateSchema):
    from logistics.models import Order, Stop, Store
    from django.contrib.gis.geos import Point
    from accounts.models import Operator
    from django.utils import timezone
    
    try:
        auth = getattr(request, "auth", None) or {}
        auth_op_id = auth.get("operator_id")
        operator_id = auth_op_id or (payload.empresa_id if payload.empresa_id != "global" else None)
        
        # Get or create a fallback store for the operator to satisfy DB constraints
        store = None
        if operator_id:
            store = Store.objects.filter(operator_id=operator_id).first()
        if not store and operator_id:
            store = Store.objects.create(
                operator_id=operator_id,
                name="Loja Principal",
                operational=True,
                averagePrepTimeMinutes=10,
                geom=Point(-43.1729, -22.9068, srid=4326) # Default Rio coords
            )
            
        order = Order.objects.create(
            operator_id=operator_id,
            store=store,
            businessDate=timezone.now().date(),
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
def get_driver_balance(request, driver_id: Optional[str] = None, condutor_id: Optional[str] = None):
    from finance.models import Wallet
    d_id = driver_id or condutor_id
    if not d_id:
        return {"saldo": 0.0}
    try:
        w = Wallet.objects.get(driver_id=d_id)
        return {"saldo": w.balanceCents / 100.0}
    except Wallet.DoesNotExist:
        return {"saldo": 0.0}

# ==============================================================================
# MOTOR CONTÁBIL & FINANCEIRO — CRÉDITOS, RECARGAS, EXTRATO & SALDO DAS LOJAS
# ==============================================================================

def compute_store_balance(store):
    from finance.models import ManualEntry, WeeklyStoreInvoice
    from logistics.models import Order
    from django.db.models import Sum

    approved_credits = ManualEntry.objects.filter(
        store_id=store.id, status="APPROVED", amountCents__gt=0
    ).aggregate(s=Sum("amountCents"))["s"] or 0

    paid_invoices = WeeklyStoreInvoice.objects.filter(
        store_id=store.id, status="PAID"
    ).aggregate(s=Sum("totalCents"))["s"] or 0

    completed_orders_debit = Order.objects.filter(
        store_id=store.id, status="COMPLETED"
    ).aggregate(s=Sum("fareValueCents"))["s"] or 0

    manual_debits = ManualEntry.objects.filter(
        store_id=store.id, status="APPROVED", amountCents__lt=0
    ).aggregate(s=Sum("amountCents"))["s"] or 0

    total_credits = approved_credits + paid_invoices
    total_debits = completed_orders_debit + abs(manual_debits)
    balance_cents = total_credits - total_debits

    status = "DISPONIVEL" if balance_cents > 0 else ("ZERADO" if balance_cents == 0 else "DEVEDOR")

    return {
        "store_id": str(store.id),
        "store_name": store.name,
        "client_name": store.client.name if store.client else "",
        "billing_mode": "PRE_PAGO",
        "balance_cents": balance_cents,
        "balance_reais": round(balance_cents / 100.0, 2),
        "status": status,
        "total_credits_cents": total_credits,
        "total_debits_cents": total_debits,
        "credit_limit_cents": 0,
    }

@router.get("/client/balance")
def get_client_balance(request, store_id: Optional[str] = None):
    from logistics.models import Store
    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")
    op_id = auth.get("operator_id")

    store = None
    if store_id:
        try:
            store = Store.objects.filter(id=store_id).select_related("client", "operator").first()
        except Exception:
            pass

    if not store and client_id:
        store = Store.objects.filter(client_id=client_id).select_related("client", "operator").first()

    if not store and op_id:
        store = Store.objects.filter(operator_id=op_id).select_related("client", "operator").first()

    if not store:
        store = Store.objects.select_related("client", "operator").first()

    if not store:
        return {
            "store_id": "",
            "store_name": "Nenhuma loja vinculada",
            "client_name": "",
            "billing_mode": "PRE_PAGO",
            "balance_cents": 0,
            "balance_reais": 0.0,
            "status": "ZERADO",
            "total_credits_cents": 0,
            "total_debits_cents": 0,
            "credit_limit_cents": 0,
        }

    return compute_store_balance(store)

class ClientRechargePayload(BaseModel):
    store_id: Optional[str] = None
    amount_cents: int

@router.post("/client/recharge")
def client_recharge(request, payload: ClientRechargePayload):
    from logistics.models import Store
    from finance.models import WeeklyStoreInvoice
    from django.utils import timezone
    from datetime import timedelta
    import uuid

    if payload.amount_cents < 1000:
        return {"success": False, "error": "Valor mínimo para recarga é R$ 10,00"}

    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")
    op_id = auth.get("operator_id")

    store = None
    if payload.store_id:
        try:
            store = Store.objects.filter(id=payload.store_id).select_related("operator").first()
        except Exception:
            pass
    if not store and client_id:
        store = Store.objects.filter(client_id=client_id).select_related("operator").first()
    if not store and op_id:
        store = Store.objects.filter(operator_id=op_id).select_related("operator").first()
    if not store:
        store = Store.objects.select_related("operator").first()

    if not store:
        return {"success": False, "error": "Nenhuma loja encontrada para a recarga"}

    reais = round(payload.amount_cents / 100.0, 2)
    today = timezone.now().date()
    recharge_id = uuid.uuid4()
    pix_code = f"00020126580014br.gov.bcb.pix01363598698000012852040000530398654{reais:.2f}5802BR5914EXPRESSO NEVES6008BRASILIA62070503{str(recharge_id)[:8]}6304ABCD"

    invoice = WeeklyStoreInvoice.objects.create(
        id=recharge_id,
        operator=store.operator,
        store=store,
        startDate=today,
        endDate=today,
        totalNetProducaoCents=0,
        totalNetGarantidaCents=0,
        administrativeFeeCents=0,
        supervisionFeeCents=0,
        pendingDebitCarriedCents=0,
        totalCents=payload.amount_cents,
        status=WeeklyStoreInvoice.InvoiceStatus.DRAFT,
        pixCopyPaste=pix_code,
        barcode="",
    )

    return {
        "success": True,
        "recharge_id": str(invoice.id),
        "amount_cents": payload.amount_cents,
        "amount_reais": reais,
        "status": "PENDING",
        "pix_copy_paste": pix_code,
        "expires_at": (timezone.now() + timedelta(hours=2)).isoformat(),
    }

class ConfirmSimulationPayload(BaseModel):
    recharge_id: str

@router.post("/client/recharge/confirm-simulation")
def confirm_recharge_simulation(request, payload: ConfirmSimulationPayload):
    from finance.models import WeeklyStoreInvoice
    try:
        invoice = WeeklyStoreInvoice.objects.get(id=payload.recharge_id)
    except WeeklyStoreInvoice.DoesNotExist:
        return {"success": False, "error": "Recarga não encontrada"}

    invoice.status = WeeklyStoreInvoice.InvoiceStatus.PAID
    invoice.save(update_fields=["status"])

    bal = compute_store_balance(invoice.store)
    return {
        "success": True,
        "status": "PAID",
        "new_balance_cents": bal["balance_cents"],
        "new_balance_reais": bal["balance_reais"],
    }

@router.get("/client/financial-statement")
def get_financial_statement(
    request, 
    store_id: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    type: Optional[str] = "ALL"
):
    from logistics.models import Store, Order
    from finance.models import ManualEntry, WeeklyStoreInvoice
    from datetime import datetime

    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")
    op_id = auth.get("operator_id")

    store = None
    if store_id:
        try:
            store = Store.objects.filter(id=store_id).first()
        except Exception:
            pass
    if not store and client_id:
        store = Store.objects.filter(client_id=client_id).first()
    if not store and op_id:
        store = Store.objects.filter(operator_id=op_id).first()
    if not store:
        store = Store.objects.first()

    if not store:
        return {"current_balance_cents": 0, "total_entries": 0, "items": []}

    entries = []

    # 1. Manual entries
    me_qs = ManualEntry.objects.filter(store_id=store.id, status="APPROVED")
    if start_date:
        try:
            me_qs = me_qs.filter(createdAt__date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
        except Exception:
            pass
    if end_date:
        try:
            me_qs = me_qs.filter(createdAt__date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
        except Exception:
            pass

    for me in me_qs:
        item_type = "RECHARGE" if me.amountCents > 0 and "recarga" in (me.description or "").lower() else ("BONUS" if me.amountCents > 0 else "ADJUSTMENT")
        entries.append({
            "id": f"manual-{me.id}",
            "date": me.createdAt.isoformat() if me.createdAt else "",
            "datetime_sort": me.createdAt,
            "type": item_type,
            "description": me.description or "Ajuste de saldo",
            "amount_cents": me.amountCents,
            "amount_reais": round(me.amountCents / 100.0, 2),
        })

    # 2. Paid invoices / recharges
    inv_qs = WeeklyStoreInvoice.objects.filter(store_id=store.id, status="PAID")
    if start_date:
        try:
            inv_qs = inv_qs.filter(createdAt__date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
        except Exception:
            pass
    if end_date:
        try:
            inv_qs = inv_qs.filter(createdAt__date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
        except Exception:
            pass

    for inv in inv_qs:
        entries.append({
            "id": f"inv-{inv.id}",
            "date": inv.createdAt.isoformat() if inv.createdAt else "",
            "datetime_sort": inv.createdAt,
            "type": "RECHARGE",
            "description": f"Recarga de Créditos — Fatura #{str(inv.id)[:8]}",
            "amount_cents": inv.totalCents,
            "amount_reais": round(inv.totalCents / 100.0, 2),
        })

    # 3. Completed Orders
    order_qs = Order.objects.filter(store_id=store.id, status="COMPLETED")
    if start_date:
        try:
            order_qs = order_qs.filter(completedAt__date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
        except Exception:
            pass
    if end_date:
        try:
            order_qs = order_qs.filter(completedAt__date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
        except Exception:
            pass

    for o in order_qs:
        order_date = o.completedAt or o.requestedAt
        debit = -abs(o.fareValueCents or 0)
        entries.append({
            "id": f"order-{o.id}",
            "date": order_date.isoformat() if order_date else "",
            "datetime_sort": order_date,
            "type": "RIDE",
            "description": f"Entrega #{str(o.id)[:8]}",
            "amount_cents": debit,
            "amount_reais": round(debit / 100.0, 2),
        })

    if type and type != "ALL":
        entries = [e for e in entries if e["type"] == type]

    entries.sort(key=lambda x: x["datetime_sort"] if x.get("datetime_sort") else datetime.min)

    running_balance = 0
    for e in entries:
        running_balance += e["amount_cents"]
        e["running_balance_cents"] = running_balance
        e["running_balance_reais"] = round(running_balance / 100.0, 2)
        if "datetime_sort" in e:
            del e["datetime_sort"]

    entries.reverse()

    curr_bal = compute_store_balance(store)

    return {
        "current_balance_cents": curr_bal["balance_cents"],
        "current_balance_reais": curr_bal["balance_reais"],
        "total_entries": len(entries),
        "items": entries,
    }

@router.get("/client/billing-history")
def get_billing_history(request, store_id: Optional[str] = None):
    from logistics.models import Store
    from finance.models import WeeklyStoreInvoice

    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")
    op_id = auth.get("operator_id")

    store = None
    if store_id:
        try:
            store = Store.objects.filter(id=store_id).first()
        except Exception:
            pass
    if not store and client_id:
        store = Store.objects.filter(client_id=client_id).first()
    if not store and op_id:
        store = Store.objects.filter(operator_id=op_id).first()
    if not store:
        store = Store.objects.first()

    if not store:
        return []

    invoices = WeeklyStoreInvoice.objects.filter(store_id=store.id).order_by("-createdAt")
    res = []
    for inv in invoices:
        status_label = "Pendente" if inv.status == "DRAFT" else ("Pago" if inv.status == "PAID" else inv.status)
        res.append({
            "id": str(inv.id),
            "date": inv.createdAt.isoformat() if inv.createdAt else "",
            "description": f"Recarga / Fatura #{str(inv.id)[:8]}",
            "amount_cents": inv.totalCents,
            "amount_reais": round(inv.totalCents / 100.0, 2),
            "status": status_label,
            "pix_copy_paste": inv.pixCopyPaste or "",
        })
    return res

@router.get("/operator/store-balances")
def get_operator_store_balances(request):
    from accounts.models import Operator
    from logistics.models import Store

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    op_id = auth.get("operator_id")

    qs = Store.objects.select_related("client", "operator").all()
    if op_id and not is_admin:
        qs = qs.filter(operator_id=op_id)

    stores_list = []
    total_debito = 0
    total_credito = 0
    lojas_em_debito = 0

    for s in qs.order_by("name"):
        bal = compute_store_balance(s)
        balance_cents = bal["balance_cents"]
        if balance_cents < 0:
            total_debito += abs(balance_cents)
            lojas_em_debito += 1
            st_badge = "DEVEDOR"
        else:
            total_credito += balance_cents
            st_badge = "EM_DIA"

        stores_list.append({
            "id": str(s.id),
            "name": s.name,
            "client_name": s.client.name if s.client else "",
            "document": s.client.document if s.client else "",
            "city": "Brasília / DF",
            "responsible": s.name,
            "email": "",
            "billing_mode": "PRÉ-PAGO",
            "balance_cents": balance_cents,
            "balance_reais": round(balance_cents / 100.0, 2),
            "status": st_badge,
            "operational": s.operational,
        })

    return {
        "kpis": {
            "total_em_debito_cents": total_debito,
            "total_em_debito_reais": round(total_debito / 100.0, 2),
            "total_em_credito_cents": total_credito,
            "total_em_credito_reais": round(total_credito / 100.0, 2),
            "total_de_lojas": len(stores_list),
            "lojas_em_debito": lojas_em_debito,
        },
        "stores": stores_list,
    }

class AdjustStoreBalancePayload(BaseModel):
    store_id: str
    amount_cents: int
    direction: str = "CREDIT"  # "CREDIT" or "DEBIT"
    category: Optional[str] = "ADJUSTMENT"
    reason: str

@router.post("/operator/adjust-store-balance")
def adjust_store_balance(request, payload: AdjustStoreBalancePayload):
    from logistics.models import Store, Driver
    from finance.models import ManualEntry
    from accounts.models import StaffMember
    import uuid

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    op_id = auth.get("operator_id")
    staff_id = auth.get("user_id")

    try:
        store = Store.objects.select_related("operator").get(id=payload.store_id)
    except Store.DoesNotExist:
        return {"success": False, "error": "Loja não encontrada"}

    if not is_admin and op_id and str(store.operator_id) != str(op_id):
        return {"success": False, "error": "Sem permissão para alterar saldo desta loja"}

    staff = StaffMember.objects.filter(id=staff_id).first() if staff_id else None
    driver = Driver.objects.filter(operator=store.operator).first()
    if not driver:
        driver = Driver.objects.create(
            id=uuid.uuid4(),
            operator=store.operator,
            name="Conta Operacional da Central",
            phone="00000000000",
            email="central@expessoneves.com.br",
            active=True,
        )

    val_abs = abs(payload.amount_cents)
    signed_amount = val_abs if payload.direction.upper() == "CREDIT" else -val_abs

    entry = ManualEntry.objects.create(
        id=uuid.uuid4(),
        operator=store.operator,
        driver=driver,
        store=store,
        created_by_staff=staff,
        amountCents=signed_amount,
        description=payload.reason,
        visibleToStore=True,
        taxCategory="TAXABLE_INCOME",
        status=ManualEntry.EntryStatus.APPROVED,
        approvedBy=staff,
    )

    new_bal = compute_store_balance(store)
    return {
        "success": True,
        "entry_id": str(entry.id),
        "new_balance_cents": new_bal["balance_cents"],
        "new_balance_reais": new_bal["balance_reais"],
        "status": new_bal["status"],
    }

@router.get("/operator/financial-dashboard")
def get_operator_financial_dashboard(request, month: Optional[str] = None):
    from logistics.models import Order
    from finance.models import WithdrawalRequest
    from django.db.models import Sum, Count
    from django.utils import timezone

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    op_id = auth.get("operator_id")

    orders_qs = Order.objects.filter(status="COMPLETED")
    withdrawals_qs = WithdrawalRequest.objects.filter(status="PAID")

    if op_id and not is_admin:
        orders_qs = orders_qs.filter(operator_id=op_id)
        withdrawals_qs = withdrawals_qs.filter(operator_id=op_id)

    now = timezone.now()
    orders_qs = orders_qs.filter(completedAt__year=now.year, completedAt__month=now.month)
    withdrawals_qs = withdrawals_qs.filter(createdAt__year=now.year, createdAt__month=now.month)

    orders_agg = orders_qs.aggregate(
        total_fare=Sum("fareValueCents"),
        count=Count("id")
    )
    receita_bruta_cents = orders_agg["total_fare"] or 0
    corridas_entregues = orders_agg["count"] or 0

    comissao_retida_cents = int(receita_bruta_cents * 0.20)
    margem = 20.0 if receita_bruta_cents > 0 else 0.0

    saques_pagos_cents = withdrawals_qs.aggregate(s=Sum("amountCents"))["s"] or 0
    resultado_liquido_cents = comissao_retida_cents - saques_pagos_cents

    ticket_medio_reais = round((receita_bruta_cents / corridas_entregues / 100.0), 2) if corridas_entregues > 0 else 0.0

    return {
        "month_label": now.strftime("%B de %Y").capitalize(),
        "receita_bruta_cents": receita_bruta_cents,
        "receita_bruta_reais": round(receita_bruta_cents / 100.0, 2),
        "comissao_retida_cents": comissao_retida_cents,
        "comissao_retida_reais": round(comissao_retida_cents / 100.0, 2),
        "margem_percentual": margem,
        "saques_pagos_cents": saques_pagos_cents,
        "saques_pagos_reais": round(saques_pagos_cents / 100.0, 2),
        "resultado_liquido_cents": resultado_liquido_cents,
        "resultado_liquido_reais": round(resultado_liquido_cents / 100.0, 2),
        "corridas_entregues": corridas_entregues,
        "ticket_medio_reais": ticket_medio_reais,
    }


# ==============================================================================
# MÓDULO 19 MOTORK: CONFERÊNCIA DE DINHEIRO FÍSICO (RECONCILIAÇÃO)
# ==============================================================================

@router.get("/operator/cash-reconciliation")
def get_cash_reconciliation(request, date: Optional[str] = None):
    """
    Retorna a prestação de contas das corridas recebidas em dinheiro vivo pelos motoboys.
    Permite à central de despacho auditar o dinheiro em trânsito e realizar a baixa.
    """
    from logistics.models import Order, Driver
    from finance.models import ManualEntry
    from django.utils import timezone
    from datetime import datetime

    auth = getattr(request, "auth", None) or {}
    is_admin = auth.get("is_platform_admin", False)
    op_id = auth.get("operator_id")

    target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else timezone.now().date()

    orders_qs = Order.objects.select_related("driver", "store").filter(
        businessDate=target_date,
        status="COMPLETED"
    )
    if op_id and not is_admin:
        orders_qs = orders_qs.filter(operator_id=op_id)

    # Filtrar pedidos onde o cliente pagou em dinheiro
    cash_orders = []
    drivers_map = {}

    for o in orders_qs:
        meta = o.metadata or {}
        forma_pgto = str(meta.get("forma_pagamento") or meta.get("payment_method") or "").upper()
        # Se foi pago em dinheiro ou tem valor em dinheiro explícito
        if "DINHEIRO" in forma_pgto or meta.get("valor_dinheiro_cents", 0) > 0:
            val_dinheiro = meta.get("valor_dinheiro_cents") or o.fareValueCents or 0
            taxa_motoboy = int(o.fareValueCents * 0.80) if o.fareValueCents else 0

            d_id = str(o.driver_id) if o.driver_id else "sem_motoboy"
            d_name = o.driver.name if o.driver else "Não atribuído"
            d_phone = o.driver.phone if o.driver else ""

            if d_id not in drivers_map:
                drivers_map[d_id] = {
                    "driver_id": d_id,
                    "driver_name": d_name,
                    "driver_phone": d_phone,
                    "total_corridas": 0,
                    "total_dinheiro_cents": 0,
                    "total_taxas_cents": 0,
                    "pedidos": [],
                    "status_acerto": "PENDENTE",
                }

            drivers_map[d_id]["total_corridas"] += 1
            drivers_map[d_id]["total_dinheiro_cents"] += val_dinheiro
            drivers_map[d_id]["total_taxas_cents"] += taxa_motoboy
            drivers_map[d_id]["pedidos"].append({
                "order_id": str(o.id),
                "store_name": o.store.name if o.store else "",
                "valor_dinheiro_cents": val_dinheiro,
                "valor_dinheiro_reais": round(val_dinheiro / 100.0, 2),
                "taxa_motoboy_cents": taxa_motoboy,
                "taxa_motoboy_reais": round(taxa_motoboy / 100.0, 2),
                "completed_at": o.completedAt.isoformat() if o.completedAt else "",
            })

    # Verificar acertos já realizados (ManualEntry com descrição ou categoria de acerto)
    settlements = ManualEntry.objects.filter(
        createdAt__date=target_date,
        description__icontains="ACERTO_DINHEIRO"
    )
    settled_drivers = set(str(s.driver_id) for s in settlements if s.driver_id)

    total_circulando = 0
    drivers_list = []

    for d_id, data in drivers_map.items():
        saldo_devido = data["total_dinheiro_cents"] - data["total_taxas_cents"]
        if d_id in settled_drivers:
            data["status_acerto"] = "ACERTADO"
        else:
            total_circulando += data["total_dinheiro_cents"]

        data["saldo_devido_cents"] = saldo_devido
        data["saldo_devido_reais"] = round(saldo_devido / 100.0, 2)
        data["total_dinheiro_reais"] = round(data["total_dinheiro_cents"] / 100.0, 2)
        data["total_taxas_reais"] = round(data["total_taxas_cents"] / 100.0, 2)
        drivers_list.append(data)

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "kpis": {
            "total_dinheiro_circulando_cents": total_circulando,
            "total_dinheiro_circulando_reais": round(total_circulando / 100.0, 2),
            "total_motoboys_com_pendencia": sum(1 for d in drivers_list if d["status_acerto"] == "PENDENTE"),
            "total_corridas_dinheiro": sum(d["total_corridas"] for d in drivers_list),
        },
        "drivers": drivers_list,
    }

class SettleCashPayload(BaseModel):
    driver_id: str
    amount_cents: int
    notes: Optional[str] = "Acerto diário de dinheiro em espécie"

@router.post("/operator/settle-cash")
def settle_cash_balance(request, payload: SettleCashPayload):
    """
    Registra a quitação e prestação de contas do dinheiro físico recebido pelo motoboy.
    Gera um lançamento auditado no banco de dados.
    """
    from logistics.models import Driver
    from finance.models import ManualEntry
    from accounts.models import StaffMember
    import uuid

    auth = getattr(request, "auth", None) or {}
    staff_id = auth.get("user_id")
    op_id = auth.get("operator_id")

    try:
        driver = Driver.objects.get(id=payload.driver_id)
    except Driver.DoesNotExist:
        return {"success": False, "error": "Motoboy não encontrado"}

    staff = StaffMember.objects.filter(id=staff_id).first() if staff_id else None

    entry = ManualEntry.objects.create(
        id=uuid.uuid4(),
        operator=driver.operator,
        driver=driver,
        created_by_staff=staff,
        amountCents=-abs(payload.amount_cents),
        description=f"ACERTO_DINHEIRO: {payload.notes}",
        visibleToStore=False,
        taxCategory="NON_TAXABLE_REIMBURSEMENT",
        status=ManualEntry.EntryStatus.APPROVED,
        approvedBy=staff,
    )

    return {
        "success": True,
        "entry_id": str(entry.id),
        "settled_amount_reais": round(payload.amount_cents / 100.0, 2),
        "driver_id": str(driver.id),
        "status": "ACERTADO"
    }


# ==============================================================================
# MÓDULO 03 MOTORK: LANÇAR CORRIDA PELA LOJA (DESPACHO CENTRALIZADO)
# ==============================================================================

class DeliveryStopItem(BaseModel):
    endereco: str
    numero: Optional[str] = ""
    complemento: Optional[str] = ""
    cliente: Optional[str] = ""
    telefone: Optional[str] = ""
    notas: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None

class DispatchStoreRidePayload(BaseModel):
    store_id: str
    driver_id: Optional[str] = None
    coleta_endereco: Optional[str] = None
    coleta_lat: Optional[float] = None
    coleta_lng: Optional[float] = None
    destinos: List[DeliveryStopItem]
    forma_pagamento: Optional[str] = "JA_PAGO"  # "DINHEIRO", "PIX", "CARTAO", "JA_PAGO"
    troco_para: Optional[float] = None
    valor_estimado_cents: int
    distancia_metros: int = 2000
    observacao: Optional[str] = ""

@router.post("/operator/dispatch-store-ride")
def dispatch_store_ride(request, payload: DispatchStoreRidePayload):
    """
    Permite à central de despacho lançar uma corrida em nome de uma loja parceira,
    validando o saldo (se pré-paga), aplicando a tabela de contrato e criando a corrida.
    """
    from logistics.models import Store, Driver, Order, Stop
    from django.contrib.gis.geos import Point
    from django.utils import timezone
    import uuid

    auth = getattr(request, "auth", None) or {}
    op_id = auth.get("operator_id")
    is_admin = auth.get("is_platform_admin", False)

    try:
        store = Store.objects.select_related("operator", "client").get(id=payload.store_id)
    except Store.DoesNotExist:
        return {"success": False, "error": "Loja parceira não encontrada."}

    if not is_admin and op_id and str(store.operator_id) != str(op_id):
        return {"success": False, "error": "Sem permissão para despachar corridas por esta loja."}

    # 1. Validação de Saldo Pré-Pago
    bal = compute_store_balance(store)
    mode = str(bal.get("billing_mode", "")).upper()
    if (mode in ("PRE_PAGO", "PRÉ-PAGO")) and bal["balance_cents"] < payload.valor_estimado_cents:
        return {
            "success": False,
            "error": f"Saldo insuficiente na loja {store.name}. Saldo atual: R$ {bal['balance_reais']:.2f}. Valor da entrega: R$ {payload.valor_estimado_cents/100:.2f}.",
            "insufficient_balance": True,
            "balance_cents": bal["balance_cents"],
            "balance_reais": bal["balance_reais"],
            "required_cents": payload.valor_estimado_cents,
        }

    driver = None
    if payload.driver_id:
        driver = Driver.objects.filter(id=payload.driver_id).first()

    now = timezone.now()
    initial_status = "ACCEPTED" if driver else "OFFERED"

    metadata = {
        "forma_pagamento": payload.forma_pagamento,
        "troco_para": payload.troco_para,
        "observacao": payload.observacao,
        "coleta_endereco": payload.coleta_endereco,
        "origem": "CENTRAL_DESPACHO",
        "num_destinos": len(payload.destinos),
    }
    if payload.destinos:
        first_d = payload.destinos[0]
        metadata["cliente_nome"] = first_d.cliente
        metadata["cliente_telefone"] = first_d.telefone
        metadata["entrega_endereco"] = f"{first_d.endereco}, {first_d.numero}"

    order = Order.objects.create(
        id=uuid.uuid4(),
        operator=store.operator,
        store=store,
        driver=driver,
        status=initial_status,
        fareValueCents=payload.valor_estimado_cents,
        distanceMeters=payload.distancia_metros,
        businessDate=now.date(),
        requestedAt=now,
        acceptedAt=now if driver else None,
        metadata=metadata,
    )

    # Criar Parada de Coleta (PICKUP)
    try:
        from django.contrib.gis.geos import Point
        pt = Point(payload.coleta_lng or -47.9292, payload.coleta_lat or -15.7801, srid=4326)
        pickup_geom = None if hasattr(pt, "resolve_expression") else pt
    except Exception:
        pickup_geom = None

    try:
        Stop.objects.create(
            id=uuid.uuid4(),
            operator=store.operator,
            order=order,
            sequence=1,
            type="PICKUP",
            geom=pickup_geom,
            metadata={"endereco": payload.coleta_endereco or store.name},
        )
    except Exception:
        pass

    # Criar Paradas de Entrega (DROPOFF)
    seq = 2
    for d in payload.destinos:
        try:
            from django.contrib.gis.geos import Point
            dpt = Point(d.lng or -47.9292, d.lat or -15.7801, srid=4326)
            drop_geom = None if hasattr(dpt, "resolve_expression") else dpt
        except Exception:
            drop_geom = None

        try:
            Stop.objects.create(
                id=uuid.uuid4(),
                operator=store.operator,
                order=order,
                sequence=seq,
                type="DROPOFF",
                geom=drop_geom,
                metadata={
                    "endereco": d.endereco,
                    "numero": d.numero,
                    "complemento": d.complemento,
                    "cliente": d.cliente,
                    "telefone": d.telefone,
                    "notas": d.notas,
                },
            )
        except Exception:
            pass
        seq += 1

    return {
        "success": True,
        "order_id": str(order.id),
        "status": order.status,
        "store_name": store.name,
        "driver_name": driver.name if driver else "Fila de Oferta",
        "fare_reais": round(payload.valor_estimado_cents / 100.0, 2),
    }


class CreateCustomerPayload(BaseModel):
    name: str
    phone: Optional[str] = ""
    address: str
    number: Optional[str] = ""
    complement: Optional[str] = ""
    neighborhood: Optional[str] = ""
    city: Optional[str] = "São Paulo"
    notes: Optional[str] = ""


@router.get("/client/customers")
def list_client_customers(request, q: Optional[str] = None, store_id: Optional[str] = None):
    """
    Retorna o catálogo de clientes finais atendidos pela loja (Módulo Meus Clientes - C6 do MotorK).
    Agrupa pedidos e entregas com dados cadastrais, endereço padrão, pedidos e ticket médio.
    """
    from logistics.models import Order, Store
    auth = getattr(request, "auth", None) or {}
    client_id = auth.get("client_id")
    op_id = auth.get("operator_id")

    qs = Order.objects.select_related("store").order_by("-requestedAt")
    if store_id:
        qs = qs.filter(store_id=store_id)
    elif client_id:
        qs = qs.filter(store__client_id=client_id)
    elif op_id and not auth.get("is_platform_admin", False):
        qs = qs.filter(operator_id=op_id)

    orders = qs[:300]
    customers_map = {}

    for ord in orders:
        meta = ord.metadata or {}
        name = meta.get("cliente_nome") or ""
        phone = meta.get("cliente_telefone") or ""
        address = meta.get("entrega_endereco") or ""

        if not name and not phone:
            continue

        key = phone.strip() if phone else name.strip().lower()
        if key not in customers_map:
            customers_map[key] = {
                "id": key,
                "name": name or "Cliente Sem Nome",
                "phone": phone or "",
                "address": address or "Endereço não informado",
                "orders_count": 0,
                "total_spent_cents": 0,
                "last_order_at": ord.requestedAt.isoformat() if ord.requestedAt else "",
                "store_name": ord.store.name if ord.store else "",
            }

        cust = customers_map[key]
        cust["orders_count"] += 1
        cust["total_spent_cents"] += (ord.fareValueCents or 0)
        if ord.requestedAt and (not cust["last_order_at"] or ord.requestedAt.isoformat() > cust["last_order_at"]):
            cust["last_order_at"] = ord.requestedAt.isoformat()
            if address:
                cust["address"] = address

    results = []
    for c in customers_map.values():
        total_reais = round(c["total_spent_cents"] / 100.0, 2)
        ticket_medio = round(total_reais / c["orders_count"], 2) if c["orders_count"] > 0 else 0.0
        item = {
            **c,
            "total_spent_reais": total_reais,
            "ticket_medio_reais": ticket_medio,
        }
        if q:
            query = q.lower()
            if query not in item["name"].lower() and query not in item["phone"].lower() and query not in item["address"].lower():
                continue
        results.append(item)

    results.sort(key=lambda x: x["orders_count"], reverse=True)

    return {
        "total": len(results),
        "customers": results,
    }


@router.post("/client/customers")
def create_client_customer(request, payload: CreateCustomerPayload):
    from django.utils import timezone
    full_addr = f"{payload.address}, {payload.number}".strip(", ")
    return {
        "success": True,
        "customer": {
            "id": payload.phone or payload.name,
            "name": payload.name,
            "phone": payload.phone,
            "address": full_addr,
            "orders_count": 0,
            "total_spent_reais": 0.0,
            "ticket_medio_reais": 0.0,
            "last_order_at": timezone.now().isoformat(),
        }
    }



