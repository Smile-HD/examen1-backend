# Schemas Pydantic para APIs de comisiones.

from datetime import datetime

from pydantic import BaseModel, Field


class PlatformQrUploadResponse(BaseModel):
    qr_image_url: str
    qr_image_url_absolute: str
    message: str


class WorkshopCommissionSummaryResponse(BaseModel):
    taller_id: int
    taller_name: str
    pending_commission: float
    qr_image_url: str | None
    qr_image_url_absolute: str | None


class CommissionPaymentCreateRequest(BaseModel):
    amount: float = Field(..., gt=0)


class CommissionPaymentCreateResponse(BaseModel):
    payment_id: int
    taller_id: int
    amount: float
    status: str
    qr_image_url: str | None
    qr_image_url_absolute: str | None
    created_at: datetime
    message: str


class CommissionPaymentUploadProofResponse(BaseModel):
    payment_id: int
    status: str
    proof_image_url: str
    proof_image_url_absolute: str
    message: str


class CommissionPaymentListItemResponse(BaseModel):
    payment_id: int
    taller_id: int
    taller_name: str
    amount: float
    status: str
    proof_image_url: str | None
    proof_image_url_absolute: str | None
    created_at: datetime
    confirmed_at: datetime | None


class CommissionPaymentListResponse(BaseModel):
    total: int
    payments: list[CommissionPaymentListItemResponse]


class CommissionPaymentConfirmRequest(BaseModel):
    payment_id: int


class CommissionPaymentConfirmResponse(BaseModel):
    payment_id: int
    taller_id: int
    status: str
    message: str


class CommissionPaymentRejectRequest(BaseModel):
    payment_id: int
    reason: str | None = None


class CommissionPaymentRejectResponse(BaseModel):
    payment_id: int
    taller_id: int
    status: str
    message: str
