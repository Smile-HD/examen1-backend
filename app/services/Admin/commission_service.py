# Servicio para gestión de comisiones y pagos de taller a plataforma.

from uuid import uuid4
from datetime import datetime, timezone
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.payment_storage import (
    build_commission_proof_urls,
    build_platform_qr_urls,
    resolve_absolute_url,
    safe_proof_file_extension,
    save_commission_proof_image,
    save_platform_qr_image,
)
from app.models.commission_schemas import (
    CommissionPaymentConfirmRequest,
    CommissionPaymentConfirmResponse,
    CommissionPaymentCreateRequest,
    CommissionPaymentCreateResponse,
    CommissionPaymentListItemResponse,
    CommissionPaymentListResponse,
    CommissionPaymentRejectRequest,
    CommissionPaymentRejectResponse,
    CommissionPaymentUploadProofResponse,
    PlatformQrUploadResponse,
    WorkshopCommissionSummaryResponse,
)
from app.repositories.commission_repository import CommissionRepository

COMMISSION_STATUS_PENDING = "pendiente"
COMMISSION_STATUS_VERIFICATION = "verificacion"
COMMISSION_STATUS_CONFIRMED = "confirmado"
COMMISSION_STATUS_REJECTED = "rechazado"

logger = logging.getLogger(__name__)


class PlatformQrNotConfiguredError(Exception):
    pass


class CommissionPaymentNotFoundError(Exception):
    pass


class InvalidCommissionPaymentStateError(Exception):
    pass


