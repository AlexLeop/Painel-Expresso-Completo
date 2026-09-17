"""Módulo Financeiro e de Repasse.

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
        PRODUCAO = "PRODUCAO", "Producao"
        GARANTIDA = "GARANTIDA", "Garantida"
        GARANTIDA_HORAS = "GARANTIDA_HORAS", "Garantida Horas"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.OneToOneField(Store, on_delete=models.CASCADE, db_column="store_id")
    compensationMode = models.CharField(
        max_length=20,
        choices=CompensationMode.choices,
        default=CompensationMode.GARANTIDA,
        db_column="compensationMode",
    )
    rideFeePerDeliveryCents = models.IntegerField(
        db_column="rideFeePerDeliveryCents", help_text="Taxa fixa de corrida repassada."
    )
    minimumRidesFeeFloorCents = models.IntegerField(
        db_column="minimumRidesFeeFloorCents"
    )
    minimumFloorBps = models.IntegerField(db_column="minimumFloorBps")
    adminTaxThresholdCents = models.IntegerField(db_column="adminTaxThresholdCents")
    adminTaxFixedAmountCents = models.IntegerField(db_column="adminTaxFixedAmountCents")
    adminTaxBps = models.IntegerField(db_column="adminTaxBps")
    supervisionFeePerWeekCents = models.IntegerField(
        default=0, db_column="supervisionFeePerWeekCents"
    )
    dailyRateWeekdayCents = models.IntegerField(
        default=0, db_column="dailyRateWeekdayCents"
    )
    dailyRateSaturdayCents = models.IntegerField(
        default=0, db_column="dailyRateSaturdayCents"
    )
    dailyRateSundayCents = models.IntegerField(
        default=0, db_column="dailyRateSundayCents"
    )
    dailyRateHolidayCents = models.IntegerField(
        default=0, db_column="dailyRateHolidayCents"
    )
    kmExcedenteValorCents = models.IntegerField(
        default=0, db_column="kmExcedenteValorCents"
    )
    allowAutomaticGrouping = models.BooleanField(
        default=True, db_column="allowAutomaticGrouping"
    )
    cloudOverflowAllowed = models.BooleanField(
        default=False, db_column="cloudOverflowAllowed"
    )
    maxStopsPerManifest = models.IntegerField(
        default=3, db_column="maxStopsPerManifest"
    )
    maxDetourPercent = models.IntegerField(default=20, db_column="maxDetourPercent")
    cutoffHour = models.IntegerField(
        default=2,
        db_column="cutoffHour",
        help_text="Hora oficial de fechamento do 'business date'.",
    )
    cutoffMinute = models.IntegerField(default=0, db_column="cutoffMinute")
    returnFeeBps = models.IntegerField(default=5000, db_column="returnFeeBps")
    overridePayoutPolicy = models.BooleanField(
        default=False,
        db_column="overridePayoutPolicy",
        help_text="Se True, aplica as regras customizadas de saque da loja ao invés da política global do operador.",
    )
    customPayoutMode = models.CharField(
        max_length=30, null=True, blank=True, db_column="customPayoutMode"
    )
    customAutoThresholdCents = models.BigIntegerField(
        null=True, blank=True, db_column="customAutoThresholdCents"
    )
    customFeeMode = models.CharField(
        max_length=30, null=True, blank=True, db_column="customFeeMode"
    )
    customFeeCents = models.BigIntegerField(
        null=True, blank=True, db_column="customFeeCents"
    )

    class Meta:
        db_table = "Contract"
        managed = False
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"


class KmFaixa(TenantModel):
    """
    Tabela de Precificação de Faixa de Quilometragem.
    Aplicada no momento em que a rota do manifesto é fechada, determinando
    o preço dinâmico da entrega baseado na distância.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, db_column="contract_id"
    )
    kmStart = models.IntegerField(db_column="kmStart")
    kmEnd = models.IntegerField(db_column="kmEnd")
    priceCents = models.IntegerField(db_column="priceCents")

    class Meta:
        db_table = "KmFaixa"
        managed = False


