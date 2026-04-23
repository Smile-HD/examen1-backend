from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment_schemas import (
    PaymentAdminSummaryResponse,
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListResponse,
    PaymentRejectRequest,
    PaymentRejectResponse,
    PaymentUploadProofResponse,
)
from app.services.Admin.payment_service import (
    IncidentNotFoundError,
    IncidentNotOwnedError,
    IncidentWithoutWorkshopError,
    InvalidPaymentStateError,
    PaymentAlreadyExistsError,
    PaymentNotFoundError,
    WorkshopQrNotConfiguredError,
    confirm_payment,
    create_payment,
    list_admin_payment_summary,
    list_client_payments,
    list_workshop_payments,
    reject_payment,
    upload_payment_proof,
)


def create_payment_controller(
    payload: PaymentCreateRequest,
    *,
    user_id: int,
    base_url: str,
    db: Session,
) -> PaymentCreateResponse:
    try:
        return create_payment(payload, user_id=user_id, base_url=base_url, db=db)
    except IncidentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentWithoutWorkshopError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkshopQrNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PaymentAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def upload_payment_proof_controller(
    *,
    payment_id: int,
    user_id: int,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> PaymentUploadProofResponse:
    try:
        return upload_payment_proof(
            payment_id=payment_id,
            user_id=user_id,
            file_bytes=file_bytes,
            original_file_name=original_file_name,
            content_type=content_type,
            base_url=base_url,
            db=db,
        )
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def confirm_payment_controller(
    payload: PaymentConfirmRequest,
    *,
    taller_id: int,
    db: Session,
) -> PaymentConfirmResponse:
    try:
        return confirm_payment(payload, taller_id=taller_id, db=db)
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def reject_payment_controller(
    payload: PaymentRejectRequest,
    *,
    taller_id: int,
    db: Session,
) -> PaymentRejectResponse:
    try:
        return reject_payment(payload, taller_id=taller_id, db=db)
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def list_workshop_payments_controller(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> PaymentListResponse:
    return list_workshop_payments(taller_id=taller_id, base_url=base_url, db=db)


def list_client_payments_controller(
    *,
    user_id: int,
    base_url: str,
    db: Session,
) -> PaymentListResponse:
    return list_client_payments(user_id=user_id, base_url=base_url, db=db)


def list_admin_payment_summary_controller(
    *,
    base_url: str,
    db: Session,
) -> PaymentAdminSummaryResponse:
    return list_admin_payment_summary(base_url=base_url, db=db)
