from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID

# --- Schemas Base da Lógica de Negócio ---

class StoreSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    averagePrepTimeMinutes: int
    geom: Optional[Dict[str, Any]] = None # GeoJSON representation do Point

    @field_validator("geom", mode="before")
    @classmethod
    def _coerce_geom(cls, value):
        if value is None or isinstance(value, dict):
            return value
        return None

class DriverSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    phone: str
    online: bool
    active: bool
    lastPingAt: Optional[datetime] = None

class StopSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    sequence: int
    type: str
    requiresPin: bool
    completedAt: Optional[datetime] = None
    geom: Optional[Dict[str, Any]] = None # GeoJSON do Point

    @field_validator("geom", mode="before")
    @classmethod
    def _coerce_geom(cls, value):
        if value is None or isinstance(value, dict):
            return value
        return None

class ManifestSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    status: str
    groupingMethod: str
    totalDistanceMeters: Optional[int] = None
    totalEtaSeconds: Optional[int] = None
    lockedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    driver: Optional[DriverSchema] = None

class OrderSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    status: str
    fareValueCents: int
    distanceMeters: Optional[int] = None
    businessDate: date
    requestedAt: Optional[datetime] = None
    acceptedAt: Optional[datetime] = None
    startedAt: Optional[datetime] = None
    arrivedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    canceledAt: Optional[datetime] = None
    store: StoreSchema
    driver: Optional[DriverSchema] = None
    manifest: Optional[UUID] = None

# --- Schemas de Entrada da API (Inputs) ---

class DispatchPayload(BaseModel):
    model_config = {"from_attributes": True}
    store_id: UUID
    client_id: UUID
    driver_id: Optional[UUID] = None
    fareValueCents: int
    businessDate: Optional[date] = None
    distanceMeters: Optional[int] = 0

class StopBatchCompleteItem(BaseModel):
    model_config = {"from_attributes": True}
    stop_id: UUID
    delivery_pin: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    timestamp: datetime

class ShiftCheckInSchema(BaseModel):
    model_config = {"from_attributes": True}
    turno_id: UUID
    store_id: UUID
    date: date


class DriverStatusPayload(BaseModel):
    model_config = {"from_attributes": True}
    status: str
    reason: Optional[str] = None


class DriverStatusResponse(BaseModel):
    model_config = {"from_attributes": True}
    driver_id: UUID
    status: str
    online: bool
    reason: Optional[str] = None
    updated_at: datetime


class OrderRejectPayload(BaseModel):
    model_config = {"from_attributes": True}
    reason_code: str
    reason_text: Optional[str] = None


class OrderReleasePayload(BaseModel):
    model_config = {"from_attributes": True}
    reason: str


class OrderOfferStopSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    sequence: int
    type: str
    requiresPin: bool
    completedAt: Optional[datetime] = None
    location: Optional[Dict[str, float]] = None


class OrderOfferDetailResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    status: str
    fareValueCents: int
    distanceMeters: Optional[int] = None
    businessDate: date
    origin: Dict[str, Any]
    destination: Dict[str, Any]
    current_driver_id: Optional[UUID] = None
    stops: List[OrderOfferStopSchema]


class DriverCockpitResponse(BaseModel):
    model_config = {"from_attributes": True}
    driver: Dict[str, Any]
    shift: Optional[Dict[str, Any]] = None
    today: Dict[str, int]
    wallet: Dict[str, int]
    active_order: Optional[Dict[str, Any]] = None
    active_orders: List[Dict[str, Any]] = Field(default_factory=list)
    active_orders_count: int = 0
    active_orders_limit: int = 0
    pending_documents: int = 0
    unread_messages: int = 0


class DriverShiftCheckoutPayload(BaseModel):
    model_config = {"from_attributes": True}
    reason: Optional[str] = None