class FaixaHoras(TenantModel):
    """
    Tabela de Precificação por Janela de Tempo.
    Usada para contratos que precificam as diárias baseados no volume de horas servidas.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, db_column="contract_id"
    )
    hoursMin = models.DecimalField(max_digits=4, decimal_places=2, db_column="hoursMin")
    hoursMax = models.DecimalField(max_digits=4, decimal_places=2, db_column="hoursMax")
    priceCents = models.IntegerField(db_column="priceCents")

    class Meta:
        db_table = "FaixaHoras"
        managed = False


class Wallet(TenantModel):
    """
    Carteira Corrente (Ledger) do Motorista.
    Consolida o saldo a receber. O campo balanceCents nunca é atualizado via UPDATE + (A+B)
    direto na aplicação, e sim por Triggers no PostgreSQL baseados nas transações de origem
    e destino, blindando contra corrida de dados (Race Conditions).
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.OneToOneField(
        Driver, on_delete=models.CASCADE, db_column="driver_id"
    )
    balanceCents = models.BigIntegerField(
        default=0, db_column="balanceCents", help_text="Saldo computado."
    )
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "Wallet"
        managed = False


class OperatorInternalWallet(TenantModel):
    """
    Carteira Corrente do Operador (Contrapartida).
    Onde o dinheiro sai para pagar motoristas (Passivo) ou onde o dinheiro entra vindo das
    faturas das Lojas (Ativo).
    """

    operator = models.OneToOneField(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    balanceCents = models.BigIntegerField(default=0, db_column="balanceCents")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        db_table = "OperatorInternalWallet"
        managed = False


class WalletTransaction(TimeStampedTenantModel):
    """
    Transação Imutável de Carteira (Ledger Entry).

    Toda movimentação financeira DEVE gerar um registro nesta tabela contendo
    uma carteira de Origem e uma carteira de Destino. O banco impede via Constraint
    a criação de uma transação desbalanceada, sendo o núcleo anti-fraude do financeiro.
    """

    class TransactionCategory(models.TextChoices):
        DAILY_SETTLEMENT = "DAILY_SETTLEMENT", "Daily Settlement"
        ADVANCE = "ADVANCE", "Advance"
        PAYOUT = "PAYOUT", "Payout"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        BONUS = "BONUS", "Bonus"
        PENALTY = "PENALTY", "Penalty"
        RETURN_RIDE = "RETURN_RIDE", "Return Ride"
        REFUND = "REFUND", "Refund"

    class TaxCategory(models.TextChoices):
        TAXABLE_INCOME = "TAXABLE_INCOME", "Taxable Income"
        NON_TAXABLE_REIMBURSEMENT = (
            "NON_TAXABLE_REIMBURSEMENT",
            "Non Taxable Reimbursement",
        )
        DEDUCTION = "DEDUCTION", "Deduction"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    source_driver_wallet = models.ForeignKey(
        Wallet,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="outgoing_transactions",
        db_column="source_driver_wallet_id",
    )
    source_operator_wallet = models.ForeignKey(
        OperatorInternalWallet,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="outgoing_transactions",
        db_column="source_operator_wallet_id",
    )
    destination_driver_wallet = models.ForeignKey(
        Wallet,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="incoming_transactions",
        db_column="destination_driver_wallet_id",
    )
    destination_operator_wallet = models.ForeignKey(
        OperatorInternalWallet,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="incoming_transactions",
        db_column="destination_operator_wallet_id",
    )
    amountCents = models.BigIntegerField(db_column="amountCents")
    category = models.CharField(max_length=50, choices=TransactionCategory.choices)
    taxCategory = models.CharField(
        max_length=50, choices=TaxCategory.choices, db_column="taxCategory"
    )

    class Meta:
        db_table = "WalletTransaction"
        managed = False


class ManualEntry(TimeStampedTenantModel):
    """
    Lançamento Financeiro Manual.
    Usado por despachantes ou clientes para adicionar bônus a corridas ou penalidades,
    sempre com um fluxo de Aprovação Pendente por trás (Four-Eyes Principle).
    """

    class EntryStatus(models.TextChoices):
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    store = models.ForeignKey(
        Store, null=True, blank=True, on_delete=models.SET_NULL, db_column="store_id"
    )
    created_by_staff = models.ForeignKey(
        StaffMember,
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="created_manual_entries",
        db_column="created_by_staff_id",
    )
    created_by_client = models.ForeignKey(
        ClientPortalUser,
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="created_manual_entries",
        db_column="created_by_client_id",
    )
    amountCents = models.BigIntegerField(db_column="amountCents")
    description = models.TextField()
    visibleToStore = models.BooleanField(default=True, db_column="visibleToStore")
    taxCategory = models.CharField(
        max_length=50,
        choices=WalletTransaction.TaxCategory.choices,
        db_column="taxCategory",
    )
    status = models.CharField(
        max_length=30, choices=EntryStatus.choices, default=EntryStatus.PENDING_APPROVAL
    )
    rejectReason = models.TextField(null=True, blank=True, db_column="rejectReason")
    approvedBy = models.ForeignKey(
        StaffMember,
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="approved_manual_entries",
        db_column="approvedById",
    )

    class Meta:
        db_table = "ManualEntry"
        managed = False


class DailyCreditCalculation(TimeStampedTenantModel):
    """
    Consolidação de Crédito Diário (Fechamento do Dia).

    Workers do Celery processam essa tabela toda madrugada (após o cutoff) para
    apurar quanto um motorista rodou, comparar com o mínimo garantido de contrato
    da Loja e consolidar o saldo final que será enviado para a Wallet Ledger.
    """

    class CreditStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CREDITED = "CREDITED", "Credited"
        SKIPPED = "SKIPPED", "Skipped"
        FAILED = "FAILED", "Failed"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    date = models.DateField(help_text="O Business Date computado para a apuração.")
    status = models.CharField(
        max_length=20, choices=CreditStatus.choices, default=CreditStatus.PENDING
    )
    productionValueCents = models.BigIntegerField(
        default=0, db_column="productionValueCents"
    )
    extrasCents = models.BigIntegerField(default=0, db_column="extrasCents")
    dailyRateOrGuaranteedCents = models.BigIntegerField(
        default=0, db_column="dailyRateOrGuaranteedCents"
    )
    advancesCents = models.BigIntegerField(default=0, db_column="advancesCents")
    netAmountCents = models.BigIntegerField(default=0, db_column="netAmountCents")
    failReason = models.TextField(null=True, blank=True, db_column="failReason")

    class Meta:
        db_table = "DailyCreditCalculation"
        managed = False


class WeeklyStoreInvoice(TimeStampedTenantModel):
    """
    Fatura de Cobrança Semanal da Loja.
    Agrupa todo o saldo apurado durante os sete dias úteis, somado aos fees de gestão,
    gerando o boleto/pix a ser liquidado pelo parceiro.
    """

    class InvoiceStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        DISPUTED = "DISPUTED", "Disputed"
        FINALIZED = "FINALIZED", "Finalized"
        LOCKED = "LOCKED", "Locked"
        PAID = "PAID", "Paid"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    startDate = models.DateField(db_column="startDate")
    endDate = models.DateField(db_column="endDate")
    totalNetProducaoCents = models.BigIntegerField(
        default=0, db_column="totalNetProducaoCents"
    )
    totalNetGarantidaCents = models.BigIntegerField(
        default=0, db_column="totalNetGarantidaCents"
    )
    administrativeFeeCents = models.BigIntegerField(
        default=0, db_column="administrativeFeeCents"
    )
    supervisionFeeCents = models.BigIntegerField(
        default=0, db_column="supervisionFeeCents"
    )
    pendingDebitCarriedCents = models.BigIntegerField(
        default=0, db_column="pendingDebitCarriedCents"
    )
    totalCents = models.BigIntegerField(
        default=0,
        db_column="totalCents",
        help_text="Total geral da fatura que será enviado ao Gateway.",
    )
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT
    )
    paymentGatewayId = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column="paymentGatewayId",
        help_text="ID do Gateway de Pagamento (Asaas/Stripe).",
    )
    pixCopyPaste = models.TextField(null=True, blank=True, db_column="pixCopyPaste")
    barcode = models.TextField(null=True, blank=True)
    pdfUrl = models.CharField(max_length=255, null=True, blank=True, db_column="pdfUrl")

    class Meta:
        db_table = "WeeklyStoreInvoice"
        managed = False


