from ninja import Router
from typing import List, Dict
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

from finance.models import (
    Wallet,
    WalletTransaction,
    WithdrawalRequest,
    ManualEntry,
    WeeklyStoreInvoice,
)
from logistics.models import Driver, Store
from accounts.auth import require_role
from config.idempotency import idempotent

from shared_schemas.finance import (
    WalletResponse,
    WithdrawalRequestPayload,
    WithdrawalResponse,
    ManualEntryPayload,
    ManualEntryResponse,
    InvoiceResponse,
    TransactionResponse,
)

# Schemas para o Painel Gerencial
from pydantic import BaseModel


class GerencialKpisResponse(BaseModel):
    totalLojas: int
    totalMotoboys: int
    faturamentoMes: int  # em centavos
    semanaAtual: int  # em centavos


class GerencialSnapshotResponse(BaseModel):
    company_id: str
    week_start: str
    total_liquido: int  # em centavos
    total_corridas: int


class GerencialResponse(BaseModel):
    kpis: GerencialKpisResponse
    snapshots: List[GerencialSnapshotResponse]
    companies: List[Dict]  # dados das lojas


router = Router(tags=["Finance", "Gerencial"])


@router.get("/wallet/balance", response=WalletResponse)
def get_balance(request):
    driver_uid = request.auth.get("sub")
    from django.shortcuts import get_object_or_404

    driver = get_object_or_404(Driver, supabase_uid=driver_uid)

    wallet, _ = Wallet.objects.get_or_create(driver=driver, operator=driver.operator)
    return wallet


@router.post("/wallet/withdraw", response=WithdrawalResponse)
@idempotent(timeout=86400, schema=WithdrawalResponse)
def request_withdrawal(request, payload: WithdrawalRequestPayload):
    driver_uid = request.auth.get("sub")
    from django.shortcuts import get_object_or_404

    driver = get_object_or_404(Driver, supabase_uid=driver_uid)

    if not driver.active:
        from ninja.errors import HttpError

        raise HttpError(403, "Motorista inativo.")

    with transaction.atomic():
        from finance.models import OperatorInternalWallet

        # Sempre travar OperatorInternalWallet PRIMEIRO, depois Wallet (prevenção de Deadlock)
        operator_wallet, _ = OperatorInternalWallet.objects.get_or_create(
            operator=driver.operator
        )
        operator_wallet = OperatorInternalWallet.objects.select_for_update().get(
            pk=operator_wallet.pk
        )
        wallet, _ = Wallet.objects.get_or_create(
            driver=driver, operator=driver.operator
        )
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.balanceCents < payload.amountCents:
            from ninja.errors import HttpError

            raise HttpError(400, "Saldo insuficiente.")

        withdrawal = WithdrawalRequest.objects.create(
            operator=driver.operator,
            driver=driver,
            amountCents=payload.amountCents,
            pixKey=payload.pixKey,
            status=WithdrawalRequest.WithdrawalStatus.PENDING,
        )

        # Cria a transação deduzindo o saldo imediatamente para evitar double spending
        WalletTransaction.objects.create(
            operator=driver.operator,
            source_driver_wallet=wallet,
            destination_operator_wallet=operator_wallet,
            amountCents=payload.amountCents,
            category=WalletTransaction.TransactionCategory.PAYOUT,
            taxCategory=WalletTransaction.TaxCategory.NON_TAXABLE_REIMBURSEMENT,
        )

        return withdrawal


@router.post("/manual-entry", response=ManualEntryResponse)
def create_manual_entry(request, payload: ManualEntryPayload):
    staff = require_role(["ADMIN", "MANAGER"])(request)

    with transaction.atomic():
        driver = Driver.objects.get(pk=payload.driver_id, operator=staff.operator)
        store = None
        if payload.store_id:
            store = Store.objects.get(pk=payload.store_id, operator=staff.operator)

        entry = ManualEntry.objects.create(
            operator=staff.operator,
            driver=driver,
            store=store,
            created_by_staff=staff,
            amountCents=payload.amountCents,
            description=payload.description,
            visibleToStore=payload.visibleToStore,
            taxCategory=payload.taxCategory,
            status=ManualEntry.EntryStatus.PENDING_APPROVAL,
        )
        return entry


@router.get("/invoices", response=List[InvoiceResponse])
def list_invoices(request):
    staff = require_role(["ADMIN", "MANAGER", "VIEWER"])(request)
    return list(
        WeeklyStoreInvoice.objects.filter(operator=staff.operator).order_by(
            "-createdAt"
        )
    )


