
""" Módulo Financeiro e de Repasse.

Gerencia o ciclo de vida contábil de ponta a ponta:
- Motor de cálculo de faturas semanais para Clientes (Lojas).
- Lógica de repasse para Motoristas (Produção vs. Garantida).
- Arquitetura de "Ledger Wallet" com dupla-contrapartida (Double-Entry Bookkeeping).

Como todas as transações importam em dinheiro no mundo real, todos os modelos
preservam o paradigma `managed = False` para usar as garantias ACID do PostgreSQL.
"""

from django.db import models
from config.core_models import TenantModel, TimeStampedTenantModel
from accounts.models import Operator, StaffMember
from logistics.models import Store, Driver, Order, ClientPortalUser

class Contract(TenantModel):
    """
    Contrato Financeiro da Loja.
    
    Define como a Loja (Store) remunera o Operador e os Motoristas.
    A modalidade de compensação dita as regras do Worker financeiro que 
    fechará as contas de madrugada.
    """
    class CompensationMode(models.TextChoices):
        PRODUCAO = 'PRODUCAO', 'Producao'
        GARANTIDA = 'GARANTIDA', 'Garantida'
        GARANTIDA_HORAS = 'GARANTIDA_HORAS', 'Garantida Horas'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    store = models.OneToOneField(Store, on_delete=models.CASCADE, db_column='store_id')
    compensationMode = models.CharField(max_length=20, choices=CompensationMode.choices, default=CompensationMode.GARANTIDA, db_column='compensationMode')
    rideFeePerDeliveryCents = models.IntegerField(db_column='rideFeePerDeliveryCents', help_text="Taxa fixa de corrida repassada.")
    minimumRidesFeeFloorCents = models.IntegerField(db_column='minimumRidesFeeFloorCents')
    minimumFloorBps = models.IntegerField(db_column='minimumFloorBps')
    adminTaxThresholdCents = models.IntegerField(db_column='adminTaxThresholdCents')
    adminTaxFixedAmountCents = models.IntegerField(db_column='adminTaxFixedAmountCents')
    adminTaxBps = models.IntegerField(db_column='adminTaxBps')
    supervisionFeePerWeekCents = models.IntegerField(default=0, db_column='supervisionFeePerWeekCents')
    dailyRateWeekdayCents = models.IntegerField(default=0, db_column='dailyRateWeekdayCents')
    dailyRateSaturdayCents = models.IntegerField(default=0, db_column='dailyRateSaturdayCents')
    dailyRateSundayCents = models.IntegerField(default=0, db_column='dailyRateSundayCents')
    dailyRateHolidayCents = models.IntegerField(default=0, db_column='dailyRateHolidayCents')
    kmExcedenteValorCents = models.IntegerField(default=0, db_column='kmExcedenteValorCents')
    allowAutomaticGrouping = models.BooleanField(default=True, db_column='allowAutomaticGrouping')
    cloudOverflowAllowed = models.BooleanField(default=False, db_column='cloudOverflowAllowed')
    maxStopsPerManifest = models.IntegerField(default=3, db_column='maxStopsPerManifest')
    maxDetourPercent = models.IntegerField(default=20, db_column='maxDetourPercent')
    cutoffHour = models.IntegerField(default=2, db_column='cutoffHour', help_text="Hora oficial de fechamento do 'business date'.")
    cutoffMinute = models.IntegerField(default=0, db_column='cutoffMinute')
    returnFeeBps = models.IntegerField(default=5000, db_column='returnFeeBps')

    class Meta:
        db_table = 'Contract'
        managed = False
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"


class KmFaixa(TenantModel):
    """
    Tabela de Precificação de Faixa de Quilometragem.
    Aplicada no momento em que a rota do manifesto é fechada, determinando
    o preço dinâmico da entrega baseado na distância.
    """
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, db_column='contract_id')
    kmStart = models.IntegerField(db_column='kmStart')
    kmEnd = models.IntegerField(db_column='kmEnd')
    priceCents = models.IntegerField(db_column='priceCents')

    class Meta:
        db_table = 'KmFaixa'
        managed = False


class FaixaHoras(TenantModel):
    """
    Tabela de Precificação por Janela de Tempo.
    Usada para contratos que precificam as diárias baseados no volume de horas servidas.
    """
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, db_column='contract_id')
    hoursMin = models.DecimalField(max_digits=4, decimal_places=2, db_column='hoursMin')
    hoursMax = models.DecimalField(max_digits=4, decimal_places=2, db_column='hoursMax')
    priceCents = models.IntegerField(db_column='priceCents')

    class Meta:
        db_table = 'FaixaHoras'
        managed = False


class Wallet(TenantModel):
    """
    Carteira Corrente (Ledger) do Motorista.
    Consolida o saldo a receber. O campo balanceCents nunca é atualizado via UPDATE + (A+B) 
    direto na aplicação, e sim por Triggers no PostgreSQL baseados nas transações de origem 
    e destino, blindando contra corrida de dados (Race Conditions).
    """
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    driver = models.OneToOneField(Driver, on_delete=models.CASCADE, db_column='driver_id')
    balanceCents = models.BigIntegerField(default=0, db_column='balanceCents', help_text="Saldo computado.")
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'Wallet'
        managed = False