class WeeklyInvoiceLineItem(TimeStampedTenantModel):
    """
    Item Detalhado da Fatura.
    Para gerar o Breakdown discriminando os custos corrida a corrida, ou turno a turno,
    eliminando dúvidas da loja.
    """

    class ItemStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DISPUTED = "DISPUTED", "Disputed"
        WAIVED = "WAIVED", "Waived"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    invoice = models.ForeignKey(
        WeeklyStoreInvoice, on_delete=models.CASCADE, db_column="invoice_id"
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True, db_column="driver_id"
    )
    businessDate = models.DateField(null=True, blank=True, db_column="businessDate")
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, db_column="order_id"
    )
    manualEntry = models.ForeignKey(
        ManualEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="manualEntryId",
    )
    description = models.TextField()
    amountCents = models.BigIntegerField(db_column="amountCents")
    status = models.CharField(
        max_length=20, choices=ItemStatus.choices, default=ItemStatus.ACTIVE
    )
    disputeReason = models.TextField(null=True, blank=True, db_column="disputeReason")

    class Meta:
        db_table = "WeeklyInvoiceLineItem"
        managed = False


class WithdrawalRequest(TimeStampedTenantModel):
    """
    Pedido de Saque.
    Comando acionado pelo aplicativo do Motoboy para disparar
    PIX imediato via BaaS Efí Pay ou enfileirar para aprovação do despachante.
    """

    class WithdrawalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    class PixKeyType(models.TextChoices):
        CPF = "CPF", "CPF"
        CNPJ = "CNPJ", "CNPJ"
        EMAIL = "EMAIL", "E-mail"
        PHONE = "PHONE", "Telefone"
        EVP = "EVP", "Chave Aleatória (EVP)"

    class ApprovalMode(models.TextChoices):
        AUTO_INSTANT = "AUTO_INSTANT", "Automático Imediato"
        MANUAL_PENDING = "MANUAL_PENDING", "Aprovação Manual"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    amountCents = models.BigIntegerField(db_column="amountCents")
    status = models.CharField(
        max_length=20,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING,
    )
    pixKey = models.CharField(max_length=255, db_column="pixKey")
    pixKeyType = models.CharField(
        max_length=20,
        choices=PixKeyType.choices,
        default=PixKeyType.CPF,
        db_column="pixKeyType",
    )
    approvalMode = models.CharField(
        max_length=30,
        choices=ApprovalMode.choices,
        default=ApprovalMode.AUTO_INSTANT,
        db_column="approvalMode",
    )
    feeAmountCents = models.BigIntegerField(default=0, db_column="feeAmountCents")
    netAmountCents = models.BigIntegerField(default=0, db_column="netAmountCents")
    approvedBy = models.ForeignKey(
        StaffMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="approved_by_id",
    )
    approvedAt = models.DateTimeField(null=True, blank=True, db_column="approvedAt")
    rejectionReason = models.TextField(null=True, blank=True, db_column="rejectionReason")
    baasProvider = models.CharField(
        max_length=50, default="EFI_PAY", db_column="baasProvider"
    )
    baasTransactionId = models.CharField(
        max_length=255, null=True, blank=True, db_column="baasTransactionId"
    )
    baasRawResponse = models.JSONField(
        default=dict, blank=True, db_column="baasRawResponse"
    )
    failureReason = models.TextField(null=True, blank=True, db_column="failureReason")
    processedAt = models.DateTimeField(null=True, blank=True, db_column="processedAt")

    class Meta:
        db_table = "WithdrawalRequest"
        managed = False
        verbose_name = "Pedido de Saque"
        verbose_name_plural = "Pedidos de Saque"