def upload_platform_qr(
    *,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> PlatformQrUploadResponse:
    repository = CommissionRepository(db)

    if not file_bytes:
        raise InvalidCommissionPaymentStateError("El QR recibido esta vacio.")

    extension = safe_proof_file_extension(original_file_name, content_type)
    qr_file_name = f"platform_qr_{uuid4().hex}{extension}"
    save_platform_qr_image(file_bytes, qr_file_name)
    qr_image_url, qr_image_url_absolute = build_platform_qr_urls(base_url, qr_file_name)

    try:
        repository.create_or_update_platform_qr(qr_image_url)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return PlatformQrUploadResponse(
        qr_image_url=qr_image_url,
        qr_image_url_absolute=qr_image_url_absolute,
        message="QR de la plataforma actualizado correctamente.",
    )


def get_workshop_commission_summary(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> WorkshopCommissionSummaryResponse:
    repository = CommissionRepository(db)

    workshop = repository.get_workshop_by_id(taller_id)
    if not workshop:
        raise CommissionPaymentNotFoundError("Taller no encontrado.")

    pending_commission = repository.get_pending_commission_for_workshop(taller_id)

    platform_config = repository.get_platform_config()
    qr_image_url = platform_config.qr_image_url if platform_config else None
    qr_image_url_absolute = (
        resolve_absolute_url(base_url, qr_image_url) if qr_image_url else None
    )

    return WorkshopCommissionSummaryResponse(
        taller_id=taller_id,
        taller_name=workshop.nombre,
        pending_commission=pending_commission,
        qr_image_url=qr_image_url,
        qr_image_url_absolute=qr_image_url_absolute,
    )


def create_commission_payment(
    payload: CommissionPaymentCreateRequest,
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> CommissionPaymentCreateResponse:
    repository = CommissionRepository(db)

    workshop = repository.get_workshop_by_id(taller_id)
    if not workshop:
        raise CommissionPaymentNotFoundError("Taller no encontrado.")

    platform_config = repository.get_platform_config()
    qr_image_url = platform_config.qr_image_url if platform_config else None

    if not qr_image_url:
        raise PlatformQrNotConfiguredError(
            "La plataforma no tiene QR configurado. No se puede crear el pago de comision."
        )

    qr_image_url_absolute = resolve_absolute_url(base_url, qr_image_url)

    amount = round(float(payload.amount), 2)

    try:
        payment = repository.create_commission_payment(
            taller_id=taller_id,
            amount=amount,
            status=COMMISSION_STATUS_PENDING,
        )

        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommissionPaymentCreateResponse(
        payment_id=payment.id,
        taller_id=payment.taller_id,
        amount=float(payment.amount),
        status=payment.status,
        qr_image_url=qr_image_url,
        qr_image_url_absolute=qr_image_url_absolute,
        created_at=payment.created_at,
        message="Pago de comision creado correctamente.",
    )


def upload_commission_proof(
    *,
    payment_id: int,
    taller_id: int,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> CommissionPaymentUploadProofResponse:
    repository = CommissionRepository(db)

    payment = repository.get_commission_payment_for_workshop(payment_id, taller_id)
    if not payment:
        raise CommissionPaymentNotFoundError(
            "Pago de comision no encontrado para el taller autenticado."
        )

    if payment.status == COMMISSION_STATUS_CONFIRMED:
        raise InvalidCommissionPaymentStateError(
            "El pago ya fue confirmado y no admite nuevos comprobantes."
        )

    if payment.status not in [
        COMMISSION_STATUS_PENDING,
        COMMISSION_STATUS_VERIFICATION,
        COMMISSION_STATUS_REJECTED,
    ]:
        raise InvalidCommissionPaymentStateError(
            f"No se puede subir comprobante en estado {payment.status}."
        )

    if not file_bytes:
        raise InvalidCommissionPaymentStateError("El comprobante recibido esta vacio.")

    extension = safe_proof_file_extension(original_file_name, content_type)
    proof_file_name = f"commission_proof_{payment.id}_{uuid4().hex}{extension}"
    save_commission_proof_image(file_bytes, proof_file_name)
    proof_image_url, proof_image_url_absolute = build_commission_proof_urls(
        base_url, proof_file_name
    )

    try:
        repository.update_commission_payment(
            payment,
            proof_image_url=proof_image_url,
            status=COMMISSION_STATUS_VERIFICATION,
        )

        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommissionPaymentUploadProofResponse(
        payment_id=payment.id,
        status=payment.status,
        proof_image_url=proof_image_url,
        proof_image_url_absolute=proof_image_url_absolute,
        message="Comprobante subido. Pago en estado verificacion.",
    )


def list_workshop_commission_payments(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> CommissionPaymentListResponse:
    repository = CommissionRepository(db)

    payments = repository.list_commission_payments_for_workshop(taller_id)

    workshop = repository.get_workshop_by_id(taller_id)
    workshop_name = workshop.nombre if workshop else f"Taller #{taller_id}"

    items: list[CommissionPaymentListItemResponse] = []
    for payment in payments:
        proof_url = payment.proof_image_url
        proof_url_absolute = (
            resolve_absolute_url(base_url, proof_url) if proof_url else None
        )

        items.append(
            CommissionPaymentListItemResponse(
                payment_id=payment.id,
                taller_id=payment.taller_id,
                taller_name=workshop_name,
                amount=float(payment.amount),
                status=payment.status,
                proof_image_url=proof_url,
                proof_image_url_absolute=proof_url_absolute,
                created_at=payment.created_at,
                confirmed_at=payment.confirmed_at,
            )
        )

    return CommissionPaymentListResponse(total=len(items), payments=items)


def list_all_commission_payments(
    *,
    base_url: str,
    db: Session,
) -> CommissionPaymentListResponse:
    repository = CommissionRepository(db)

    payments = repository.list_all_commission_payments()

    workshop_ids = {int(payment.taller_id) for payment in payments}
    workshops_by_id = {
        int(workshop.id): workshop
        for workshop in repository.list_workshops_by_ids(workshop_ids)
    }

    items: list[CommissionPaymentListItemResponse] = []
    for payment in payments:
        workshop = workshops_by_id.get(int(payment.taller_id))
        workshop_name = workshop.nombre if workshop else f"Taller #{payment.taller_id}"

        proof_url = payment.proof_image_url
        proof_url_absolute = (
            resolve_absolute_url(base_url, proof_url) if proof_url else None
        )

        items.append(
            CommissionPaymentListItemResponse(
                payment_id=payment.id,
                taller_id=payment.taller_id,
                taller_name=workshop_name,
                amount=float(payment.amount),
                status=payment.status,
                proof_image_url=proof_url,
                proof_image_url_absolute=proof_url_absolute,
                created_at=payment.created_at,
                confirmed_at=payment.confirmed_at,
            )
        )

    return CommissionPaymentListResponse(total=len(items), payments=items)


def confirm_commission_payment(
    payload: CommissionPaymentConfirmRequest,
    *,
    db: Session,
) -> CommissionPaymentConfirmResponse:
    repository = CommissionRepository(db)

    payment = repository.get_commission_payment_by_id(payload.payment_id)
    if not payment:
        raise CommissionPaymentNotFoundError("Pago de comision no encontrado.")

    if payment.status == COMMISSION_STATUS_CONFIRMED:
        return CommissionPaymentConfirmResponse(
            payment_id=payment.id,
            taller_id=payment.taller_id,
            status=payment.status,
            message="El pago ya estaba confirmado.",
        )

    if payment.status != COMMISSION_STATUS_VERIFICATION:
        raise InvalidCommissionPaymentStateError(
            "Solo se puede confirmar un pago en estado verificacion."
        )

    try:
        repository.update_commission_payment(
            payment,
            status=COMMISSION_STATUS_CONFIRMED,
            confirmed_at=datetime.now(timezone.utc),
        )

        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommissionPaymentConfirmResponse(
        payment_id=payment.id,
        taller_id=payment.taller_id,
        status=payment.status,
        message="Pago de comision confirmado correctamente.",
    )


def reject_commission_payment(
    payload: CommissionPaymentRejectRequest,
    *,
    db: Session,
) -> CommissionPaymentRejectResponse:
    repository = CommissionRepository(db)

    payment = repository.get_commission_payment_by_id(payload.payment_id)
    if not payment:
        raise CommissionPaymentNotFoundError("Pago de comision no encontrado.")

    if payment.status == COMMISSION_STATUS_REJECTED:
        return CommissionPaymentRejectResponse(
            payment_id=payment.id,
            taller_id=payment.taller_id,
            status=payment.status,
            message="El pago ya estaba rechazado.",
        )

    if payment.status == COMMISSION_STATUS_CONFIRMED:
        raise InvalidCommissionPaymentStateError(
            "No se puede rechazar un pago ya confirmado."
        )

    if payment.status != COMMISSION_STATUS_VERIFICATION:
        raise InvalidCommissionPaymentStateError(
            "Solo se puede rechazar un pago en estado verificacion."
        )

    try:
        repository.update_commission_payment(
            payment,
            status=COMMISSION_STATUS_REJECTED,
        )

        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return CommissionPaymentRejectResponse(
        payment_id=payment.id,
        taller_id=payment.taller_id,
        status=payment.status,
        message="Pago de comision rechazado.",
    )
