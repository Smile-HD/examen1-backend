from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.controllers.payment_controller import (
    confirm_payment_controller,
    create_payment_controller,
    list_admin_payment_summary_controller,
    list_client_payments_controller,
    list_workshop_payments_controller,
    reject_payment_controller,
    upload_payment_proof_controller,
)
from app.core.payment_storage import (
    resolve_payment_proofs_directory,
    resolve_payment_qr_directory,
)
from app.database import get_db
from app.dependencies.auth import (
    AuthenticatedUser,
    require_mobile_cliente,
    require_web_superuser,
    require_web_taller,
)
from app.models.payment_schemas import PaymentListResponse
from app.models.payment_schemas import (
    PaymentAdminSummaryResponse,
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentRejectRequest,
    PaymentRejectResponse,
    PaymentUploadProofResponse,
)

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post(
    "/create",
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_endpoint(
    payload: PaymentCreateRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> PaymentCreateResponse:
    return create_payment_controller(
        payload,
        user_id=current_user.user_id,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.post(
    "/upload-proof",
    response_model=PaymentUploadProofResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_payment_proof_endpoint(
    request: Request,
    payment_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> PaymentUploadProofResponse:
    if payment_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_id invalido.")

    content = await file.read()
    max_size_bytes = 15 * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El comprobante supera el limite permitido.",
        )

    return upload_payment_proof_controller(
        payment_id=payment_id,
        user_id=current_user.user_id,
        file_bytes=content,
        original_file_name=file.filename,
        content_type=file.content_type,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.post(
    "/confirm",
    response_model=PaymentConfirmResponse,
    status_code=status.HTTP_200_OK,
)
def confirm_payment_endpoint(
    payload: PaymentConfirmRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> PaymentConfirmResponse:
    return confirm_payment_controller(payload, taller_id=current_user.user_id, db=db)


@router.post(
    "/reject",
    response_model=PaymentRejectResponse,
    status_code=status.HTTP_200_OK,
)
def reject_payment_endpoint(
    payload: PaymentRejectRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> PaymentRejectResponse:
    return reject_payment_controller(payload, taller_id=current_user.user_id, db=db)


@router.get(
    "/workshop",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_workshop_payments_endpoint(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> PaymentListResponse:
    return list_workshop_payments_controller(
        taller_id=current_user.user_id,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.get(
    "/client",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_client_payments_endpoint(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> PaymentListResponse:
    return list_client_payments_controller(
        user_id=current_user.user_id,
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.get(
    "/admin/summary",
    response_model=PaymentAdminSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def list_admin_payment_summary_endpoint(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
) -> PaymentAdminSummaryResponse:
    _ = current_user
    return list_admin_payment_summary_controller(
        base_url=str(request.base_url).rstrip("/"),
        db=db,
    )


@router.get(
    "/proofs/{file_name}",
    status_code=status.HTTP_200_OK,
)
def get_payment_proof_file_endpoint(file_name: str) -> FileResponse:
    if Path(file_name).name != file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo invalido.")

    file_path = resolve_payment_proofs_directory() / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comprobante no encontrado.")

    return FileResponse(path=file_path)


@router.get(
    "/qr/{file_name}",
    status_code=status.HTTP_200_OK,
)
def get_payment_qr_file_endpoint(file_name: str) -> FileResponse:
    if Path(file_name).name != file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo invalido.")

    file_path = resolve_payment_qr_directory() / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR no encontrado.")

    return FileResponse(path=file_path)
