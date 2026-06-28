import os
import re

file_path = "finance/tasks.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace close_weekly_invoice
start_weekly = content.find("@shared_task\ndef close_weekly_invoice():")
end_weekly = content.find("@shared_task\ndef run_hourly_cutoff_billing():")

new_weekly = """@shared_task
def close_weekly_invoice():
    \"\"\"
    Roda aos domingos às 23:59.
    Consolida as faturas para as Lojas (Restaurantes).
    \"\"\"
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


"""
content = content[:start_weekly] + new_weekly + content[end_weekly:]


# Replace process_withdrawal_remessas
start_remessa = content.find("@shared_task\ndef process_withdrawal_remessas():")
end_remessa = content.find("@shared_task\ndef process_return_file_ret(file_path: str):")

new_remessa = """@shared_task
def process_withdrawal_remessas():
    \"\"\"
    Agrupa os pedidos de saque PENDING e gera o CNAB 240
    para envio ao Banco de cada Operador Logístico.
    Resiliente a falhas de rede do Supabase.
    \"\"\"
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


"""
content = content[:start_remessa] + new_remessa + content[end_remessa:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("File rewritten successfully")
