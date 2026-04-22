from uuid import uuid4
import json
from datetime import datetime, timezone
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.payment_storage import (
    build_payment_proof_urls,
    resolve_absolute_url,
    safe_proof_file_extension,
    save_payment_proof_image,
)
from app.models.payment_schemas import (
    PaymentAdminSummaryResponse,
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListItemResponse,
    PaymentListResponse,
    PaymentRejectRequest,
    PaymentRejectResponse,
    PaymentWorkshopSummaryItemResponse,
    PaymentUploadProofResponse,
)
from app.repositories.payment_repository import PaymentRepository

PLATFORM_COMMISSION_RATE = 0.10

PAYMENT_STATUS_PENDING = "pendiente"
PAYMENT_STATUS_VERIFICATION = "verificacion"
PAYMENT_STATUS_CONFIRMED = "confirmado"
PAYMENT_STATUS_REJECTED = "rechazado"

logger = logging.getLogger(__name__)


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


def _build_payment_list_item(
    *,
    payment,
    base_url: str,
    user_name: str | None,
    workshop_name: str | None,
) -> PaymentListItemResponse:
    amount = float(payment.amount)
    commission = float(payment.commission)
    proof_url = payment.proof_image_url
    proof_url_absolute = resolve_absolute_url(base_url, proof_url) if proof_url else None

    return PaymentListItemResponse(
        payment_id=payment.id,
        incident_id=payment.incident_id,
        user_id=payment.user_id,
        user_name=user_name,
        taller_id=payment.taller_id,
        taller_name=workshop_name,
        amount=amount,
        commission=commission,
        net_amount_to_workshop=round(amount - commission, 2),
        status=payment.status,
        reference=_build_payment_reference(incident_id=payment.incident_id, payment_id=payment.id),
        proof_image_url=proof_url,
        proof_image_url_absolute=proof_url_absolute,
        created_at=payment.created_at,
    )


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


