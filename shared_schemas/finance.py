from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

class WalletResponse(BaseModel):
    model_config = {"from_attributes": True}
    balanceCents: int
    updatedAt: datetime

class WithdrawalRequestPayload(BaseModel):
    amountCents: int = Field(..., gt=0)
    pixKey: str

class WithdrawalResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    amountCents: int
    status: str
    pixKey: str
    createdAt: datetime

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