class OperatorInternalWallet(TenantModel):
    """
    Carteira Corrente do Operador (Contrapartida).
    Onde o dinheiro sai para pagar motoristas (Passivo) ou onde o dinheiro entra vindo das 
    faturas das Lojas (Ativo).
    """
    operator = models.OneToOneField(Operator, on_delete=models.CASCADE, db_column='operator_id')
    balanceCents = models.BigIntegerField(default=0, db_column='balanceCents')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        db_table = 'OperatorInternalWallet'
        managed = False


class WalletTransaction(TimeStampedTenantModel):
    """
    Transação Imutável de Carteira (Ledger Entry).
    
    Toda movimentação financeira DEVE gerar um registro nesta tabela contendo 
    uma carteira de Origem e uma carteira de Destino. O banco impede via Constraint
    a criação de uma transação desbalanceada, sendo o núcleo anti-fraude do financeiro.
    """
    class TransactionCategory(models.TextChoices):
        DAILY_SETTLEMENT = 'DAILY_SETTLEMENT', 'Daily Settlement'
        ADVANCE = 'ADVANCE', 'Advance'
        PAYOUT = 'PAYOUT', 'Payout'
        ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
        BONUS = 'BONUS', 'Bonus'
        PENALTY = 'PENALTY', 'Penalty'
        RETURN_RIDE = 'RETURN_RIDE', 'Return Ride'
        REFUND = 'REFUND', 'Refund'

    class TaxCategory(models.TextChoices):
        TAXABLE_INCOME = 'TAXABLE_INCOME', 'Taxable Income'
        NON_TAXABLE_REIMBURSEMENT = 'NON_TAXABLE_REIMBURSEMENT', 'Non Taxable Reimbursement'
        DEDUCTION = 'DEDUCTION', 'Deduction'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    source_driver_wallet = models.ForeignKey(Wallet, null=True, blank=True, on_delete=models.CASCADE, related_name='outgoing_transactions', db_column='source_driver_wallet_id')
    source_operator_wallet = models.ForeignKey(OperatorInternalWallet, null=True, blank=True, on_delete=models.CASCADE, related_name='outgoing_transactions', db_column='source_operator_wallet_id')
    destination_driver_wallet = models.ForeignKey(Wallet, null=True, blank=True, on_delete=models.CASCADE, related_name='incoming_transactions', db_column='destination_driver_wallet_id')
    destination_operator_wallet = models.ForeignKey(OperatorInternalWallet, null=True, blank=True, on_delete=models.CASCADE, related_name='incoming_transactions', db_column='destination_operator_wallet_id')
    amountCents = models.BigIntegerField(db_column='amountCents')
    category = models.CharField(max_length=50, choices=TransactionCategory.choices)
    taxCategory = models.CharField(max_length=50, choices=TaxCategory.choices, db_column='taxCategory')

    class Meta:
        db_table = 'WalletTransaction'
        managed = False


class ManualEntry(TimeStampedTenantModel):
    """
    Lançamento Financeiro Manual.
    Usado por despachantes ou clientes para adicionar bônus a corridas ou penalidades,
    sempre com um fluxo de Aprovação Pendente por trás (Four-Eyes Principle).
    """
    class EntryStatus(models.TextChoices):
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column='driver_id')
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.SET_NULL, db_column='store_id')
    created_by_staff = models.ForeignKey(StaffMember, null=True, blank=True, on_delete=models.RESTRICT, related_name='created_manual_entries', db_column='created_by_staff_id')
    created_by_client = models.ForeignKey(ClientPortalUser, null=True, blank=True, on_delete=models.RESTRICT, related_name='created_manual_entries', db_column='created_by_client_id')
    amountCents = models.BigIntegerField(db_column='amountCents')
    description = models.TextField()
    visibleToStore = models.BooleanField(default=True, db_column='visibleToStore')
    taxCategory = models.CharField(max_length=50, choices=WalletTransaction.TaxCategory.choices, db_column='taxCategory')
    status = models.CharField(max_length=30, choices=EntryStatus.choices, default=EntryStatus.PENDING_APPROVAL)
    rejectReason = models.TextField(null=True, blank=True, db_column='rejectReason')
    approvedBy = models.ForeignKey(StaffMember, null=True, blank=True, on_delete=models.RESTRICT, related_name='approved_manual_entries', db_column='approvedById')

    class Meta:
        db_table = 'ManualEntry'
        managed = False