class DriverIncidentCreatePayload(BaseModel):
    model_config = {"from_attributes": True}
    order_id: Optional[UUID] = None
    stop_id: Optional[UUID] = None
    type: str
    description: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DriverPerformanceResponse(BaseModel):
    model_config = {"from_attributes": True}
    deliveries: int
    earnings_cents: int
    incidents_open: int
    acceptance_rate: float
    completion_rate: float


class DriverCalendarItem(BaseModel):
    model_config = {"from_attributes": True}
    kind: str
    date: str
    status: str
    store_id: str
    store_name: str
    turno_id: str
    turno_name: str


class DriverShiftReservationPayload(BaseModel):
    model_config = {"from_attributes": True}
    store_id: UUID
    turno_id: UUID
    date: date
    note: Optional[str] = None


class DriverDeviceRegisterPayload(BaseModel):
    model_config = {"from_attributes": True}
    device_identifier: str
    platform: str
    label: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DriverDeviceAttestationPayload(BaseModel):
    model_config = {"from_attributes": True}
    device_identifier: str
    risk_level: str
    flags: Dict[str, Any] = Field(default_factory=dict)


class DriverOfflineSyncPayload(BaseModel):
    model_config = {"from_attributes": True}
    device_identifier: str
    items: List[Dict[str, Any]] = Field(default_factory=list)


class DriverExpensePayload(BaseModel):
    model_config = {"from_attributes": True}
    type: str
    amountCents: int = Field(..., gt=0)
    description: str
    order_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceDocumentPayload(BaseModel):
    model_config = {"from_attributes": True}
    audience_type: str = "DRIVER"
    code: str
    title: str
    version: str
    body: str
    required: bool = True
    effective_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DriverConsentItem(BaseModel):
    model_config = {"from_attributes": True}
    consent_id: UUID
    audience_type: str
    code: str
    title: str
    version: str
    body: str
    required: bool
    accepted: bool
    effective_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DriverConsentRevokePayload(BaseModel):
    model_config = {"from_attributes": True}
    reason: str


class PrivacyDataRequestCreatePayload(BaseModel):
    model_config = {"from_attributes": True}
    request_type: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PrivacyDataRequestResolvePayload(BaseModel):
    model_config = {"from_attributes": True}
    status: str
    resolution: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PrivacyDataRequestItem(BaseModel):
    model_config = {"from_attributes": True}
    request_id: UUID
    subject_type: str
    request_type: str
    status: str
    description: str
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ComplianceRetentionPolicyPayload(BaseModel):
    model_config = {"from_attributes": True}
    resource_type: str
    retention_days: int = Field(..., gt=0)
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceRetentionPolicyItem(BaseModel):
    model_config = {"from_attributes": True}
    policy_id: UUID
    resource_type: str
    retention_days: int
    active: bool
    last_executed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ClientDispatchOrderPayload(BaseModel):
    model_config = {"from_attributes": True}
    store_id: UUID
    driver_id: Optional[UUID] = None
    fareValueCents: int = Field(..., ge=0)
    distanceMeters: int = Field(0, ge=0)
    businessDate: Optional[date] = None


class OrderReassignmentPayload(BaseModel):
    model_config = {"from_attributes": True}
    new_driver_id: Optional[UUID] = None
    reason: str


class CommunicationThreadCreatePayload(BaseModel):
    model_config = {"from_attributes": True}
    order_id: UUID
    subject: Optional[str] = None
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CommunicationMessagePayload(BaseModel):
    model_config = {"from_attributes": True}
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

# --- Schemas da Fast Lane (Telemetria) ---

class TelemetryPayload(BaseModel):
    model_config = {"from_attributes": True}
    """
    O driver_id e operator_id não são mais enviados pelo client.
    O client envia apenas lat, lng, speed, heading.
    A identidade é extraída estritamente do Device Token!
    """
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    heading: int = Field(0, ge=0, le=360)
    speedKmh: int = Field(0, ge=0)
    timestamp: Optional[int] = None
