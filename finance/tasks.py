from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from finance.models import (
    Wallet,
    WalletTransaction,
    DailyCreditCalculation,
    OperatorInternalWallet,
    FaixaHoras,
    Contract,
)
from logistics.models import Order, ScheduleEntry
from accounts.models import Operator
from django.db import transaction
import redis
from config.redis_client import get_redis
import os

r = get_redis()


@shared_task
def compute_daily_credit(target_cutoff_hour=None):
    """
    Roda dinamicamente calculando a competência (business_date) baseada
    no cutoffHour do contrato da loja, eliminando o Bug da Meia-Noite.
    """
    timezone.localtime()

    operators = Operator.objects.values_list("id", flat=True)
    total_processed = 0
    for operator_id in operators:
        from config.core_models import tenant_context

        with tenant_context(operator_id):
            from logistics.models import Store
            from collections import defaultdict
            from django.db.models import Exists, OuterRef, Q
            from finance.models import ManualEntry

            stores = Store.objects.select_related("contract").all()

            for store in stores:
                if not hasattr(store, "contract"):
                    continue
                contract = store.contract

                # Filter by cutoff hour if running in HOURLY mode
                if (
                    target_cutoff_hour is not None
                    and contract.cutoffHour != target_cutoff_hour
                ):
                    continue

                # Cálculo determinístico
                current_time = timezone.localtime()
                business_date_limit = (
                    current_time - timedelta(hours=contract.cutoffHour, minutes=30)
                ).date()

                # Catch-up Automático
                schedules = (
                    ScheduleEntry.objects.filter(
                        store=store, date__lte=business_date_limit
                    )
                    .annotate(
                        is_billed=Exists(
                            DailyCreditCalculation.objects.filter(
                                store=store,
                                driver=OuterRef("driver"),
                                date=OuterRef("date"),
                                status__in=[
                                    DailyCreditCalculation.CreditStatus.CREDITED,
                                    DailyCreditCalculation.CreditStatus.PENDING,
                                ],
                            )
                        )
                    )
                    .filter(is_billed=False)
                    .select_related("driver", "operator", "turno")
                )

                if not schedules.exists():
                    continue
                
                # --- OTIMIZAÇÃO: BATCH FETCHING PARA EVITAR N+1 QUERIES ---
                schedule_list = list(schedules)
                driver_ids = {s.driver_id for s in schedule_list}
                dates = {s.date for s in schedule_list}
                
                # 1. Fetch Orders
                orders_qs = Order.objects.filter(
                    operator_id=operator_id,
                    store=store,
                    driver_id__in=driver_ids,
                    businessDate__in=dates,
                    status__in=[
                        Order.OrderStatus.COMPLETED,
                        Order.OrderStatus.RETURNED,
                        Order.OrderStatus.CANCELED_IN_TRANSIT,
                    ],
                )
                orders_by_driver_date = defaultdict(list)
                for order in orders_qs:
                    orders_by_driver_date[(order.driver_id, order.businessDate)].append(order)
                
                # 2. Fetch Advances (ManualEntry)
                advances_qs = ManualEntry.objects.filter(
                    Q(store=store) | Q(store__isnull=True),
                    operator_id=operator_id,
                    driver_id__in=driver_ids,
                    status=ManualEntry.EntryStatus.APPROVED,
                    taxCategory=WalletTransaction.TaxCategory.DEDUCTION,
                    createdAt__date__in=dates,
                ).values('driver_id', 'createdAt__date').annotate(total=Sum('amountCents'))
                
                advances_by_driver_date = defaultdict(int)
                for adv in advances_qs:
                    advances_by_driver_date[(adv['driver_id'], adv['createdAt__date'])] = adv['total'] or 0

                # 3. Cache FaixaHoras para a Loja atual
                faixas = list(FaixaHoras.objects.filter(
                    operator_id=operator_id,
                    contract=contract,
                ))
                # -----------------------------------------------------------

                for schedule in schedule_list:
                    driver = schedule.driver
                    operator = schedule.operator
                    turno = schedule.turno
                    business_date = schedule.date

                    total_processed += 1

                    # SEGURANÇA: Contabilidade Interceptadora
                    if getattr(driver, "active", True) is False:
                        continue

                    # Trava Interceptadora Geral: Bloqueio O(1) via Redis
                    try:
                        is_blocked = r.get(f"deny_list:driver:{driver.id}")
                        if is_blocked:
                            continue
                    except (
                        redis.exceptions.ConnectionError,
                        redis.exceptions.TimeoutError,
                    ):
                        # Fail-Closed
                        continue

                    with transaction.atomic():
                        # Padrão seguro contra race condition:
                        operator_wallet, _ = (
                            OperatorInternalWallet.objects.get_or_create(
                                operator=operator
                            )
                        )
                        operator_wallet = (
                            OperatorInternalWallet.objects.select_for_update().get(
                                pk=operator_wallet.pk
                            )
                        )

                        wallet, _ = Wallet.objects.get_or_create(
                            driver=driver, operator=operator
                        )
                        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

                        # Idempotência Robusta: Ignora FAILED, permite reprocessamento
                        if DailyCreditCalculation.objects.filter(
                            driver=driver,
                            store=store,
                            date=business_date,
                            status__in=[
                                DailyCreditCalculation.CreditStatus.CREDITED,
                                DailyCreditCalculation.CreditStatus.PENDING,
                            ],
                        ).exists():
                            continue

                        # O(1) in-memory order lookup
                        orders = orders_by_driver_date.get((driver.id, business_date), [])

                        production = 0
                        extras = 0
                        deliveries = 0

                        return_fee_bps = (
                            contract.returnFeeBps if contract.returnFeeBps else 5000
                        )

                        for order in orders:
                            if order.status == Order.OrderStatus.COMPLETED:
                                production += order.fareValueCents or 0
                                extras += order.storeAuthorizedBonusCents or 0
                                deliveries += 1
                            else:
                                fare_value = order.fareValueCents or 0
                                bonus_value = order.storeAuthorizedBonusCents or 0
                                production += (fare_value * return_fee_bps) // 10000
                                extras += (bonus_value * return_fee_bps) // 10000

                        weekday = business_date.weekday()
                        if weekday == 5:
                            dailyRateCents = contract.dailyRateSaturdayCents
                        elif weekday == 6:
                            dailyRateCents = contract.dailyRateSundayCents
                        else:
                            dailyRateCents = contract.dailyRateWeekdayCents

                        # O(1) in-memory advances lookup
                        advances = advances_by_driver_date.get((driver.id, business_date), 0)

                        mode = contract.compensationMode
                        netAmountCents = 0
                        guaranteedCents = 0

                        # ==========================================
                        # MOTOR FINANCEIRO: A Fórmula do Contrato
                        # ==========================================
                        if mode == "PRODUCAO":
                            excess = max(0, production - dailyRateCents)
                            netAmountCents = (
                                dailyRateCents
                                + excess
                                + (deliveries * contract.rideFeePerDeliveryCents)
                                - advances
                            )

                        elif mode == "GARANTIDA":
                            override = schedule.minGuaranteedOverrideCents
                            effective_guarantee = (
                                override if override is not None else dailyRateCents
                            )
                            guaranteedCents = max(
                                production + extras, effective_guarantee
                            )
                            netAmountCents = (
                                guaranteedCents
                                + (deliveries * contract.rideFeePerDeliveryCents)
                                - advances
                            )

                        elif mode == "GARANTIDA_HORAS":
                            t_start = turno.startTime
                            t_end = turno.endTime
                            minutes_worked = (t_end.hour * 60 + t_end.minute) - (
                                t_start.hour * 60 + t_start.minute
                            )
                            if minutes_worked < 0:
                                minutes_worked += 24 * 60
                            from decimal import Decimal

                            hours_worked = Decimal(minutes_worked) / Decimal(60)

                            # Encontrar faixa em memória O(N) onde N é número de faixas do contrato (muito pequeno)
                            faixa_price = 0
                            for faixa in faixas:
                                if faixa.hoursMin <= hours_worked < faixa.hoursMax:
                                    faixa_price = faixa.priceCents
                                    break

                            guaranteedCents = max(production + extras, faixa_price)
                            netAmountCents = (
                                guaranteedCents
                                + (deliveries * contract.rideFeePerDeliveryCents)
                                - advances
                            )

                        # ==========================================
                        # EFETIVAÇÃO CONTÁBIL E LEDGER
                        # ==========================================
                        DailyCreditCalculation.objects.create(
                            operator=operator,
                            driver=driver,
                            store=store,
                            date=business_date,
                            status=DailyCreditCalculation.CreditStatus.CREDITED,
                            productionValueCents=production,
                            extrasCents=extras,
                            dailyRateOrGuaranteedCents=guaranteedCents
                            or dailyRateCents,
                            advancesCents=advances,
                            netAmountCents=netAmountCents,
                        )

                        if netAmountCents > 0:
                            WalletTransaction.objects.create(
                                operator=operator,
                                source_operator_wallet=operator_wallet,
                                destination_driver_wallet=wallet,
                                amountCents=netAmountCents,
                                category=WalletTransaction.TransactionCategory.DAILY_SETTLEMENT,
                                taxCategory=WalletTransaction.TaxCategory.NON_TAXABLE_REIMBURSEMENT,
                            )
                        elif netAmountCents < 0:
                            WalletTransaction.objects.create(
                                operator=operator,
                                source_driver_wallet=wallet,
                                destination_operator_wallet=operator_wallet,
                                amountCents=abs(netAmountCents),
                                category=WalletTransaction.TransactionCategory.DAILY_SETTLEMENT,
                                taxCategory=WalletTransaction.TaxCategory.NON_TAXABLE_REIMBURSEMENT,
                            )