class DailyCreditCalculation(TimeStampedTenantModel):
    """
    Consolidação de Crédito Diário (Fechamento do Dia).
    
    Workers do Celery processam essa tabela toda madrugada (após o cutoff) para 
    apurar quanto um motorista rodou, comparar com o mínimo garantido de contrato
    da Loja e consolidar o saldo final que será enviado para a Wallet Ledger.
    """
    class CreditStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CREDITED = 'CREDITED', 'Credited'
        SKIPPED = 'SKIPPED', 'Skipped'
        FAILED = 'FAILED', 'Failed'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column='driver_id')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column='store_id')
    date = models.DateField(help_text="O Business Date computado para a apuração.")
    status = models.CharField(max_length=20, choices=CreditStatus.choices, default=CreditStatus.PENDING)
    productionValueCents = models.BigIntegerField(default=0, db_column='productionValueCents')
    extrasCents = models.BigIntegerField(default=0, db_column='extrasCents')
    dailyRateOrGuaranteedCents = models.BigIntegerField(default=0, db_column='dailyRateOrGuaranteedCents')
    advancesCents = models.BigIntegerField(default=0, db_column='advancesCents')
    netAmountCents = models.BigIntegerField(default=0, db_column='netAmountCents')
    failReason = models.TextField(null=True, blank=True, db_column='failReason')

    class Meta:
        db_table = 'DailyCreditCalculation'
        managed = False


class WeeklyStoreInvoice(TimeStampedTenantModel):
    """
    Fatura de Cobrança Semanal da Loja.
    Agrupa todo o saldo apurado durante os sete dias úteis, somado aos fees de gestão, 
    gerando o boleto/pix a ser liquidado pelo parceiro.
    """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        DISPUTED = 'DISPUTED', 'Disputed'
        FINALIZED = 'FINALIZED', 'Finalized'
        LOCKED = 'LOCKED', 'Locked'
        PAID = 'PAID', 'Paid'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column='store_id')
    startDate = models.DateField(db_column='startDate')
    endDate = models.DateField(db_column='endDate')
    totalNetProducaoCents = models.BigIntegerField(default=0, db_column='totalNetProducaoCents')
    totalNetGarantidaCents = models.BigIntegerField(default=0, db_column='totalNetGarantidaCents')
    administrativeFeeCents = models.BigIntegerField(default=0, db_column='administrativeFeeCents')
    supervisionFeeCents = models.BigIntegerField(default=0, db_column='supervisionFeeCents')
    pendingDebitCarriedCents = models.BigIntegerField(default=0, db_column='pendingDebitCarriedCents')
    totalCents = models.BigIntegerField(default=0, db_column='totalCents', help_text="Total geral da fatura que será enviado ao Gateway.")
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    paymentGatewayId = models.CharField(max_length=255, null=True, blank=True, db_column='paymentGatewayId', help_text="ID do Gateway de Pagamento (Asaas/Stripe).")
    pixCopyPaste = models.TextField(null=True, blank=True, db_column='pixCopyPaste')
    barcode = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'WeeklyStoreInvoice'
        managed = False


class WeeklyInvoiceLineItem(TimeStampedTenantModel):
    """
    Item Detalhado da Fatura.
    Para gerar o Breakdown discriminando os custos corrida a corrida, ou turno a turno,
    eliminando dúvidas da loja.
    """
    class ItemStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        DISPUTED = 'DISPUTED', 'Disputed'
        WAIVED = 'WAIVED', 'Waived'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    invoice = models.ForeignKey(WeeklyStoreInvoice, on_delete=models.CASCADE, db_column='invoice_id')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, db_column='driver_id')
    businessDate = models.DateField(null=True, blank=True, db_column='businessDate')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, db_column='order_id')
    manualEntry = models.ForeignKey(ManualEntry, on_delete=models.SET_NULL, null=True, blank=True, db_column='manualEntryId')
    description = models.TextField()
    amountCents = models.BigIntegerField(db_column='amountCents')
    status = models.CharField(max_length=20, choices=ItemStatus.choices, default=ItemStatus.ACTIVE)
    disputeReason = models.TextField(null=True, blank=True, db_column='disputeReason')

    class Meta:
        db_table = 'WeeklyInvoiceLineItem'
        managed = False


class WithdrawalRequest(TimeStampedTenantModel):
    """
    Pedido de Saque.
    Comando assíncrono acionado pelo aplicativo do Motoboy para disparar
    PIX em lote esvaziando a carteira corrente.
    """
    class WithdrawalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column='driver_id')
    amountCents = models.BigIntegerField(db_column='amountCents')
    status = models.CharField(max_length=20, choices=WithdrawalStatus.choices, default=WithdrawalStatus.PENDING)
    pixKey = models.CharField(max_length=255, db_column='pixKey')

    class Meta:
        db_table = 'WithdrawalRequest'
        managed = False


class DriverExpense(TimeStampedTenantModel):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column='driver_id')
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL, db_column='order_id')
    type = models.CharField(max_length=20)
    amountCents = models.BigIntegerField(db_column='amountCents')
    description = models.TextField()
    status = models.CharField(max_length=20, default='SUBMITTED')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'DriverExpense'
        managed = False


class DriverExpenseReceipt(TimeStampedTenantModel):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, db_column='operator_id')
    expense = models.ForeignKey(DriverExpense, on_delete=models.CASCADE, db_column='expense_id')
    fileUrl = models.TextField(db_column='fileUrl')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'DriverExpenseReceipt'
        managed = False