def reject_payment(
    payload: PaymentRejectRequest,
    *,
    taller_id: int,
    db: Session,
) -> PaymentRejectResponse:
    repository = PaymentRepository(db)

    payment = repository.get_payment_for_workshop(payload.payment_id, taller_id)
    if not payment:
        raise PaymentNotFoundError("Pago no encontrado para el taller autenticado.")

    incident = repository.get_incident_by_id(payment.incident_id)
    if not incident:
        raise IncidentNotFoundError("Incidente asociado al pago no encontrado.")

    if payment.status == PAYMENT_STATUS_REJECTED:
        return PaymentRejectResponse(
            payment_id=payment.id,
            incident_id=payment.incident_id,
            status=payment.status,
            incident_status=repository.get_service_state_name(incident.estado_servicio_id),
            message="El pago ya estaba rechazado.",
        )

    if payment.status == PAYMENT_STATUS_CONFIRMED:
        raise InvalidPaymentStateError("No se puede rechazar un pago ya confirmado.")

    if payment.status != PAYMENT_STATUS_VERIFICATION:
        raise InvalidPaymentStateError(
            "Solo se puede rechazar un pago en estado verificacion."
        )

    reason_suffix = f" Motivo: {payload.reason}." if payload.reason else ""

    try:
        repository.update_payment(payment, status=PAYMENT_STATUS_REJECTED)

        repository.create_history(
            incidente_id=payment.incident_id,
            taller_id=payment.taller_id,
            cliente_id=payment.user_id,
            accion="pago_rechazado",
            descripcion=(
                f"Taller {taller_id} rechazo pago {payment.id}."
                f"{reason_suffix}"
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

    return PaymentRejectResponse(
        payment_id=payment.id,
        incident_id=payment.incident_id,
        status=payment.status,
        incident_status=repository.get_service_state_name(incident.estado_servicio_id),
        message="Pago rechazado por el taller.",
    )


def list_workshop_payments(
    *,
    taller_id: int,
    base_url: str,
    db: Session,
) -> PaymentListResponse:
    repository = PaymentRepository(db)
    payments = repository.list_payments_for_workshop(taller_id)

    user_ids = {int(payment.user_id) for payment in payments}
    workshop_ids = {int(payment.taller_id) for payment in payments}

    users_by_id = {int(user.id): user for user in repository.list_users_by_ids(user_ids)}
    workshops_by_id = {int(workshop.id): workshop for workshop in repository.list_workshops_by_ids(workshop_ids)}

    items: list[PaymentListItemResponse] = []
    for payment in payments:
        user = users_by_id.get(int(payment.user_id))
        workshop = workshops_by_id.get(int(payment.taller_id))
        items.append(
            _build_payment_list_item(
                payment=payment,
                base_url=base_url,
                user_name=user.nombre if user else None,
                workshop_name=workshop.nombre if workshop else None,
            )
        )

    return PaymentListResponse(total=len(items), payments=items)


def list_admin_payment_summary(
    *,
    base_url: str,
    db: Session,
) -> PaymentAdminSummaryResponse:
    start_ts = datetime.now(timezone.utc)
    repository = PaymentRepository(db)
    logger.info("list_admin_payment_summary: inicio de petición admin summary")
    payments = repository.list_all_payments()
    mid_ts = datetime.now(timezone.utc)
    logger.info(
        "list_admin_payment_summary: cargados %d pagos en %s",
        len(payments),
        str(mid_ts - start_ts),
    )

    user_ids = {int(payment.user_id) for payment in payments}
    workshop_ids = {int(payment.taller_id) for payment in payments}

    users_by_id = {int(user.id): user for user in repository.list_users_by_ids(user_ids)}
    workshops_by_id = {int(workshop.id): workshop for workshop in repository.list_workshops_by_ids(workshop_ids)}

    payment_items: list[PaymentListItemResponse] = []
    workshop_accumulator: dict[int, dict[str, float | int | str]] = {}

    total_amount = 0.0
    total_commission = 0.0
    total_net = 0.0
    total_confirmed = 0
    total_pending = 0
    total_verification = 0
    total_rejected = 0

    for payment in payments:
        user = users_by_id.get(int(payment.user_id))
        workshop = workshops_by_id.get(int(payment.taller_id))

        item = _build_payment_list_item(
            payment=payment,
            base_url=base_url,
            user_name=user.nombre if user else None,
            workshop_name=workshop.nombre if workshop else None,
        )
        payment_items.append(item)

        total_amount += item.amount
        total_commission += item.commission
        total_net += item.net_amount_to_workshop

        if item.status == PAYMENT_STATUS_CONFIRMED:
            total_confirmed += 1
        elif item.status == PAYMENT_STATUS_VERIFICATION:
            total_verification += 1
        elif item.status == PAYMENT_STATUS_REJECTED:
            total_rejected += 1
        else:
            total_pending += 1

        if item.taller_id not in workshop_accumulator:
            workshop_accumulator[item.taller_id] = {
                "taller_id": item.taller_id,
                "taller_name": item.taller_name or f"Taller #{item.taller_id}",
                "total_payments": 0,
                "confirmed_payments": 0,
                "pending_payments": 0,
                "verification_payments": 0,
                "rejected_payments": 0,
                "total_amount": 0.0,
                "total_commission": 0.0,
                "total_net_to_workshop": 0.0,
                "amount_due_to_platform": 0.0,
            }

        row = workshop_accumulator[item.taller_id]
        row["total_payments"] = int(row["total_payments"]) + 1
        row["total_amount"] = float(row["total_amount"]) + item.amount
        row["total_commission"] = float(row["total_commission"]) + item.commission
        row["total_net_to_workshop"] = float(row["total_net_to_workshop"]) + item.net_amount_to_workshop

        if item.status == PAYMENT_STATUS_CONFIRMED:
            row["confirmed_payments"] = int(row["confirmed_payments"]) + 1
            row["amount_due_to_platform"] = float(row["amount_due_to_platform"]) + item.commission
        elif item.status == PAYMENT_STATUS_VERIFICATION:
            row["verification_payments"] = int(row["verification_payments"]) + 1
        elif item.status == PAYMENT_STATUS_REJECTED:
            row["rejected_payments"] = int(row["rejected_payments"]) + 1
        else:
            row["pending_payments"] = int(row["pending_payments"]) + 1

    workshop_items = [
        PaymentWorkshopSummaryItemResponse(
            taller_id=int(data["taller_id"]),
            taller_name=str(data["taller_name"]),
            total_payments=int(data["total_payments"]),
            confirmed_payments=int(data["confirmed_payments"]),
            pending_payments=int(data["pending_payments"]),
            verification_payments=int(data["verification_payments"]),
            rejected_payments=int(data["rejected_payments"]),
            total_amount=round(float(data["total_amount"]), 2),
            total_commission=round(float(data["total_commission"]), 2),
            total_net_to_workshop=round(float(data["total_net_to_workshop"]), 2),
            amount_due_to_platform=round(float(data["amount_due_to_platform"]), 2),
        )
        for data in workshop_accumulator.values()
    ]
    workshop_items.sort(key=lambda item: item.amount_due_to_platform, reverse=True)

    return PaymentAdminSummaryResponse(
        generated_at=datetime.now(timezone.utc),
        total_payments=len(payment_items),
        confirmed_payments=total_confirmed,
        pending_payments=total_pending,
        verification_payments=total_verification,
        rejected_payments=total_rejected,
        total_amount=round(total_amount, 2),
        total_commission=round(total_commission, 2),
        total_net_to_workshop=round(total_net, 2),
        workshops=workshop_items,
        payments=payment_items,
    )
