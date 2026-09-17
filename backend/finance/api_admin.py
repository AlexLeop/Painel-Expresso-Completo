from ninja import Router, Schema
from typing import List, Optional
from uuid import UUID
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from ninja.errors import HttpError

from finance.models import (
    Contract,
    KmFaixa,
    FaixaHoras,
    WithdrawalRequest,
    PayoutPolicyConfig,
)
from logistics.models import Store, Driver
from accounts.models import Operator, StaffMember
from accounts.auth import get_staff_member
from config.core_models import tenant_context
from finance.baas_client import EfiBaasClient
from finance.services import AtomicRefundEngine
from finance.tasks import execute_pix_payout_task
from shared_schemas.finance import (
    WithdrawalAdminDetailResponse,
    WithdrawalRejectionPayload,
    BulkApprovalPayload,
    PayoutPolicyConfigSchema,
    BaasBalanceResponse,
)

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
    operator_id = request.auth.get("operator_id")
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
                returnFeeBps=data.returnFeeBps,
            )

            if data.km_faixas:
                for k in data.km_faixas:
                    KmFaixa.objects.create(
                        operator=operator,
                        contract=contract,
                        kmStart=k.kmStart,
                        kmEnd=k.kmEnd,
                        priceCents=k.priceCents,
                    )

            if data.faixa_horas and data.compensationMode == "GARANTIDA_HORAS":
                for f in data.faixa_horas:
                    FaixaHoras.objects.create(
                        operator=operator,
                        contract=contract,
                        hoursMin=f.hoursMin,
                        hoursMax=f.hoursMax,
                        priceCents=f.priceCents,
                    )

        return {"id": str(contract.id), "status": "created"}


@router.get("/contracts")
def list_contracts(request):
    operator_id = request.auth.get("operator_id")
    with tenant_context(operator_id):
        contracts = Contract.objects.filter(operator_id=operator_id)
        return [{"id": str(c.id), "store_id": str(c.store.id if c.store else "")} for c in contracts]


def _resolve_operator(request):
    staff = get_staff_member(request)
    if staff and staff.operator:
        return staff.operator, staff
    op_id = request.auth.get("operator_id") if request.auth else None
    if op_id:
        try:
            return Operator.objects.get(id=op_id), None
        except Operator.DoesNotExist:
            pass
    # Fallback para primeiro operador em ambiente local/dev se aplicável
    op = Operator.objects.first()
    if op:
        return op, None
    raise HttpError(401, "Operador não autenticado.")