@shared_task
def close_weekly_invoice():
    """
    Roda aos domingos às 23:59.
    Consolida as faturas para as Lojas (Restaurantes).
    """
    from logistics.models import Store
    from finance.models import WeeklyStoreInvoice, WeeklyInvoiceLineItem

    today = timezone.localdate()
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)

    operators = Operator.objects.values_list("id", flat=True)
    total_invoices = 0

    for operator_id in operators:
        from config.core_models import tenant_context

        with tenant_context(operator_id):
            operator_obj = Operator.objects.get(pk=operator_id)
            stores = Store.objects.select_related("contract").all()
            for store in stores:
                if not hasattr(store, "contract"):
                    continue
                contract = store.contract

                with transaction.atomic():
                    if WeeklyStoreInvoice.objects.filter(
                        operator_id=operator_id,
                        store=store,
                        startDate=start_date,
                        endDate=end_date,
                    ).exists():
                        continue

                    daily_credits = list(DailyCreditCalculation.objects.filter(
                        operator_id=operator_id,
                        store=store,
                        date__gte=start_date,
                        date__lte=end_date,
                        status=DailyCreditCalculation.CreditStatus.CREDITED,
                    ))

                    if not daily_credits:
                        continue

                    # Cálculo na memória para economizar chamadas SQL (O(N) in-memory)
                    totalNetProducaoCents = sum(dc.productionValueCents for dc in daily_credits)
                    totalNetGarantidaCents = sum(dc.dailyRateOrGuaranteedCents for dc in daily_credits)

                    # CRIT-002: Escolher apenas um modo de compensação (não somar ambos)
                    if contract.compensationMode == Contract.CompensationMode.PRODUCAO:
                        base_total = totalNetProducaoCents
                    else:
                        base_total = totalNetGarantidaCents

                    supervisionFee = contract.supervisionFeePerWeekCents
                    adminFee = 0
                    if base_total <= contract.adminTaxThresholdCents:
                        adminFee = contract.adminTaxFixedAmountCents
                    else:
                        # LOW-002: Usar aritmética de inteiros (pontos-base) em vez de float
                        adminFee = (base_total * contract.adminTaxBps) // 10000

                    total = base_total + supervisionFee + adminFee

                    invoice = WeeklyStoreInvoice.objects.create(
                        operator=operator_obj,
                        store=store,
                        startDate=start_date,
                        endDate=end_date,
                        totalNetProducaoCents=totalNetProducaoCents,
                        totalNetGarantidaCents=totalNetGarantidaCents,
                        administrativeFeeCents=adminFee,
                        supervisionFeeCents=supervisionFee,
                        totalCents=total,
                        status=WeeklyStoreInvoice.InvoiceStatus.FINALIZED,
                    )
                    
                    line_items = []
                    for dc in daily_credits:
                        line_items.append(
                            WeeklyInvoiceLineItem(
                                operator=operator_obj,
                                invoice=invoice,
                                driver=dc.driver,
                                businessDate=dc.date,
                                description=f"Repasse referente a {dc.date}",
                                amountCents=dc.netAmountCents,
                            )
                        )
                    
                    # Inserção O(1) de inserts
                    if line_items:
                        WeeklyInvoiceLineItem.objects.bulk_create(line_items)

                    total_invoices += 1

    return f"Weekly invoices created: {total_invoices}"


