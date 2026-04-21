from uuid import uuid4
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.payment_storage import (
    build_payment_proof_urls,
    resolve_absolute_url,
    safe_proof_file_extension,
    save_payment_proof_image,
)
from app.models.payment_schemas import (
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListItemResponse,
    PaymentListResponse,
    PaymentUploadProofResponse,
)
from app.repositories.payment_repository import PaymentRepository

PLATFORM_COMMISSION_RATE = 0.10

PAYMENT_STATUS_PENDING = "pendiente"
PAYMENT_STATUS_VERIFICATION = "verificacion"
PAYMENT_STATUS_CONFIRMED = "confirmado"


class IncidentNotOwnedError(Exception):
    pass


class IncidentNotFoundError(Exception):
    pass


class IncidentWithoutWorkshopError(Exception):
    pass


class WorkshopQrNotConfiguredError(Exception):
    pass


class PaymentAlreadyExistsError(Exception):
    pass


class PaymentNotFoundError(Exception):
    pass


class InvalidPaymentStateError(Exception):
    pass


def _calculate_commission(amount: float) -> float:
    return round(float(amount) * PLATFORM_COMMISSION_RATE, 2)


def _build_payment_reference(*, incident_id: int, payment_id: int) -> str:
    return f"INC-{incident_id}-PAY-{payment_id}"


def _resolve_workshop_account(*, taller_id: int, requested_account: str | None) -> str:
    if requested_account:
        return requested_account
    return f"TALLER-{taller_id:06d}"


def _serialize_qr_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def create_payment(
    payload: PaymentCreateRequest,
    *,
    user_id: int,
    base_url: str,
    db: Session,
) -> PaymentCreateResponse:
    repository = PaymentRepository(db)

    incident = repository.get_incident_for_client(payload.incident_id, user_id)
    if not incident:
        raise IncidentNotOwnedError("Incidente no encontrado para el cliente autenticado.")

    if incident.taller_id is None:
        raise IncidentWithoutWorkshopError(
            "El incidente aun no tiene taller asignado para recibir el pago."
        )

    workshop = repository.get_workshop_by_id(incident.taller_id)
    if not workshop:
        raise IncidentWithoutWorkshopError("No se encontro el taller asociado al incidente.")

    workshop_qr_url = (workshop.qr_image_url or "").strip() if workshop.qr_image_url else ""
    if not workshop_qr_url:
        raise WorkshopQrNotConfiguredError(
            "El taller no tiene QR configurado. No se puede crear el pago."
        )

    existing_payment = repository.get_payment_by_incident(incident.id)
    if existing_payment:
        raise PaymentAlreadyExistsError("Ya existe un pago creado para este incidente.")

    amount = round(float(payload.amount), 2)
    commission = _calculate_commission(amount)

    try:
        payment = repository.create_payment(
            incident_id=incident.id,
            user_id=user_id,
            taller_id=incident.taller_id,
            amount=amount,
            commission=commission,
            status=PAYMENT_STATUS_PENDING,
        )

        reference = _build_payment_reference(incident_id=incident.id, payment_id=payment.id)
        workshop_account = _resolve_workshop_account(
            taller_id=incident.taller_id,
            requested_account=payload.workshop_account,
        )

        qr_payload_dict: dict[str, object] = {
            "amount": amount,
            "workshop_account": workshop_account,
            "reference": reference,
            "incident_id": incident.id,
            "payment_id": payment.id,
        }

        qr_image_url = workshop_qr_url
        qr_image_url_absolute = resolve_absolute_url(base_url, workshop_qr_url)

        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=incident.cliente_id,
            accion="pago_creado",
            descripcion=(
                f"Cliente {user_id} creo pago QR {payment.id} por monto {amount}. "
                f"Comision plataforma {commission}."
            ),
            actor_usuario_id=user_id,
        )

        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return PaymentCreateResponse(
        payment_id=payment.id,
        incident_id=payment.incident_id,
        user_id=payment.user_id,
        taller_id=payment.taller_id,
        amount=float(payment.amount),
        commission=float(payment.commission),
        status=payment.status,
        reference=reference,
        workshop_account=workshop_account,
        qr_payload=_serialize_qr_payload(qr_payload_dict),
        qr_image_url=qr_image_url,
        qr_image_url_absolute=qr_image_url_absolute,
        created_at=payment.created_at,
        message="Pago QR creado correctamente.",
    )