from ninja.pagination import paginate


@router.get("/transactions", response=List[TransactionResponse])
@paginate
def list_transactions(request):
    driver_uid = request.auth.get("sub")
    from django.shortcuts import get_object_or_404

    driver = get_object_or_404(Driver, supabase_uid=driver_uid)

    # Lista transações onde a carteira de destino é a do motorista (créditos)
    # Ou a de origem é a dele (débitos/saques)
    wallet = Wallet.objects.get(driver=driver, operator=driver.operator)
    from django.db.models import Q

    transactions = WalletTransaction.objects.filter(
        Q(destination_driver_wallet=wallet) | Q(source_driver_wallet=wallet),
        operator=driver.operator,
    ).order_by("-createdAt")

    return transactions


# ── Endpoints para o Painel Gerencial (BI Executivo Básico) ────────────────────────


@router.get("/gerencial", response=GerencialResponse)
def get_gerencial_data(request):
    """
    Retorna todos os dados para o painel gerencial: KPIs, snapshots (tendência semanal),
    e dados das lojas (empresas).
    """
    staff = require_role(["ADMIN", "MANAGER", "VIEWER", "OPERATOR_ROLE"])(request)
    operator = staff.operator

    # 1. Dados das lojas (Companies)
    # No nosso modelo, as "empresas" são os Client (marcas) e as "lojas" são Store
    # Para manter a compatibilidade com o frontend, vamos retornar:
    companies = []
    for store in Store.objects.filter(
        operator=operator, operational=True
    ).select_related("client"):
        client_has = getattr(store, "client", None)
        companies.append(
            {
                "id": str(store.id),
                "machine_empresa_id": str(
                    store.id
                ),  # compatibilidade com frontend antigo
                "nome": store.name,
                "cnpj": client_has.document if client_has else "",
                "ativo": store.operational,
            }
        )

    # 2. Dados dos drivers
    drivers = Driver.objects.filter(operator=operator, active=True).count()

    # 3. KPIs Globais
    today = timezone.localdate()
    first_day_of_month = today.replace(day=1)
    last_day_of_month = (first_day_of_month + timedelta(days=32)).replace(
        day=1
    ) - timedelta(days=1)

    # Faturamento do mês (total de totalCents das WeeklyStoreInvoice)
    faturamento_mes = (
        WeeklyStoreInvoice.objects.filter(
            operator=operator,
            startDate__gte=first_day_of_month,
            startDate__lte=last_day_of_month,
            status=WeeklyStoreInvoice.InvoiceStatus.FINALIZED,
        ).aggregate(total=Sum("totalCents"))["total"]
        or 0
    )

    # Semana atual: calcula startDate desta semana (segunda-feira)
    today_weekday = today.weekday()
    week_start = today - timedelta(days=today_weekday)
    week_end = week_start + timedelta(days=6)

    semana_atual = (
        WeeklyStoreInvoice.objects.filter(
            operator=operator,
            startDate=week_start,
            status=WeeklyStoreInvoice.InvoiceStatus.FINALIZED,
        ).aggregate(total=Sum("totalCents"))["total"]
        or 0
    )

    kpis = GerencialKpisResponse(
        totalLojas=len(companies),
        totalMotoboys=drivers,
        faturamentoMes=faturamento_mes,
        semanaAtual=semana_atual,
    )

    # 4. Snapshots para tendência semanal e ranking de lojas
    snapshots_query = (
        WeeklyStoreInvoice.objects.filter(
            operator=operator, status=WeeklyStoreInvoice.InvoiceStatus.FINALIZED
        )
        .select_related("store")
        .order_by("-startDate")[:50]
    )
    snapshots = []

    for invoice in snapshots_query:
        # Calcula total de corridas: número de DailyCreditCalculation + Order completadas?
        # Vamos simplificar: contar número de DailyCreditCalculation da semana
        from finance.models import DailyCreditCalculation

        total_corridas = DailyCreditCalculation.objects.filter(
            operator=operator,
            store=invoice.store,
            date__gte=invoice.startDate,
            date__lte=invoice.endDate,
        ).count()

        snapshots.append(
            GerencialSnapshotResponse(
                company_id=str(invoice.store.id),
                week_start=str(invoice.startDate),
                total_liquido=invoice.totalCents or 0,
                total_corridas=total_corridas,
            )
        )

    return GerencialResponse(kpis=kpis, snapshots=snapshots, companies=companies)
