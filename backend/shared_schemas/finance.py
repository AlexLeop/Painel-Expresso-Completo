from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class WalletResponse(BaseModel):
    model_config = {"from_attributes": True}
    balanceCents: int
    updatedAt: datetime


class WithdrawalRequestPayload(BaseModel):
    amountCents: int = Field(..., gt=0)
    pixKey: str
    pixKeyType: Optional[str] = "CPF"


class WithdrawalResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    amountCents: int
    feeAmountCents: int = 0
    netAmountCents: int = 0
    status: str
    pixKey: str
    pixKeyType: Optional[str] = "CPF"
    approvalMode: Optional[str] = "AUTO_INSTANT"
    createdAt: datetime
    processedAt: Optional[datetime] = None
    failureReason: Optional[str] = None
    rejectionReason: Optional[str] = None


class PayoutPolicyConfigSchema(BaseModel):
    model_config = {"from_attributes": True}
    mode: str = "HYBRID_THRESHOLD"
    autoThresholdCents: int = 15000
    dailyLimitPerDriverCents: int = 50000
    minWithdrawalCents: int = 1000
    payoutFeeMode: str = "ABSORBED_BY_PLATFORM"
    payoutFeeCents: int = 0
    notifyPushEnabled: bool = True
    notifyWhatsappEnabled: bool = True


class WithdrawalAdminDetailResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    driver_id: UUID
    driver_name: str
    driver_phone: Optional[str] = None
    amountCents: int
    feeAmountCents: int = 0
    netAmountCents: int = 0
    status: str
    pixKey: str
    pixKeyType: str = "CPF"
    approvalMode: str = "AUTO_INSTANT"
    baasProvider: str = "EFI_PAY"
    baasTransactionId: Optional[str] = None
    failureReason: Optional[str] = None
    rejectionReason: Optional[str] = None
    approvedAt: Optional[datetime] = None
    processedAt: Optional[datetime] = None
    createdAt: datetime


class WithdrawalRejectionPayload(BaseModel):
    reason: str = Field(..., min_length=3)


class BulkApprovalPayload(BaseModel):
    withdrawal_ids: list[UUID]


class BaasBalanceResponse(BaseModel):
    saldo: float
    saldo_cents: int
    bloqueado: float = 0.0
    mock: bool = False


class ManualEntryPayload(BaseModel):
    driver_id: UUID
    store_id: Optional[UUID] = None
    amountCents: int
    description: str
    visibleToStore: bool = True
    taxCategory: str


class ManualEntryResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    amountCents: int
    description: str
    status: str
    taxCategory: str
    createdAt: datetime


class InvoiceResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    startDate: date
    endDate: date
    totalCents: int
    status: str
    barcode: Optional[str] = None
    pixCopyPaste: Optional[str] = None


class TransactionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    amountCents: int
    category: str
    taxCategory: str
    createdAt: datetime