def upload_payment_proof(
    *,
    payment_id: int,
    user_id: int,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> PaymentUploadProofResponse:
    repository = PaymentRepository(db)

    payment = repository.get_payment_for_client(payment_id, user_id)
    if not payment:
        raise PaymentNotFoundError("Pago no encontrado para el cliente autenticado.")

    if payment.status == PAYMENT_STATUS_CONFIRMED:
        raise InvalidPaymentStateError("El pago ya fue confirmado y no admite nuevos comprobantes.")

    if not file_bytes:
        raise InvalidPaymentStateError("El comprobante recibido esta vacio.")

    extension = safe_proof_file_extension(original_file_name, content_type)
    proof_file_name = f"payment_proof_{payment.id}_{uuid4().hex}{extension}"
    save_payment_proof_image(file_bytes, proof_file_name)
    proof_image_url, proof_image_url_absolute = build_payment_proof_urls(base_url, proof_file_name)

    try:
        repository.update_payment(
            payment,
            proof_image_url=proof_image_url,
            status=PAYMENT_STATUS_VERIFICATION,
        )

        repository.create_history(
            incidente_id=payment.incident_id,
            taller_id=payment.taller_id,
            cliente_id=payment.user_id,
            accion="comprobante_subido",
            descripcion=f"Cliente {user_id} subio comprobante para pago {payment.id}.",
            actor_usuario_id=user_id,
        )

        db.commit()
        db.refresh(payment)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return PaymentUploadProofResponse(
        payment_id=payment.id,
        status=payment.status,
        proof_image_url=proof_image_url,
        proof_image_url_absolute=proof_image_url_absolute,
        message="Comprobante subido. Pago en estado verificacion.",
    )


def confirm_payment(
    payload: PaymentConfirmRequest,
    *,
    taller_id: int,
    db: Session,
) -> PaymentConfirmResponse:
    repository = PaymentRepository(db)

    payment = repository.get_payment_for_workshop(payload.payment_id, taller_id)
    if not payment:
        raise PaymentNotFoundError("Pago no encontrado para el taller autenticado.")

    incident = repository.get_incident_by_id(payment.incident_id)
    if not incident:
        raise IncidentNotFoundError("Incidente asociado al pago no encontrado.")

    if payment.status == PAYMENT_STATUS_CONFIRMED:
        return PaymentConfirmResponse(
            payment_id=payment.id,
            incident_id=payment.incident_id,
            status=payment.status,
            incident_status=repository.get_service_state_name(incident.estado_servicio_id),
            message="El pago ya estaba confirmado.",
        )

    if payment.status != PAYMENT_STATUS_VERIFICATION:
        raise InvalidPaymentStateError(
            "Solo se puede confirmar un pago en estado verificacion."
        )

    try:
        attended_state = repository.get_or_create_service_state(
            name="atendido",
            description="Incidente atendido tras confirmacion de pago por el taller.",
        )

        repository.update_payment(payment, status=PAYMENT_STATUS_CONFIRMED)
        repository.update_incident(incident, estado_servicio_id=attended_state.id)

        repository.create_history(
            incidente_id=payment.incident_id,
            taller_id=payment.taller_id,
            cliente_id=payment.user_id,
            accion="pago_confirmado",
            descripcion=f"Taller {taller_id} confirmo pago {payment.id}.",
            actor_usuario_id=taller_id,
        )
        repository.create_history(
            incidente_id=payment.incident_id,
            taller_id=payment.taller_id,
            cliente_id=payment.user_id,
            accion="incidente_atendido_por_pago",
            descripcion=(
                f"Pago {payment.id} confirmado. Estado del incidente actualizado a atendido."
            ),
            actor_usuario_id=taller_id,
        )

        db.commit()
        db.refresh(payment)
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return PaymentConfirmResponse(
        payment_id=payment.id,
        incident_id=payment.incident_id,
        status=payment.status,
        incident_status=repository.get_service_state_name(incident.estado_servicio_id),
        message="Pago confirmado e incidente actualizado a atendido.",
    )


def list_workshop_payments(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> PaymentListResponse:
    repository = PaymentRepository(db)
    payments = repository.list_payments_for_workshop(taller_id)

    items: list[PaymentListItemResponse] = []
    for payment in payments:
        proof_url = payment.proof_image_url
        proof_url_absolute = (
            resolve_absolute_url(base_url, proof_url) if proof_url else None
        )
        items.append(
            PaymentListItemResponse(
                payment_id=payment.id,
                incident_id=payment.incident_id,
                user_id=payment.user_id,
                taller_id=payment.taller_id,
                amount=float(payment.amount),
                commission=float(payment.commission),
                status=payment.status,
                proof_image_url=proof_url,
                proof_image_url_absolute=proof_url_absolute,
                created_at=payment.created_at,
            )
        )

    return PaymentListResponse(total=len(items), payments=items)
