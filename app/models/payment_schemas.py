from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PaymentCreateRequest(BaseModel):
    # Datos para crear una orden de pago QR asociada a un incidente.

    incident_id: int = Field(gt=0)
    amount: float = Field(gt=0)
    workshop_account: str | None = Field(default=None, max_length=120)

    @field_validator("workshop_account")
    @classmethod
    def normalize_optional_account(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PaymentCreateResponse(BaseModel):
    payment_id: int
    incident_id: int
    user_id: int
    taller_id: int
    amount: float
    commission: float
    status: str
    reference: str
    workshop_account: str
    qr_payload: str
    qr_image_url: str
    qr_image_url_absolute: str
    created_at: datetime
    message: str


class PaymentUploadProofRequest(BaseModel):
    payment_id: int = Field(gt=0)


class PaymentUploadProofResponse(BaseModel):
    payment_id: int
    status: str
    proof_image_url: str
    proof_image_url_absolute: str
    message: str


class PaymentConfirmRequest(BaseModel):
    payment_id: int = Field(gt=0)


class PaymentConfirmResponse(BaseModel):
    payment_id: int
    incident_id: int
    status: str
    incident_status: str
    message: str


class PaymentRejectRequest(BaseModel):
    payment_id: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_optional_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PaymentRejectResponse(BaseModel):
    payment_id: int
    incident_id: int
    status: str
    incident_status: str
    message: str


class PaymentListItemResponse(BaseModel):
    payment_id: int
    incident_id: int
    user_id: int
    user_name: str | None
    taller_id: int
    taller_name: str | None
    amount: float
    commission: float
    net_amount_to_workshop: float
    status: str
    reference: str
    proof_image_url: str | None
    proof_image_url_absolute: str | None
    qr_image_url: str | None
    qr_image_url_absolute: str | None
    created_at: datetime


class PaymentListResponse(BaseModel):
    total: int
    payments: list[PaymentListItemResponse]


class PaymentWorkshopSummaryItemResponse(BaseModel):
    taller_id: int
    taller_name: str
    taller_estado: str  # Estado del taller: activo/inactivo
    total_payments: int
    confirmed_payments: int
    pending_payments: int
    verification_payments: int
    rejected_payments: int
    total_amount: float
    total_commission: float
    total_net_to_workshop: float
    amount_due_to_platform: float


class PaymentAdminSummaryResponse(BaseModel):
    generated_at: datetime
    total_payments: int
    confirmed_payments: int
    pending_payments: int
    verification_payments: int
    rejected_payments: int
    total_amount: float
    total_commission: float
    total_net_to_workshop: float
    workshops: list[PaymentWorkshopSummaryItemResponse]
    payments: list[PaymentListItemResponse]