class PayoutPolicyConfig(TimeStampedTenantModel):
    """
    Configuração Global da Política de Saques e BaaS PIX para o Operador.
    Define se saques são liberados instantaneamente dentro de um teto (HYBRID_THRESHOLD)
    ou se todos exigem aprovação humana (MANUAL_ALL), além de limites e tarifas.
    """

    class PayoutMode(models.TextChoices):
        HYBRID_THRESHOLD = "HYBRID_THRESHOLD", "Híbrido (Alçada)"
        MANUAL_ALL = "MANUAL_ALL", "Aprovação Manual para Todos"

    class PayoutFeeMode(models.TextChoices):
        ABSORBED_BY_PLATFORM = "ABSORBED_BY_PLATFORM", "Absorvida pela Plataforma"
        CHARGED_TO_DRIVER = "CHARGED_TO_DRIVER", "Cobrada do Entregador"

    operator = models.OneToOneField(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    mode = models.CharField(
        max_length=30,
        choices=PayoutMode.choices,
        default=PayoutMode.HYBRID_THRESHOLD,
        db_column="mode",
    )
    autoThresholdCents = models.BigIntegerField(
        default=15000,
        db_column="autoThresholdCents",
        help_text="Valor máximo em centavos para liberação automática de PIX (ex: 15000 = R$ 150,00).",
    )
    dailyLimitPerDriverCents = models.BigIntegerField(
        default=50000,
        db_column="dailyLimitPerDriverCents",
        help_text="Teto diário acumulado de saque por motoboy nas últimas 24h.",
    )
    minWithdrawalCents = models.BigIntegerField(
        default=1000,
        db_column="minWithdrawalCents",
        help_text="Valor mínimo por solicitação de saque.",
    )
    payoutFeeMode = models.CharField(
        max_length=30,
        choices=PayoutFeeMode.choices,
        default=PayoutFeeMode.ABSORBED_BY_PLATFORM,
        db_column="payoutFeeMode",
    )
    payoutFeeCents = models.BigIntegerField(
        default=0,
        db_column="payoutFeeCents",
        help_text="Taxa fixa retida do entregador quando payoutFeeMode = CHARGED_TO_DRIVER.",
    )
    notifyPushEnabled = models.BooleanField(
        default=True,
        db_column="notifyPushEnabled",
        help_text="Disparar notificação Push via FCM no NevesGo ao concluir PIX.",
    )
    notifyWhatsappEnabled = models.BooleanField(
        default=True,
        db_column="notifyWhatsappEnabled",
        help_text="Enviar mensagem e comprovante PIX via Z-API WhatsApp.",
    )

    class Meta:
        db_table = "PayoutPolicyConfig"
        managed = False
        verbose_name = "Configuração de Política de Saque"
        verbose_name_plural = "Configurações de Políticas de Saque"


class DriverExpense(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL, db_column="order_id"
    )
    type = models.CharField(max_length=20)
    amountCents = models.BigIntegerField(db_column="amountCents")
    description = models.TextField()
    status = models.CharField(max_length=20, default="SUBMITTED")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "DriverExpense"
        managed = False


class DriverExpenseReceipt(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    expense = models.ForeignKey(
        DriverExpense, on_delete=models.CASCADE, db_column="expense_id"
    )
    fileUrl = models.TextField(db_column="fileUrl")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "DriverExpenseReceipt"
        managed = False
