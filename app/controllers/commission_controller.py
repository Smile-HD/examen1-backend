# Controladores para APIs de comisiones.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.commission_schemas import (
    CommissionPaymentConfirmRequest,
    CommissionPaymentConfirmResponse,
    CommissionPaymentCreateRequest,
    CommissionPaymentCreateResponse,
    CommissionPaymentListResponse,
    CommissionPaymentRejectRequest,
    CommissionPaymentRejectResponse,
    CommissionPaymentUploadProofResponse,
    PlatformQrUploadResponse,
    WorkshopCommissionSummaryResponse,
)
from app.services.Admin.commission_service import (
    CommissionPaymentNotFoundError,
    InvalidCommissionPaymentStateError,
    PlatformQrNotConfiguredError,
    confirm_commission_payment,
    create_commission_payment,
    get_workshop_commission_summary,
    list_all_commission_payments,
    list_workshop_commission_payments,
    reject_commission_payment,
    upload_commission_proof,
    upload_platform_qr,
)


def upload_platform_qr_controller(
    *,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> PlatformQrUploadResponse:
    try:
        return upload_platform_qr(
            file_bytes=file_bytes,
            original_file_name=original_file_name,
            content_type=content_type,
            base_url=base_url,
            db=db,
        )
    except InvalidCommissionPaymentStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir QR: {str(e)}",
        )


def get_workshop_commission_summary_controller(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> WorkshopCommissionSummaryResponse:
    try:
        return get_workshop_commission_summary(
            taller_id=taller_id,
            base_url=base_url,
            db=db,
        )
    except CommissionPaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resumen: {str(e)}",
        )


def create_commission_payment_controller(
    payload: CommissionPaymentCreateRequest,
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> CommissionPaymentCreateResponse:
    try:
        return create_commission_payment(
            payload,
            taller_id=taller_id,
            base_url=base_url,
            db=db,
        )
    except CommissionPaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PlatformQrNotConfiguredError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear pago: {str(e)}",
        )


def upload_commission_proof_controller(
    *,
    payment_id: int,
    taller_id: int,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> CommissionPaymentUploadProofResponse:
    try:
        return upload_commission_proof(
            payment_id=payment_id,
            taller_id=taller_id,
            file_bytes=file_bytes,
            original_file_name=original_file_name,
            content_type=content_type,
            base_url=base_url,
            db=db,
        )
    except CommissionPaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidCommissionPaymentStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir comprobante: {str(e)}",
        )


def list_workshop_commission_payments_controller(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> CommissionPaymentListResponse:
    try:
        return list_workshop_commission_payments(
            taller_id=taller_id,
            base_url=base_url,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar pagos: {str(e)}",
        )


def list_all_commission_payments_controller(
    *,
    base_url: str,
    db: Session,
) -> CommissionPaymentListResponse:
    try:
        return list_all_commission_payments(
            base_url=base_url,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar pagos: {str(e)}",
        )


def confirm_commission_payment_controller(
    payload: CommissionPaymentConfirmRequest,
    *,
    db: Session,
) -> CommissionPaymentConfirmResponse:
    try:
        return confirm_commission_payment(payload, db=db)
    except CommissionPaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidCommissionPaymentStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al confirmar pago: {str(e)}",
        )


def reject_commission_payment_controller(
    payload: CommissionPaymentRejectRequest,
    *,
    db: Session,
) -> CommissionPaymentRejectResponse:
    try:
        return reject_commission_payment(payload, db=db)
    except CommissionPaymentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidCommissionPaymentStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al rechazar pago: {str(e)}",
        )
