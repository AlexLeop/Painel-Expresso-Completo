from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class OperatorCreatePayload(BaseModel):
    name: str = Field(..., max_length=255)

class OperatorResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    status: str
    createdAt: datetime

class DriverRegistrationPayload(BaseModel):
    name: str
    phone: str
    pixKey: Optional[str] = None
    cnhNumber: Optional[str] = None

class DriverResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    phone: str
    online: bool
    active: bool

class DenyListPayload(BaseModel):
    targetId: UUID
    targetType: str = Field(..., description="Ex: DEVICE_TOKEN, IP, DRIVER_ID")
    reason: str
    expiresAt: Optional[datetime] = None

class DenyListResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    targetId: UUID
    targetType: str
    reason: str
    blockedAt: datetime
    expiresAt: Optional[datetime] = None
