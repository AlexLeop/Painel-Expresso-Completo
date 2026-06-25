from ninja import Router, Schema
from typing import List, Optional
from finance.models import Contract, KmFaixa, FaixaHoras
from logistics.models import Store
from accounts.models import Operator
from config.core_models import tenant_context
from django.db import transaction
from ninja.errors import HttpError

router = Router(tags=["Admin - Finance"])

class KmFaixaSchema(Schema):
    kmStart: int
    kmEnd: int
    priceCents: int

class FaixaHorasSchema(Schema):
    hoursMin: float
    hoursMax: float
    priceCents: int

class ContractWizardSchema(Schema):
    store_id: str
    compensationMode: str
    rideFeePerDeliveryCents: int
    minimumRidesFeeFloorCents: int
    minimumFloorBps: int
    adminTaxThresholdCents: int
    adminTaxFixedAmountCents: int
    adminTaxBps: int
    supervisionFeePerWeekCents: int
    dailyRateWeekdayCents: int
    dailyRateSaturdayCents: int
    dailyRateSundayCents: int
    dailyRateHolidayCents: int
    kmExcedenteValorCents: int
    allowAutomaticGrouping: bool
    cloudOverflowAllowed: bool
    maxStopsPerManifest: int
    maxDetourPercent: int
    cutoffHour: int
    cutoffMinute: int
    returnFeeBps: int
    
    km_faixas: Optional[List[KmFaixaSchema]] = None
    faixa_horas: Optional[List[FaixaHorasSchema]] = None

@router.post("/contracts/wizard")
def create_contract_wizard(request, data: ContractWizardSchema):
    """
    [Flow 3.3] Wizard Contract.
    Criação transacional do contrato e suas sub-regras.
    """
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        operator = Operator.objects.get(id=operator_id)
        store = Store.objects.get(id=data.store_id, operator_id=operator_id)
        
        with transaction.atomic():
            contract = Contract.objects.create(
                operator=operator,
                store=store,
                compensationMode=data.compensationMode,
                rideFeePerDeliveryCents=data.rideFeePerDeliveryCents,
                minimumRidesFeeFloorCents=data.minimumRidesFeeFloorCents,
                minimumFloorBps=data.minimumFloorBps,
                adminTaxThresholdCents=data.adminTaxThresholdCents,
                adminTaxFixedAmountCents=data.adminTaxFixedAmountCents,
                adminTaxBps=data.adminTaxBps,
                supervisionFeePerWeekCents=data.supervisionFeePerWeekCents,
                dailyRateWeekdayCents=data.dailyRateWeekdayCents,
                dailyRateSaturdayCents=data.dailyRateSaturdayCents,
                dailyRateSundayCents=data.dailyRateSundayCents,
                dailyRateHolidayCents=data.dailyRateHolidayCents,
                kmExcedenteValorCents=data.kmExcedenteValorCents,
                allowAutomaticGrouping=data.allowAutomaticGrouping,
                cloudOverflowAllowed=data.cloudOverflowAllowed,
                maxStopsPerManifest=data.maxStopsPerManifest,
                maxDetourPercent=data.maxDetourPercent,
                cutoffHour=data.cutoffHour,
                cutoffMinute=data.cutoffMinute,
                returnFeeBps=data.returnFeeBps
            )
            
            if data.km_faixas:
                for k in data.km_faixas:
                    KmFaixa.objects.create(
                        operator=operator,
                        contract=contract,
                        kmStart=k.kmStart,
                        kmEnd=k.kmEnd,
                        priceCents=k.priceCents
                    )
                    
            if data.faixa_horas and data.compensationMode == 'GARANTIDA_HORAS':
                for f in data.faixa_horas:
                    FaixaHoras.objects.create(
                        operator=operator,
                        contract=contract,
                        hoursMin=f.hoursMin,
                        hoursMax=f.hoursMax,
                        priceCents=f.priceCents
                    )
            
        return {"id": str(contract.id), "status": "created"}

@router.get("/contracts")
def list_contracts(request):
    operator_id = request.auth.get('operator_id')
    with tenant_context(operator_id):
        contracts = Contract.objects.filter(operator_id=operator_id)
        return [{"id": str(c.id), "store_id": str(c.store_id)} for c in contracts]