@shared_task
def run_hourly_cutoff_billing():
    """
    Executa a cada hora cheia. Varre apenas as lojas cujo cutoffHour
    seja igual a hora atual.
    """
    if os.environ.get("ENABLE_HOURLY_BILLING", "True") != "True":
        return "Hourly billing disabled."

    current_hour = timezone.localtime().hour
    compute_daily_credit.delay(target_cutoff_hour=current_hour)  # type: ignore
    return f"Hourly billing dispatched for cutoff = {current_hour}h."


@shared_task
def run_global_cutoff_billing():
    """
    Executa maciçamente para todos os contratos, independentemente do cutoffHour.
    Geralmente agendada para as 04:00 AM (fallback).
    """
    if os.environ.get("ENABLE_GLOBAL_BILLING", "True") != "True":
        return "Global billing disabled."

    compute_daily_credit.delay(target_cutoff_hour=None)  # type: ignore
    return "Global billing dispatched for ALL stores."


@shared_task
def generate_pending_invoices_pdfs():
    """
    Roda para as faturas de Lojas que foram finalizadas (FINALIZED)
    mas ainda não possuem o PDF gerado (Simulado como gerado se ok).
    """
    from finance.models import WeeklyStoreInvoice
    from finance.pdf_generator import InvoicePDFBuilder
    from config.supabase_client import supabase

    invoices = WeeklyStoreInvoice.objects.filter(
        status=WeeklyStoreInvoice.InvoiceStatus.FINALIZED, pdfUrl__isnull=True
    )

    generated = 0
    for invoice in invoices:
        builder = InvoicePDFBuilder(invoice)
        pdf_bytes = builder.build()

        if supabase:
            file_path = f"invoices/{invoice.operator.id}/{invoice.id}.pdf"
            supabase.storage.from_("invoices").upload(file_path, pdf_bytes)
            invoice.pdfUrl = file_path
            invoice.save(update_fields=["pdfUrl"])

        generated += 1

    return f"PDF Invoices Generated: {generated}"


