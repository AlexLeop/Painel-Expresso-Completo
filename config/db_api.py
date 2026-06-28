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
def get_entries(request, company_id: str = None, start: str = None, end: str = None):
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
            "driverName": entry.driver.name if entry.driver else "",
            "motoboy": entry.driver.name if entry.driver else "",
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
def get_company_drivers(request, company_id: int = None, active_only: int = 0):
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
            "active": sd.is_active
        })
    return res

@router.patch("/company-drivers")
def update_company_driver(request, payload: CompanyDriverPayload):
    # Mock implementation to prevent frontend crash
    return {"success": True}

@router.get("/configs")
def get_configs(request, company_id: int = None):
    # Return mock config to prevent frontend crash
    return [{"id": 1, "company_id": company_id or 1, "chave": "tema", "valor": "light"}]

@router.post("/configs")
def create_config(request, payload: dict):
    return {"success": True}

@router.put("/configs")
def update_config(request, payload: dict):
    return {"success": True}

@router.get("/snapshots")
def get_snapshots(request, company_id: int = None, limit: int = 50):
    # Mock snapshot to prevent crash in dashboards
    return []

@router.get("/positions")
def get_positions(request, max_age_minutes: int = 720, limit: int = 1000):
    # Return empty positions array
    return []