@router.get("/withdrawals", response=List[WithdrawalAdminDetailResponse])
def list_withdrawals(
    request,
    status: Optional[str] = None,
    driver_id: Optional[UUID] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Lista solicitações de saque com filtros por status, motorista e texto de busca.
    """
    operator, _ = _resolve_operator(request)
    qs = (
        WithdrawalRequest.objects.filter(operator=operator)
        .select_related("driver")
        .order_by("-createdAt")
    )

    if status:
        qs = qs.filter(status=status.upper())
    if driver_id:
        qs = qs.filter(driver_id=driver_id)
    if search:
        qs = qs.filter(
            Q(driver__name__icontains=search)
            | Q(pixKey__icontains=search)
            | Q(baasTransactionId__icontains=search)
        )

    items = qs[offset : offset + limit]
    results = []
    for w in items:
        results.append(
            WithdrawalAdminDetailResponse(
                id=w.id,
                driver_id=w.driver.id,
                driver_name=w.driver.name,
                driver_phone=w.driver.phone,
                amountCents=w.amountCents,
                feeAmountCents=w.feeAmountCents,
                netAmountCents=w.netAmountCents,
                status=w.status,
                pixKey=w.pixKey,
                pixKeyType=w.pixKeyType,
                approvalMode=w.approvalMode,
                baasProvider=w.baasProvider,
                baasTransactionId=w.baasTransactionId,
                failureReason=w.failureReason,
                rejectionReason=w.rejectionReason,
                approvedAt=w.approvedAt,
                processedAt=w.processedAt,
                createdAt=w.createdAt,
            )
        )
    return results


@router.post("/withdrawals/{withdrawal_id}/approve")
def approve_withdrawal(request, withdrawal_id: UUID):
    """
    Aprova individualmente uma solicitação de saque pendente e despacha a task Celery.
    """
    operator, staff = _resolve_operator(request)

    with transaction.atomic():
        try:
            withdrawal = (
                WithdrawalRequest.objects.select_for_update()
                .get(id=withdrawal_id, operator=operator)
            )
        except WithdrawalRequest.DoesNotExist:
            raise HttpError(404, "Solicitação de saque não encontrada.")

        if withdrawal.status != WithdrawalRequest.WithdrawalStatus.PENDING:
            raise HttpError(
                400,
                f"Apenas saques com status PENDING podem ser aprovados (atual: {withdrawal.status}).",
            )

        withdrawal.status = WithdrawalRequest.WithdrawalStatus.PROCESSING
        if staff:
            withdrawal.approvedBy = staff
        withdrawal.approvedAt = timezone.now()
        withdrawal.save(update_fields=["status", "approvedBy", "approvedAt", "updatedAt"])

        w_id = str(withdrawal.id)
        transaction.on_commit(lambda: execute_pix_payout_task.delay(w_id))  # type: ignore

    return {
        "success": True,
        "withdrawal_id": str(withdrawal_id),
        "status": "PROCESSING",
        "message": "Saque aprovado com sucesso. Disparo PIX em andamento.",
    }


@router.post("/withdrawals/bulk-approve")
def bulk_approve_withdrawals(request, payload: BulkApprovalPayload):
    """
    Aprova em lote múltiplas solicitações de saque pendentes.
    """
    operator, staff = _resolve_operator(request)
    approved_ids = []

    for w_id in payload.withdrawal_ids:
        with transaction.atomic():
            try:
                w = (
                    WithdrawalRequest.objects.select_for_update()
                    .get(id=w_id, operator=operator, status=WithdrawalRequest.WithdrawalStatus.PENDING)
                )
                w.status = WithdrawalRequest.WithdrawalStatus.PROCESSING
                if staff:
                    w.approvedBy = staff
                w.approvedAt = timezone.now()
                w.save(update_fields=["status", "approvedBy", "approvedAt", "updatedAt"])

                w_id_str = str(w.id)
                transaction.on_commit(lambda wid=w_id_str: execute_pix_payout_task.delay(wid))  # type: ignore
                approved_ids.append(w_id_str)
            except WithdrawalRequest.DoesNotExist:
                continue

    return {
        "success": True,
        "approved_count": len(approved_ids),
        "approved_ids": approved_ids,
    }


@router.post("/withdrawals/{withdrawal_id}/reject")
def reject_withdrawal(request, withdrawal_id: UUID, payload: WithdrawalRejectionPayload):
    """
    Rejeita a solicitação de saque, devolvendo integralmente o saldo à carteira do motorista.
    """
    operator, staff = _resolve_operator(request)

    try:
        withdrawal = WithdrawalRequest.objects.get(id=withdrawal_id, operator=operator)
    except WithdrawalRequest.DoesNotExist:
        raise HttpError(404, "Solicitação de saque não encontrada.")

    if withdrawal.status not in (
        WithdrawalRequest.WithdrawalStatus.PENDING,
        WithdrawalRequest.WithdrawalStatus.PROCESSING,
    ):
        raise HttpError(
            400,
            f"Não é possível rejeitar um saque no status atual ({withdrawal.status}).",
        )

    # Executa o estorno atômico contábil
    refunded = AtomicRefundEngine.refund_failed_withdrawal(
        withdrawal=withdrawal,
        reason=payload.reason,
    )

    if staff:
        refunded.approvedBy = staff
        refunded.save(update_fields=["approvedBy", "updatedAt"])

    return {
        "success": True,
        "withdrawal_id": str(withdrawal_id),
        "status": "FAILED",
        "reason": payload.reason,
        "message": "Saque rejeitado e saldo estornado com sucesso para o motorista.",
    }


@router.get("/payout-policy", response=PayoutPolicyConfigSchema)
def get_payout_policy(request):
    """
    Retorna a política de liberação de saques PIX ativa para o operador.
    """
    operator, _ = _resolve_operator(request)
    policy = PayoutPolicyConfig.objects.filter(operator=operator).first()
    if not policy:
        # Retorna os defaults do sistema
        return PayoutPolicyConfigSchema()
    return policy


@router.put("/payout-policy", response=PayoutPolicyConfigSchema)
def update_payout_policy(request, payload: PayoutPolicyConfigSchema):
    """
    Atualiza os limiares de aprovação automática, tarifas de saque e canais de notificação.
    """
    operator, _ = _resolve_operator(request)
    policy, _ = PayoutPolicyConfig.objects.get_or_create(operator=operator)

    policy.mode = payload.mode
    policy.autoThresholdCents = payload.autoThresholdCents
    policy.dailyLimitPerDriverCents = payload.dailyLimitPerDriverCents
    policy.minWithdrawalCents = payload.minWithdrawalCents
    policy.payoutFeeMode = payload.payoutFeeMode
    policy.payoutFeeCents = payload.payoutFeeCents
    policy.notifyPushEnabled = payload.notifyPushEnabled
    policy.notifyWhatsappEnabled = payload.notifyWhatsappEnabled
    policy.save()

    return policy


@router.get("/baas-balance", response=BaasBalanceResponse)
def get_baas_balance(request):
    """
    Consulta em tempo real o saldo disponível na conta jurídica da Efí Pay para alertas e KPIs.
    """
    client = EfiBaasClient()
    balance = client.get_account_balance()
    return BaasBalanceResponse(
        saldo=balance.get("saldo", 0.0),
        saldo_cents=balance.get("saldo_cents", 0),
        bloqueado=balance.get("bloqueado", 0.0),
        mock=balance.get("mock", False),
    )