@shared_task
def process_withdrawal_remessas():
    """
    Agrupa os pedidos de saque PENDING e gera o CNAB 240
    para envio ao Banco de cada Operador Logístico.
    Resiliente a falhas de rede do Supabase.
    """
    from finance.models import WithdrawalRequest
    from accounts.models import Operator
    from finance.cnab_generator import CNAB240RemessaBuilder
    from config.supabase_client import supabase
    from django.db import transaction
    from datetime import datetime

    operators = Operator.objects.all()
    files_generated = 0

    for operator in operators:
        if not operator.cnpj:
            from logging import getLogger
            getLogger(__name__).error(
                f"Operador {operator.name} nao possui CNPJ configurado."
            )
            continue
            
        locked_withdrawals = []
        cnab_string = None
        
        # 1. TRANSAÇÃO DE BANCO: Apenas bloqueio e atualização de status
        with transaction.atomic():
            withdrawals = list(
                WithdrawalRequest.objects.filter(
                    operator=operator, status=WithdrawalRequest.WithdrawalStatus.PENDING
                ).select_for_update()
            )

            if not withdrawals:
                continue
                
            builder = CNAB240RemessaBuilder(
                operator_cnpj=operator.cnpj, operator_name=operator.name
            )
            cnab_string = builder.build(withdrawals)

            # Marca como processando na base
            for w in withdrawals:
                w.status = WithdrawalRequest.WithdrawalStatus.PROCESSING
                w.save(update_fields=["status"])
                locked_withdrawals.append(w)
                
        # Se não processou nada, vai pro próximo
        if not locked_withdrawals or not cnab_string:
            continue

        # 2. I/O DE REDE (SUPABASE): Fora da transação
        upload_success = False
        try:
            if supabase:
                file_path = f"remessas/{operator.id}/{datetime.now().strftime('%Y%m%d%H%M%S')}.rem"
                supabase.storage.from_("financial").upload(
                    file_path, cnab_string.encode("utf-8")
                )
                upload_success = True
            else:
                upload_success = True # Modo sem supabase
        except Exception as e:
            from logging import getLogger
            getLogger(__name__).error(f"Erro ao enviar remessa Supabase (Operator {operator.id}): {e}")
            
            # Rollback dos status se a rede caiu (Compensating Transaction)
            with transaction.atomic():
                revert_withdrawals = WithdrawalRequest.objects.filter(
                    id__in=[w.id for w in locked_withdrawals]
                ).select_for_update()
                for w in revert_withdrawals:
                    w.status = WithdrawalRequest.WithdrawalStatus.PENDING
                    w.save(update_fields=["status"])

        if upload_success:
            files_generated += 1

    return f"CNAB 240 files generated: {files_generated}"


