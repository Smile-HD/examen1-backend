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


class PaymentListItemResponse(BaseModel):
    payment_id: int
    incident_id: int
    user_id: int
    taller_id: int
    amount: float
    commission: float
    status: str
    proof_image_url: str | None
    proof_image_url_absolute: str | None
    created_at: datetime


class PaymentListResponse(BaseModel):
    total: int
    payments: list[PaymentListItemResponse]
