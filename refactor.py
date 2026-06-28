import os
import re

file_path = "finance/tasks.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_idx = content.find("def compute_daily_credit(target_cutoff_hour=None):")
end_idx = content.find("@shared_task\ndef close_weekly_invoice():")

if start_idx == -1 or end_idx == -1:
    print("Could not find boundaries")
    exit(1)

new_func = """def compute_daily_credit(target_cutoff_hour=None):
    \"\"\"
    Roda dinamicamente calculando a competência (business_date) baseada
    no cutoffHour do contrato da loja, eliminando o Bug da Meia-Noite.
    \"\"\"
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

"""

new_content = content[:start_idx] + new_func + content[end_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("File rewritten successfully")
