from pydantic import BaseModel, Field
from typing import Optional
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
    cpf: str = Field(..., max_length=14, description="CPF do motorista (formatado ou não)")
    pixKey: Optional[str] = None
    cnhNumber: Optional[str] = None


class DriverBiometricPayload(BaseModel):
    driver_id: UUID
    face_image_base64: str
    cnh_image_base64: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DriverBiometricResponse(BaseModel):
    status: str
    match_score: float
    message: str


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


class BiometricWebhookPayload(BaseModel):
    driver_id: UUID
    status: str
    match_score: float