@shared_task
def process_return_file_ret(file_path: str):
    """
    Processa o arquivo .RET de retorno do banco.
    Resolve os saques no estado PROCESSING, movendo para COMPLETED ou FAILED.
    """
    from finance.models import WithdrawalRequest
    from django.db import transaction

    # Simulação de leitura de um arquivo (num cenário real abriríamos do S3)
    # Lemos linha por linha.
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            if len(line) >= 240 and line[7] == "3" and line[13] == "A":
                # Segmento A
                # Em nosso gerador: 076-095 (índices 75 a 94) é o "Seu Numero" (Withdrawal ID)
                withdrawal_id_str = line[75:95].strip()

                if withdrawal_id_str:
                    with transaction.atomic():
                        # Bloqueio pessimista do Saque para evitar condições de corrida
                        try:
                            withdrawal = WithdrawalRequest.objects.select_for_update().get(
                                id=withdrawal_id_str,
                                status=WithdrawalRequest.WithdrawalStatus.PROCESSING,
                            )
                            # Simulação: se tudo OK (código de retorno 00), COMPLETED.
                            # Para simplificar, assumiremos sucesso para todos encontrados.
                            withdrawal.status = (
                                WithdrawalRequest.WithdrawalStatus.COMPLETED
                            )
                            withdrawal.save(update_fields=["status"])
                        except WithdrawalRequest.DoesNotExist:
                            continue
    except Exception as e:
        import logging

        logging.error(f"Failed to process return file {file_path}: {e}")
