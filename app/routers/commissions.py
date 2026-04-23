# Rutas de API para gestion de comisiones de taller a plataforma.

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.controllers.commission_controller import (
    confirm_commission_payment_controller,
    create_commission_payment_controller,
    get_workshop_commission_summary_controller,
    list_all_commission_payments_controller,
    list_workshop_commission_payments_controller,
    reject_commission_payment_controller,
    upload_commission_proof_controller,
    upload_platform_qr_controller,
)
from app.core.payment_storage import (
    resolve_commission_proofs_directory,
    resolve_platform_qr_directory,
)
from app.database import get_db
from app.dependencies.auth import (
    AuthenticatedUser,
    require_web_superuser,
    require_web_taller,
)
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

router = APIRouter(prefix="/api/v1/commissions", tags=["Commissions"])


@router.post(
    "/admin/platform-qr-upload",
    response_model=PlatformQrUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_platform_qr_endpoint(
    request: Request,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
) -> PlatformQrUploadResponse:
    """Sube el QR de pago de la plataforma. Acceso solo para superusuarios."""
    _ = current_user

    content = await file.read()
    max_size_bytes = 10 * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen QR supera el limite permitido (10 MB).",
        )

    return upload_platform_qr_controller(
        file_bytes=content,
        original_file_name=file.filename,
        content_type=file.content_type,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.get(
    "/workshop/summary",
    response_model=WorkshopCommissionSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def get_workshop_commission_summary_endpoint(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopCommissionSummaryResponse:
    """Obtiene el resumen de comisiones pendientes del taller autenticado."""
    return get_workshop_commission_summary_controller(
        taller_id=current_user.user_id,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.post(
    "/workshop/create",
    response_model=CommissionPaymentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commission_payment_endpoint(
    payload: CommissionPaymentCreateRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> CommissionPaymentCreateResponse:
    """Crea un pago de comision del taller a la plataforma."""
    return create_commission_payment_controller(
        payload,
        taller_id=current_user.user_id,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.post(
    "/workshop/upload-proof",
    response_model=CommissionPaymentUploadProofResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_commission_proof_endpoint(
    request: Request,
    payment_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> CommissionPaymentUploadProofResponse:
    """Sube comprobante de pago de comision."""
    if payment_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="payment_id invalido."
        )

    content = await file.read()
    max_size_bytes = 15 * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El comprobante supera el limite permitido.",
        )

    return upload_commission_proof_controller(
        payment_id=payment_id,
        taller_id=current_user.user_id,
        file_bytes=content,
        original_file_name=file.filename,
        content_type=file.content_type,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.get(
    "/workshop/payments",
    response_model=CommissionPaymentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_workshop_commission_payments_endpoint(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> CommissionPaymentListResponse:
    """Lista pagos de comision del taller autenticado."""
    return list_workshop_commission_payments_controller(
        taller_id=current_user.user_id,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.get(
    "/admin/payments",
    response_model=CommissionPaymentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_all_commission_payments_endpoint(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
) -> CommissionPaymentListResponse:
    """Lista todos los pagos de comision. Acceso solo para superusuarios."""
    _ = current_user
    return list_all_commission_payments_controller(
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.post(
    "/admin/confirm",
    response_model=CommissionPaymentConfirmResponse,
    status_code=status.HTTP_200_OK,
)
def confirm_commission_payment_endpoint(
    payload: CommissionPaymentConfirmRequest,
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
) -> CommissionPaymentConfirmResponse:
    """Confirma un pago de comision. Acceso solo para superusuarios."""
    _ = current_user
    return confirm_commission_payment_controller(payload, db=db)


@router.post(
    "/admin/reject",
    response_model=CommissionPaymentRejectResponse,
    status_code=status.HTTP_200_OK,
)
def reject_commission_payment_endpoint(
    payload: CommissionPaymentRejectRequest,
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
) -> CommissionPaymentRejectResponse:
    """Rechaza un pago de comision. Acceso solo para superusuarios."""
    _ = current_user
    return reject_commission_payment_controller(payload, db=db)


@router.get(
    "/proofs/{file_name}",
    status_code=status.HTTP_200_OK,
)
def get_commission_proof_file_endpoint(file_name: str) -> FileResponse:
    """Obtiene un comprobante de pago de comision."""
    if Path(file_name).name != file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo invalido."
        )

    file_path = resolve_commission_proofs_directory() / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comprobante no encontrado."
        )

    return FileResponse(path=file_path)


@router.get(
    "/platform-qr/{file_name}",
    status_code=status.HTTP_200_OK,
)
def get_platform_qr_file_endpoint(file_name: str) -> FileResponse:
    """Obtiene el QR de la plataforma."""
    if Path(file_name).name != file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo invalido."
        )

    file_path = resolve_platform_qr_directory() / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="QR no encontrado."
        )

    return FileResponse(path=file_path)
