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

                # Cálculo determinístico: Quando foi a ÚLTIMA vez que o relógio marcou a hora do cutoff?
                # Se agora são 02:05 e o cutoff é 02:00, o último cutoff foi hoje às 02:00. O dia fiscal fechado é "ontem".
                # Se agora são 23:05 e o cutoff é 23:00, o último cutoff foi hoje às 23:00. O dia fiscal fechado é "hoje".
                # Para evitar falhas por atrasos de filas, recuamos 1 hora do cutoff nominal para "travar" o dia correto.
                current_time = timezone.localtime()
                # Limite máximo de data fiscal a ser processada hoje (Cutoff)
                business_date_limit = (
                    current_time - timedelta(hours=contract.cutoffHour, minutes=30)
                ).date()

                from django.db.models import Exists, OuterRef

                # Catch-up Automático: Puxa QUALQUER turno do passado que o Celery
                # tenha deixado de processar (Downtime/Crashes) até o limite fiscal atual.
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

                for schedule in schedules:
                    driver = schedule.driver
                    operator = schedule.operator
                    turno = schedule.turno
                    business_date = schedule.date

                    total_processed += 1

                    # SEGURANÇA: Contabilidade Interceptadora
                    # Não computar faturas diárias e repasses para motoristas suspensos
                    if getattr(driver, "active", True) is False:
                        continue

                    # Trava Interceptadora Geral: Bloqueio O(1) via Redis
                    try:
                        is_blocked = r.get(f"deny_list:driver:{driver.id}")
                        if is_blocked:
                            # Se banido, a transação aborta como FAILED mid-flight para este driver
                            continue
                    except (
                        redis.exceptions.ConnectionError,
                        redis.exceptions.TimeoutError,
                    ):
                        # A indisponibilidade de sistema temporária é infinitamente superior ao risco contábil cego.
                        # Fail-Closed
                        continue

                    with transaction.atomic():
                        # Padrão seguro contra race condition:
                        # 1. get_or_create SEM lock (cria se não existir, IntegrityError é handled pelo Django)
                        # 2. Depois, select_for_update para travar a row existente/criada
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

                        # Buscar produção (Orders) filtrando os que geram repasse
                        orders = Order.objects.filter(
                            operator=operator,
                            driver=driver,
                            store=store,
                            businessDate=business_date,
                            status__in=[
                                Order.OrderStatus.COMPLETED,
                                Order.OrderStatus.RETURNED,
                                Order.OrderStatus.CANCELED_IN_TRANSIT,
                            ],
                        )

                        production = 0
                        extras = 0
                        deliveries = 0

                        # Calcular aplicando proporção de taxa de devolução (returnFeeBps)
                        # LOW-002: Usar aritmética de inteiros (não floats)
                        return_fee_bps = (
                            contract.returnFeeBps if contract.returnFeeBps else 5000
                        )  # 50% = 5000 bps

                        for order in orders:
                            if order.status == Order.OrderStatus.COMPLETED:
                                production += order.fareValueCents or 0
                                extras += order.storeAuthorizedBonusCents or 0
                                deliveries += 1
                            else:
                                # RETURNED ou CANCELED_IN_TRANSIT: Motoboy foi e voltou/cancelado. Paga a fração (ex: 50%)
                                fare_value = order.fareValueCents or 0
                                bonus_value = order.storeAuthorizedBonusCents or 0
                                production += (fare_value * return_fee_bps) // 10000
                                extras += (bonus_value * return_fee_bps) // 10000
                                # Não conta como 'delivery' pleno para bônus de número de entregas

                        # Determinar a diária base do contrato (simplificado para dia da semana vs Sábado/Domingo)
                        weekday = business_date.weekday()
                        if weekday == 5:  # Sábado
                            dailyRateCents = contract.dailyRateSaturdayCents
                        elif weekday == 6:  # Domingo
                            dailyRateCents = contract.dailyRateSundayCents
                        else:  # Seg-Sex
                            dailyRateCents = contract.dailyRateWeekdayCents

                        # Consultar adiantamentos/vales aprovados para este motorista neste dia
                        # Inclui lançamentos privados (store=NULL) conforme schema.sql
                        from finance.models import ManualEntry
                        from django.db.models import Q

                        advances = (
                            ManualEntry.objects.filter(
                                Q(store=store) | Q(store__isnull=True),
                                operator=operator,
                                driver=driver,
                                status=ManualEntry.EntryStatus.APPROVED,
                                taxCategory=WalletTransaction.TaxCategory.DEDUCTION,
                                createdAt__date=business_date,
                            ).aggregate(total=Sum("amountCents"))["total"]
                            or 0
                        )

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
                            # Permite override manual na escala específica
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
                            # Cálculo de horas decimais do Turno (INTERVALO SEMI-ABERTO)
                            t_start = turno.startTime
                            t_end = turno.endTime
                            minutes_worked = (t_end.hour * 60 + t_end.minute) - (
                                t_start.hour * 60 + t_start.minute
                            )
                            if minutes_worked < 0:
                                minutes_worked += 24 * 60
                            from decimal import Decimal

                            hours_worked = Decimal(minutes_worked) / Decimal(60)

                            faixa = FaixaHoras.objects.filter(
                                operator=operator,
                                contract=contract,
                                hoursMin__lte=hours_worked,
                                hoursMax__gt=hours_worked,  # Estrito: Menor que hoursMax (Semi-aberto)
                            ).first()

                            faixa_price = faixa.priceCents if faixa else 0
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
                            # O saldo nunca é atualizado diretamente pelo worker.
                            # Apenas registramos a Transação Imutável, e o PostGIS/PostgreSQL
                            # através de Triggers recalcula o Ledger consolidado.
                            WalletTransaction.objects.create(
                                operator=operator,
                                source_operator_wallet=operator_wallet,
                                destination_driver_wallet=wallet,
                                amountCents=netAmountCents,
                                category=WalletTransaction.TransactionCategory.DAILY_SETTLEMENT,
                                taxCategory=WalletTransaction.TaxCategory.NON_TAXABLE_REIMBURSEMENT,
                            )
                        elif netAmountCents < 0:
                            # Partidas Dobradas: O dinheiro não surge nem desaparece.
                            # Motorista pegou mais adiantamentos que a produção. Débito contra o Motorista!
                            WalletTransaction.objects.create(
                                operator=operator,
                                source_driver_wallet=wallet,  # Wallet do motorista (Origem: de onde sai o dinheiro)
                                destination_operator_wallet=operator_wallet,  # OperatorInternalWallet (Destino: para onde vai)
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

                    daily_credits = DailyCreditCalculation.objects.filter(
                        operator_id=operator_id,
                        store=store,
                        date__gte=start_date,
                        date__lte=end_date,
                        status=DailyCreditCalculation.CreditStatus.CREDITED,
                    )

                    if not daily_credits.exists():
                        continue

                    totalNetProducaoCents = (
                        daily_credits.aggregate(t=Sum("productionValueCents"))["t"] or 0
                    )
                    totalNetGarantidaCents = (
                        daily_credits.aggregate(t=Sum("dailyRateOrGuaranteedCents"))[
                            "t"
                        ]
                        or 0
                    )

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
                    operator = Operator.objects.get(pk=operator_id)

                    invoice = WeeklyStoreInvoice.objects.create(
                        operator=operator,
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

                    for dc in daily_credits:
                        WeeklyInvoiceLineItem.objects.create(
                            operator=operator,
                            invoice=invoice,
                            driver=dc.driver,
                            businessDate=dc.date,
                            description=f"Repasse referente a {dc.date}",
                            amountCents=dc.netAmountCents,
                        )

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
        with transaction.atomic():
            withdrawals = list(
                WithdrawalRequest.objects.filter(
                    operator=operator, status=WithdrawalRequest.WithdrawalStatus.PENDING
                ).select_for_update()
            )

            if not withdrawals:
                continue

            if not operator.cnpj:
                from logging import getLogger

                getLogger(__name__).error(
                    f"Operador {operator.name} nao possui CNPJ configurado."
                )
                continue

            builder = CNAB240RemessaBuilder(
                operator_cnpj=operator.cnpj, operator_name=operator.name
            )
            cnab_string = builder.build(withdrawals)

            if supabase:
                file_path = f"remessas/{operator.id}/{datetime.now().strftime('%Y%m%d%H%M%S')}.rem"
                # Usando str.encode para enviar os bytes do arquivo de texto
                supabase.storage.from_("financial").upload(
                    file_path, cnab_string.encode("utf-8")
                )

            # Marca como processando
            for w in withdrawals:
                w.status = WithdrawalRequest.WithdrawalStatus.PROCESSING
                w.save(update_fields=["status"])

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
