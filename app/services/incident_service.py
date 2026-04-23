"""Servicio de negocio para incidentes (CU4, reenvio de evidencia y candidatos)."""

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.incident import Incidente
from app.models.incident_schemas import (
    ClientRequestItem,
    ClientIncidentHistoryItem,
    ClientIncidentHistoryResponse,
    WorkshopIncidentHistoryResponse,
    TechnicianIncidentHistoryResponse,
    ClientRequestsResponse,
    IncidentDetailResponse,
    IncidentCancelResponse,
    IncidentHistoryItem,
    IncidentCandidateSelectionRequest,
    IncidentCandidateSelectionResponse,
    IncidentCandidatesResponse,
    IncidentEvidenceResubmissionRequest,
    IncidentReportRequest,
    IncidentReportResponse,
    WorkshopEvidenceItem,
    WorkshopIncomingRequestItem,
    WorkshopIncomingRequestsResponse,
    WorkshopServiceCompletionRequest,
    WorkshopServiceCompletionResponse,
    WorkshopRequestDecisionRequest,
    WorkshopRequestDecisionResponse,
    TechnicianLocationUpdateRequest,
    TechnicianLocationUpdateResponse,
    TechnicianIncomingRequestItem,
    TechnicianIncomingRequestsResponse,
    TechnicianRequestRejectRequest,
    TechnicianRequestRejectResponse,
)
from app.repositories.incident_repository import IncidentRepository
from app.services.Cliente.push_service import send_client_push_best_effort
from app.services.Sistema.ai_incident_processor import AIIncidentProcessingResult, process_incident_payload_for_ai
from app.services.Sistema.workshop_assignment_service import build_incident_candidates


class VehicleNotOwnedError(Exception):
    # Error de dominio cuando el vehiculo no existe o no pertenece al cliente.
    pass


class LocationRequiredError(Exception):
    # Error de dominio cuando no se pudo obtener ubicacion para la solicitud.
    pass


class IncidentNotOwnedError(Exception):
    # Error cuando el incidente no existe o no pertenece al cliente autenticado.
    pass


class IncidentNeedsMoreEvidenceError(Exception):
    # Error cuando un incidente no puede pasar a matching por evidencia insuficiente.
    pass


class NoWorkshopCandidatesError(Exception):
    # Error cuando no hay talleres candidatos disponibles para el incidente.
    pass


class InvalidWorkshopSelectionError(Exception):
    # Error cuando la seleccion del cliente contiene talleres fuera de candidatos.
    pass


class WorkshopRequestNotFoundError(Exception):
    # Error cuando solicitud no existe o no pertenece al taller autenticado.
    pass


class WorkshopResourcesUnavailableError(Exception):
    # Error cuando no hay tecnico o transporte disponible para aceptar solicitud.
    pass


class WorkshopResourceSelectionError(Exception):
    # Error cuando la seleccion manual de recursos del taller es invalida.
    pass


class IncidentNotFoundError(Exception):
    # Error cuando no existe el incidente solicitado.
    pass


class WorkshopIncidentAccessDeniedError(Exception):
    # Error cuando el taller no tiene permiso para ver detalle del incidente.
    pass


class InvalidIncidentFinalizationError(Exception):
    # Error cuando no se puede cerrar el servicio por estado invalido.
    pass


class IncidentCancellationError(Exception):
    # Error cuando el cliente no puede cancelar el incidente por estado.
    pass


class TechnicianAccessDeniedError(Exception):
    # Error cuando el tecnico intenta operar solicitud no asignada a el.
    pass


MAX_INFO_RETRIES = 3


def _apply_information_policy(
    *,
    ai_result: AIIncidentProcessingResult,
    retries_count: int,
) -> tuple[bool, str | None]:
    # Si llega al maximo de reintentos, fuerza continuidad del flujo aunque falte evidencia.
    if ai_result.informacion_suficiente:
        return (True, ai_result.solicitud_mas_informacion)

    if retries_count >= MAX_INFO_RETRIES:
        return (
            True,
            "Se alcanzo el maximo de reintentos sin evidencia suficiente. El incidente continua con la informacion disponible.",
        )

    return (False, ai_result.solicitud_mas_informacion)


def _merge_location(ubicacion: str | None, referencia: str | None) -> str | None:
    # Une ubicacion y referencia opcional en un solo campo legible/auditable.
    merged_location = ubicacion
    if referencia:
        merged_location = (
            f"{merged_location} | Ref: {referencia}" if merged_location else f"Ref: {referencia}"
        )
    return merged_location


def _persist_incident_evidence(
    repository: IncidentRepository,
    *,
    incidente_id: int,
    image_url: str | None,
    audio_url: str | None,
    ai_result: AIIncidentProcessingResult,
) -> None:
    # Guarda evidencias multimodales y resumen de forma consistente
    if image_url or audio_url:
        evidence_type = "multimedia" if image_url and audio_url else ("imagen" if image_url else "audio")
        extracted_parts = [
            part
            for part in [
                f"Imagen: {ai_result.image_summary}" if ai_result.image_summary else None,
                f"Audio: {ai_result.audio_transcripcion}" if ai_result.audio_transcripcion else None,
            ]
            if part
        ]
        repository.create_evidence(
            incidente_id=incidente_id,
            tipo=evidence_type,
            url=image_url,
            url_audio=audio_url,
            texto_extraido="\n".join(extracted_parts) if extracted_parts else None,
        )

    if ai_result.texto_extraido:
        repository.create_evidence(
            incidente_id=incidente_id,
            tipo="texto",
            url=None,
            texto_extraido=ai_result.texto_extraido,
        )

    if ai_result.resumen_incidente:
        repository.create_evidence(
            incidente_id=incidente_id,
            tipo="resumen",
            url=None,
            texto_extraido=ai_result.resumen_incidente,
        )


def _build_incident_report_response(
    repository: IncidentRepository,
    *,
    incident: Incidente,
    ai_result: AIIncidentProcessingResult,
    effective_info_sufficient: bool,
    effective_detail: str | None,
    message: str,
) -> IncidentReportResponse:
    # Estandariza respuesta del incidente para reporte inicial y reenvio de evidencia.
    return IncidentReportResponse(
        incidente_id=incident.id,
        estado=repository.get_service_state_name(incident.estado_servicio_id),
        tipo_problema=incident.tipo_problema,
        prioridad=incident.prioridad,
        procesamiento_ia=ai_result.estado_procesamiento,
        informacion_suficiente=effective_info_sufficient,
        info_reintentos=incident.info_reintentos,
        solicitar_mas_informacion=not effective_info_sufficient,
        resumen_incidente=ai_result.resumen_incidente,
        detalle_solicitud_info=effective_detail,
        tipo_deducido_ia=ai_result.problem_deduced,
        audio_transcripcion_ia=ai_result.audio_transcripcion,
        resumen_imagen_ia=ai_result.image_summary,
        vehiculo_placa=incident.vehiculo_placa,
        fecha_hora=incident.fecha_hora,
        mensaje=message,
    )


def _build_metric_payload(metric) -> dict[str, float | int | str | None] | None:
    # Serializa metrica de servicio para respuestas API.
    if not metric:
        return None
    return {
        "tiempo_minutos": int(metric.tiempo_minutos),
        "costo_total": float(metric.costo_total),
        "comision_plataforma": float(metric.comision_plataforma),
        "distancia_km": float(metric.distancia_km) if metric.distancia_km is not None else None,
        "observaciones": metric.observaciones,
        "fecha_cierre": metric.fecha_cierre.isoformat() if metric.fecha_cierre else None,
    }


def _build_incident_history_item(
    repository: IncidentRepository,
    *,
    incident: Incidente,
    request_states: set[str],
    solicitud_id: int | None = None,
) -> ClientIncidentHistoryItem:
    # Construye un item uniforme de historial de incidentes para cualquier actor.
    metric = repository.get_metric_by_incident(incident.id)
    return ClientIncidentHistoryItem(
        incidente_id=incident.id,
        solicitud_id=solicitud_id,
        vehiculo_placa=incident.vehiculo_placa,
        tipo_problema=incident.tipo_problema,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        fecha_hora=incident.fecha_hora,
        estados_solicitud=sorted(request_states),
        metrica=_build_metric_payload(metric),
    )


def _build_incident_detail_response(
    repository: IncidentRepository,
    *,
    incident: Incidente,
) -> IncidentDetailResponse:
    # Construye vista completa del incidente para cliente o taller.
    vehicle = repository.get_vehicle_by_plate(incident.vehiculo_placa)
    evidences = repository.list_incident_evidence(incident.id)
    history = repository.list_incident_history(incident.id)
    assigned_request = repository.get_primary_assigned_request_for_incident(incident.id)
    metric = repository.get_metric_by_incident(incident.id)
    location_payload = _get_live_technician_location(
        tecnico_id=assigned_request.tecnico_id if assigned_request else None,
        solicitud_id=assigned_request.id if assigned_request else None,
        repository=repository,
    )

    return IncidentDetailResponse(
        incidente_id=incident.id,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        tipo_problema=incident.tipo_problema,
        prioridad=incident.prioridad,
        info_reintentos=incident.info_reintentos,
        cliente_id=incident.cliente_id,
        taller_asignado_id=incident.taller_id,
        solicitud_aceptada_id=assigned_request.id if assigned_request else None,
        tecnico_asignado_id=assigned_request.tecnico_id if assigned_request else None,
        transporte_asignado_id=assigned_request.transporte_id if assigned_request else None,
        tecnico_latitud=location_payload["latitud"],
        tecnico_longitud=location_payload["longitud"],
        tecnico_precision_metros=location_payload["precision_metros"],
        tecnico_ubicacion_actualizada_en=location_payload["actualizada_en"],
        vehiculo_placa=incident.vehiculo_placa,
        vehiculo_marca=vehicle.marca if vehicle else None,
        vehiculo_modelo=vehicle.modelo if vehicle else None,
        vehiculo_anio=vehicle.anio if vehicle else None,
        ubicacion=incident.ubicacion,
        latitud=incident.latitud,
        longitud=incident.longitud,
        descripcion=incident.descripcion,
        fecha_hora=incident.fecha_hora,
        metrica=_build_metric_payload(metric),
        evidencias=[
            WorkshopEvidenceItem(
                evidencia_id=evidence.id,
                tipo=evidence.tipo,
                url=evidence.url,
                url_audio=evidence.url_audio,
                texto_extraido=evidence.texto_extraido,
            )
            for evidence in evidences
        ],
        historial=[
            IncidentHistoryItem(
                historial_id=entry.id,
                accion=entry.accion,
                descripcion=entry.descripcion,
                fecha_hora=entry.fecha_hora,
                actor_usuario_id=entry.actor_usuario_id,
            )
            for entry in history
        ],
    )


def _get_live_technician_location(
    *,
    tecnico_id: int | None,
    solicitud_id: int | None,
    repository: IncidentRepository | None = None,
) -> dict[str, object]:
    # Recupera ubicacion reciente del tecnico desde cache y fallback persistido en DB.
    if tecnico_id is None:
        return {
            "latitud": None,
            "longitud": None,
            "precision_metros": None,
            "actualizada_en": None,
        }

    from app.services.Tecnico.location_cache import ACTIVE_TECHNICIAN_LOCATIONS

    memory_entry = ACTIVE_TECHNICIAN_LOCATIONS.get(tecnico_id)
    db_entry = repository.get_technician_location(tecnico_id) if repository else None

    entry = None
    if memory_entry and db_entry:
        memory_ts = memory_entry.actualizada_en.timestamp() if memory_entry.actualizada_en else 0.0
        db_ts = db_entry.actualizada_en.timestamp() if db_entry.actualizada_en else 0.0
        entry = memory_entry if memory_ts >= db_ts else db_entry
    elif memory_entry:
        entry = memory_entry
    elif db_entry:
        entry = db_entry
    if not entry:
        return {
            "latitud": None,
            "longitud": None,
            "precision_metros": None,
            "actualizada_en": None,
        }

    # Mostramos la última ubicación conocida del técnico aunque la solicitud
    # enviada por el cliente móvil no venga sincronizada con el id actual.
    _ = solicitud_id

    return {
        "latitud": float(entry.latitud),
        "longitud": float(entry.longitud),
        "precision_metros": float(entry.precision_metros) if entry.precision_metros is not None else None,
        "actualizada_en": entry.actualizada_en,
    }


def report_incident(
    data: IncidentReportRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentReportResponse:
    # Ejecuta flujo principal del CU4: validar, registrar e iniciar procesamiento.
    repository = IncidentRepository(db)

    if data.latitud is None or data.longitud is None:
        raise LocationRequiredError("No se pudo obtener la ubicacion del usuario.")

    vehicle = repository.get_vehicle_for_client(data.vehiculo_placa, cliente_id)
    if not vehicle:
        raise VehicleNotOwnedError(
            "El vehiculo no existe o no pertenece al cliente autenticado."
        )

    # Preprocesamiento IA previo a persistencia y despacho a talleres.
    ai_result = process_incident_payload_for_ai(
        image_url=data.imagen_url,
        audio_url=data.audio_url,
        user_text=data.texto_usuario,
    )

    retries_count = 1 if not ai_result.informacion_suficiente else 0
    effective_info_sufficient, effective_detail = _apply_information_policy(
        ai_result=ai_result,
        retries_count=retries_count,
    )

    if effective_info_sufficient:
        current_state = repository.get_or_create_service_state(
            name="pendiente",
            description="Incidente reportado pendiente de evaluacion.",
        )
    else:
        current_state = repository.get_or_create_service_state(
            name="requiere_info",
            description="Incidente incompleto. Se solicita mas informacion al cliente.",
        )

    merged_location = _merge_location(data.ubicacion, data.referencia)

    try:
        # Registramos el incidente base con la informacion enviada por app movil.
        incident = repository.create_incident(
            cliente_id=cliente_id,
            vehiculo_placa=data.vehiculo_placa,
            estado_servicio_id=current_state.id,
            tipo_problema=ai_result.tipo_problema,
            descripcion=data.texto_usuario,
            ubicacion=merged_location,
            latitud=data.latitud,
            longitud=data.longitud,
            prioridad=ai_result.prioridad,
            info_reintentos=retries_count,
        )

        _persist_incident_evidence(
            repository,
            incidente_id=incident.id,
            image_url=data.imagen_url,
            audio_url=data.audio_url,
            ai_result=ai_result,
        )

        # Trazabilidad del flujo: reporte recibido y procesamiento iniciado.
        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="incidente_reportado",
            descripcion="Cliente reporto emergencia desde app movil.",
            actor_usuario_id=cliente_id,
        )
        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="ia_preprocesamiento",
            descripcion=(
                "Preprocesamiento IA ejecutado. "
                f"estado={ai_result.estado_procesamiento}, "
                f"tipo_problema={ai_result.tipo_problema}, "
                f"prioridad={ai_result.prioridad}, "
                f"informacion_suficiente={effective_info_sufficient}, "
                f"reintentos={retries_count}."
            ),
            actor_usuario_id=cliente_id,
        )

        if not effective_info_sufficient and effective_detail:
            repository.create_history(
                incidente_id=incident.id,
                taller_id=incident.taller_id,
                cliente_id=cliente_id,
                accion="solicitar_mas_info",
                descripcion=effective_detail,
                actor_usuario_id=cliente_id,
            )
        elif effective_info_sufficient and retries_count >= MAX_INFO_RETRIES:
            repository.create_history(
                incidente_id=incident.id,
                taller_id=incident.taller_id,
                cliente_id=cliente_id,
                accion="maximo_reintentos_alcanzado",
                descripcion=effective_detail or "Se continua con informacion parcial.",
                actor_usuario_id=cliente_id,
            )
        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="procesamiento_iniciado",
            descripcion="Se inicia procesamiento inicial de clasificacion del incidente.",
            actor_usuario_id=cliente_id,
        )

        db.commit()
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    response_message = "Incidente registrado y procesamiento iniciado."
    if not effective_info_sufficient:
        response_message = (
            "Incidente registrado parcialmente. Se requiere mas informacion para enviarlo a talleres."
        )

    return _build_incident_report_response(
        repository,
        incident=incident,
        ai_result=ai_result,
        effective_info_sufficient=effective_info_sufficient,
        effective_detail=effective_detail,
        message=response_message,
    )


def resubmit_incident_evidence(
    incidente_id: int,
    data: IncidentEvidenceResubmissionRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentReportResponse:
    # Reprocesa incidente en estado requiere_info con evidencia adicional del cliente.
    repository = IncidentRepository(db)

    incident = repository.get_incident_for_client(incidente_id, cliente_id)
    if not incident:
        raise IncidentNotOwnedError("Incidente no encontrado para el cliente autenticado.")

    merged_text = data.texto_usuario or incident.descripcion

    ai_result = process_incident_payload_for_ai(
        image_url=data.imagen_url,
        audio_url=data.audio_url,
        user_text=merged_text,
    )

    retries_count = incident.info_reintentos + (0 if ai_result.informacion_suficiente else 1)
    effective_info_sufficient, effective_detail = _apply_information_policy(
        ai_result=ai_result,
        retries_count=retries_count,
    )

    if effective_info_sufficient:
        current_state = repository.get_or_create_service_state(
            name="pendiente",
            description="Incidente listo para evaluacion de talleres.",
        )
        response_message = "Evidencia actualizada. El incidente ya puede pasar a fase de candidatos."
    else:
        current_state = repository.get_or_create_service_state(
            name="requiere_info",
            description="Incidente incompleto. Se solicita mas informacion al cliente.",
        )
        response_message = "Evidencia recibida, pero aun se requiere informacion adicional."

    updated_location = data.ubicacion if data.ubicacion is not None else incident.ubicacion
    updated_location = _merge_location(updated_location, data.referencia)

    updated_lat = data.latitud if data.latitud is not None else incident.latitud
    updated_lon = data.longitud if data.longitud is not None else incident.longitud

    try:
        repository.update_incident(
            incident,
            estado_servicio_id=current_state.id,
            tipo_problema=ai_result.tipo_problema,
            prioridad=ai_result.prioridad,
            info_reintentos=retries_count,
            descripcion=merged_text,
            ubicacion=updated_location,
            latitud=updated_lat,
            longitud=updated_lon,
        )

        _persist_incident_evidence(
            repository,
            incidente_id=incident.id,
            image_url=data.imagen_url,
            audio_url=data.audio_url,
            ai_result=ai_result,
        )

        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="evidencia_reenviada",
            descripcion="Cliente reenvio evidencia para completar informacion del incidente.",
            actor_usuario_id=cliente_id,
        )
        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="ia_reprocesamiento",
            descripcion=(
                "Reprocesamiento IA ejecutado. "
                f"estado={ai_result.estado_procesamiento}, "
                f"tipo_problema={ai_result.tipo_problema}, "
                f"prioridad={ai_result.prioridad}, "
                f"informacion_suficiente={effective_info_sufficient}, "
                f"reintentos={retries_count}."
            ),
            actor_usuario_id=cliente_id,
        )

        if not effective_info_sufficient and effective_detail:
            repository.create_history(
                incidente_id=incident.id,
                taller_id=incident.taller_id,
                cliente_id=cliente_id,
                accion="solicitar_mas_info",
                descripcion=effective_detail,
                actor_usuario_id=cliente_id,
            )
        elif effective_info_sufficient and retries_count >= MAX_INFO_RETRIES:
            repository.create_history(
                incidente_id=incident.id,
                taller_id=incident.taller_id,
                cliente_id=cliente_id,
                accion="maximo_reintentos_alcanzado",
                descripcion=effective_detail or "Se continua con informacion parcial.",
                actor_usuario_id=cliente_id,
            )

        db.commit()
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return _build_incident_report_response(
        repository,
        incident=incident,
        ai_result=ai_result,
        effective_info_sufficient=effective_info_sufficient,
        effective_detail=effective_detail,
        message=response_message,
    )


def list_workshop_candidates(
    incidente_id: int,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentCandidatesResponse:
    # Genera la lista de talleres candidatos para que el cliente marque/desmarque.
    repository = IncidentRepository(db)

    incident = repository.get_incident_for_client(incidente_id, cliente_id)
    if not incident:
        raise IncidentNotOwnedError("Incidente no encontrado para el cliente autenticado.")

    incident_state = repository.get_service_state_name(incident.estado_servicio_id)
    if incident_state == "requiere_info":
        raise IncidentNeedsMoreEvidenceError(
            "El incidente aun requiere informacion adicional antes de evaluar talleres."
        )

    workshop_rows = repository.list_active_workshops_with_context()
    candidates = build_incident_candidates(incident=incident, workshop_rows=workshop_rows)

    if not candidates:
        raise NoWorkshopCandidatesError("No hay talleres candidatos disponibles en este momento.")

    return IncidentCandidatesResponse(
        incidente_id=incident.id,
        tipo_problema=incident.tipo_problema,
        prioridad=incident.prioridad,
        total_candidatos=len(candidates),
        candidatos=candidates,
    )


def select_workshops_for_incident(
    incidente_id: int,
    data: IncidentCandidateSelectionRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentCandidateSelectionResponse:
    # Crea solicitudes para los talleres elegidos por el cliente desde fase de candidatos.
    repository = IncidentRepository(db)

    incident = repository.get_incident_for_client(incidente_id, cliente_id)
    if not incident:
        raise IncidentNotOwnedError("Incidente no encontrado para el cliente autenticado.")

    incident_state = repository.get_service_state_name(incident.estado_servicio_id)
    if incident_state == "requiere_info":
        raise IncidentNeedsMoreEvidenceError(
            "No se puede enviar a talleres: el incidente aun requiere mas evidencia."
        )

    workshop_rows = repository.list_active_workshops_with_context()
    candidates = build_incident_candidates(incident=incident, workshop_rows=workshop_rows)
    allowed_workshop_ids = {candidate.taller_id for candidate in candidates}

    invalid_selection = [workshop_id for workshop_id in data.talleres_ids if workshop_id not in allowed_workshop_ids]
    if invalid_selection:
        raise InvalidWorkshopSelectionError(
            "La seleccion contiene talleres que no forman parte de los candidatos vigentes."
        )

    sent_requests: list[int] = []
    try:
        for workshop_id in data.talleres_ids:
            existing = repository.get_existing_active_request(
                incidente_id=incident.id,
                taller_id=workshop_id,
            )
            if existing:
                continue

            repository.create_request_to_workshop(
                incidente_id=incident.id,
                taller_id=workshop_id,
                estado="enviada",
            )
            sent_requests.append(workshop_id)
            repository.create_history(
                incidente_id=incident.id,
                taller_id=workshop_id,
                cliente_id=cliente_id,
                accion="solicitud_enviada_taller",
                descripcion=f"Cliente envio solicitud al taller {workshop_id}.",
                actor_usuario_id=cliente_id,
            )

        in_progress_state = repository.get_or_create_service_state(
            name="en_proceso",
            description="Solicitud enviada a talleres seleccionados por el cliente.",
        )
        repository.update_incident(incident, estado_servicio_id=in_progress_state.id)

        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="talleres_seleccionados",
            descripcion=f"Cliente selecciono talleres: {data.talleres_ids}",
            actor_usuario_id=cliente_id,
        )
        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="solicitudes_enviadas",
            descripcion=f"Solicitudes enviadas a talleres: {sent_requests}",
            actor_usuario_id=cliente_id,
        )

        db.commit()
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return IncidentCandidateSelectionResponse(
        incidente_id=incident.id,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        solicitudes_enviadas=len(sent_requests),
        talleres_enviados=sent_requests,
        mensaje="Solicitudes enviadas a talleres seleccionados.",
    )


def list_client_requests(
    *,
    cliente_id: int,
    db: Session,
) -> ClientRequestsResponse:
    # Permite al cliente ver todas sus solicitudes y estado actual.
    repository = IncidentRepository(db)
    rows = repository.list_client_requests(cliente_id)

    items: list[ClientRequestItem] = []
    for row in rows:
        solicitud = row["solicitud"]
        incidente = row["incidente"]
        metric = repository.get_metric_by_incident(incidente.id)
        metric_payload = None
        if metric and metric.solicitud_id == solicitud.id:
            metric_payload = _build_metric_payload(metric)
        location_payload = _get_live_technician_location(
            tecnico_id=solicitud.tecnico_id,
            solicitud_id=solicitud.id,
            repository=repository,
        )
        items.append(
            ClientRequestItem(
                solicitud_id=solicitud.id,
                incidente_id=incidente.id,
                taller_id=solicitud.taller_id,
                nombre_taller=row.get("taller_nombre"),
                estado_solicitud=solicitud.estado,
                estado_incidente=repository.get_service_state_name(incidente.estado_servicio_id),
                tipo_problema=incidente.tipo_problema,
                prioridad=incidente.prioridad,
                fecha_asignacion=solicitud.fecha_asignacion,
                tecnico_id=solicitud.tecnico_id,
                tecnico_latitud=location_payload["latitud"],
                tecnico_longitud=location_payload["longitud"],
                tecnico_precision_metros=location_payload["precision_metros"],
                tecnico_ubicacion_actualizada_en=location_payload["actualizada_en"],
                metrica=metric_payload,
            )
        )

    return ClientRequestsResponse(total=len(items), solicitudes=items)


def list_workshop_incoming_requests(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopIncomingRequestsResponse:
    # Entrega al taller toda la informacion necesaria del incidente para decidir.
    repository = IncidentRepository(db)
    rows = repository.list_incoming_requests_for_workshop(taller_id)

    items: list[WorkshopIncomingRequestItem] = []
    for row in rows:
        solicitud = row["solicitud"]
        incidente = row["incidente"]
        vehiculo = row["vehiculo"]
        evidencias = repository.list_incident_evidence(incidente.id)
        location_payload = _get_live_technician_location(
            tecnico_id=solicitud.tecnico_id,
            solicitud_id=solicitud.id,
            repository=repository,
        )

        items.append(
            WorkshopIncomingRequestItem(
                solicitud_id=solicitud.id,
                incidente_id=incidente.id,
                estado_solicitud=solicitud.estado,
                estado_incidente=repository.get_service_state_name(incidente.estado_servicio_id),
                tipo_problema=incidente.tipo_problema,
                prioridad=incidente.prioridad,
                ubicacion=incidente.ubicacion,
                latitud=incidente.latitud,
                longitud=incidente.longitud,
                vehiculo_placa=vehiculo.placa,
                vehiculo_marca=vehiculo.marca,
                vehiculo_modelo=vehiculo.modelo,
                vehiculo_anio=vehiculo.anio,
                cliente_id=incidente.cliente_id,
                fecha_asignacion=solicitud.fecha_asignacion,
                evidencias=[
                    WorkshopEvidenceItem(
                        evidencia_id=evidence.id,
                        tipo=evidence.tipo,
                        url=evidence.url,
                        url_audio=evidence.url_audio,
                        texto_extraido=evidence.texto_extraido,
                    )
                    for evidence in evidencias
                ],
                tecnico_id=solicitud.tecnico_id,
                tecnico_latitud=location_payload["latitud"],
                tecnico_longitud=location_payload["longitud"],
                tecnico_precision_metros=location_payload["precision_metros"],
                tecnico_ubicacion_actualizada_en=location_payload["actualizada_en"],
            )
        )

    return WorkshopIncomingRequestsResponse(total=len(items), solicitudes=items)


def decide_workshop_request(
    solicitud_id: int,
    data: WorkshopRequestDecisionRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopRequestDecisionResponse:
    # Taller acepta/rechaza; solo el primero en aceptar queda valido.
    repository = IncidentRepository(db)

    request = repository.get_request_for_workshop(solicitud_id, taller_id)
    if not request:
        raise WorkshopRequestNotFoundError("Solicitud no encontrada para el taller autenticado.")

    incident = repository.get_incident_by_id(request.incidente_id)
    if not incident:
        raise WorkshopRequestNotFoundError("Incidente asociado no encontrado.")

    # Estado terminal idempotente.
    if request.estado in {"aceptada", "rechazada", "otro_taller_acepto", "finalizada"}:
        return WorkshopRequestDecisionResponse(
            solicitud_id=request.id,
            incidente_id=incident.id,
            estado_solicitud=request.estado,
            estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
            tecnico_id=request.tecnico_id,
            transporte_id=request.transporte_id,
            mensaje="La solicitud ya fue procesada previamente.",
        )

    try:
        if data.accion == "rechazar":
            repository.update_request(
                request,
                estado="rechazada",
                comentario=data.comentario,
            )
            repository.create_history(
                incidente_id=incident.id,
                taller_id=taller_id,
                cliente_id=incident.cliente_id,
                accion="solicitud_rechazada",
                descripcion=f"Taller {taller_id} rechazo solicitud {request.id}.",
                actor_usuario_id=taller_id,
            )

            db.commit()
            db.refresh(request)
            db.refresh(incident)

            send_client_push_best_effort(
                cliente_id=incident.cliente_id,
                titulo="Tu solicitud fue rechazada",
                cuerpo="Un taller rechazó tu solicitud. Seguiremos intentando con otras opciones.",
                data={
                    "evento": "solicitud_rechazada_taller",
                    "solicitud_id": str(request.id),
                    "incidente_id": str(incident.id),
                    "estado_solicitud": str(request.estado),
                    "estado_incidente": repository.get_service_state_name(incident.estado_servicio_id),
                },
                db=db,
            )

            return WorkshopRequestDecisionResponse(
                solicitud_id=request.id,
                incidente_id=incident.id,
                estado_solicitud=request.estado,
                estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
                tecnico_id=request.tecnico_id,
                transporte_id=request.transporte_id,
                mensaje="Solicitud rechazada por el taller.",
            )

        # accion=aceptar
        if incident.taller_id and incident.taller_id != taller_id:
            repository.update_request(
                request,
                estado="otro_taller_acepto",
                comentario="Solicitud invalidada: otro taller acepto primero.",
            )
            repository.create_history(
                incidente_id=incident.id,
                taller_id=taller_id,
                cliente_id=incident.cliente_id,
                accion="solicitud_invalidada",
                descripcion=f"Solicitud {request.id} invalidada porque otro taller acepto primero.",
                actor_usuario_id=taller_id,
            )
            db.commit()
            db.refresh(request)
            db.refresh(incident)
            return WorkshopRequestDecisionResponse(
                solicitud_id=request.id,
                incidente_id=incident.id,
                estado_solicitud=request.estado,
                estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
                tecnico_id=request.tecnico_id,
                transporte_id=request.transporte_id,
                mensaje="Otro taller acepto primero; esta solicitud queda invalidada.",
            )

        technician = repository.get_available_technician_for_workshop(taller_id)
        if not technician:
            raise WorkshopResourcesUnavailableError(
                "No hay tecnico disponible para aceptar la solicitud."
            )

        if data.transporte_id is None:
            raise WorkshopResourceSelectionError(
                "Debes seleccionar un transporte disponible para aceptar la solicitud."
            )

        transport = repository.get_transport_by_id(data.transporte_id)
        if not transport or transport.taller_id != taller_id:
            raise WorkshopResourceSelectionError(
                "El transporte seleccionado no pertenece a tu taller."
            )

        if transport.estado != "disponible":
            raise WorkshopResourcesUnavailableError(
                "El transporte seleccionado no esta disponible para aceptar la solicitud."
            )

        repository.update_technician_state(technician, "asignado")
        repository.update_transport_state(transport, "asignado")
        repository.update_request(
            request,
            estado="aceptada",
            tecnico_id=technician.id,
            transporte_id=transport.id,
            comentario=data.comentario,
        )

        in_progress_state = repository.get_or_create_service_state(
            name="en_proceso",
            description="Incidente aceptado por taller y en atencion.",
        )
        repository.update_incident(
            incident,
            taller_id=taller_id,
            estado_servicio_id=in_progress_state.id,
        )

        # Invalida solicitudes paralelas por regla primer-aceptacion.
        all_requests = repository.list_requests_for_incident(incident.id)
        for other_request in all_requests:
            if other_request.id == request.id:
                continue
            if other_request.estado in {"enviada", "pendiente"}:
                repository.update_request(
                    other_request,
                    estado="otro_taller_acepto",
                    comentario="Solicitud invalidada: otro taller acepto primero.",
                )
                repository.create_history(
                    incidente_id=incident.id,
                    taller_id=other_request.taller_id,
                    cliente_id=incident.cliente_id,
                    accion="solicitud_invalidada",
                    descripcion=(
                        f"Solicitud {other_request.id} invalidada: otro taller acepto primero."
                    ),
                    actor_usuario_id=taller_id,
                )

        repository.create_history(
            incidente_id=incident.id,
            taller_id=taller_id,
            cliente_id=incident.cliente_id,
            accion="solicitud_aceptada",
            descripcion=(
                f"Taller {taller_id} acepto solicitud {request.id} "
                f"y asigno tecnico={technician.id}, transporte={transport.id}."
            ),
            actor_usuario_id=taller_id,
        )

        db.commit()
        db.refresh(request)
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    send_client_push_best_effort(
        cliente_id=incident.cliente_id,
        titulo="Tu solicitud fue aceptada",
        cuerpo="Un taller aceptó tu solicitud y ya asignó técnico para atenderte.",
        data={
            "evento": "solicitud_aceptada",
            "solicitud_id": str(request.id),
            "incidente_id": str(incident.id),
            "estado_solicitud": str(request.estado),
            "estado_incidente": repository.get_service_state_name(incident.estado_servicio_id),
        },
        db=db,
    )

    return WorkshopRequestDecisionResponse(
        solicitud_id=request.id,
        incidente_id=incident.id,
        estado_solicitud=request.estado,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        tecnico_id=request.tecnico_id,
        transporte_id=request.transporte_id,
        mensaje="Solicitud aceptada y recursos asignados.",
    )


def get_incident_detail_for_client(
    incidente_id: int,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentDetailResponse:
    # Devuelve detalle completo del incidente para su cliente propietario.
    repository = IncidentRepository(db)
    incident = repository.get_incident_for_client(incidente_id, cliente_id)
    if not incident:
        raise IncidentNotOwnedError("Incidente no encontrado para el cliente autenticado.")

    return _build_incident_detail_response(repository, incident=incident)


def get_incident_detail_for_workshop(
    incidente_id: int,
    *,
    taller_id: int,
    db: Session,
) -> IncidentDetailResponse:
    # Devuelve detalle completo del incidente para taller participante.
    repository = IncidentRepository(db)
    incident = repository.get_incident_by_id(incidente_id)
    if not incident:
        raise IncidentNotFoundError("Incidente no encontrado.")

    has_access = repository.has_workshop_request_for_incident(
        taller_id=taller_id,
        incidente_id=incidente_id,
    )
    if not has_access:
        raise WorkshopIncidentAccessDeniedError(
            "El taller no tiene acceso al detalle de este incidente."
        )

    return _build_incident_detail_response(repository, incident=incident)


def finalize_workshop_service(
    solicitud_id: int,
    data: WorkshopServiceCompletionRequest,
    *,
    taller_id: int,
    actor_tipo: str = "taller",
    actor_id: int | None = None,
    db: Session,
) -> WorkshopServiceCompletionResponse:
    # Cierra atencion de solicitud aceptada y libera tecnico/transporte.
    repository = IncidentRepository(db)

    request = repository.get_request_for_workshop(solicitud_id, taller_id)
    if not request:
        raise WorkshopRequestNotFoundError("Solicitud no encontrada para el taller autenticado.")

    incident = repository.get_incident_by_id(request.incidente_id)
    if not incident:
        raise IncidentNotFoundError("Incidente asociado no encontrado.")

    if request.estado == "finalizada":
        metric = repository.get_metric_by_incident(incident.id)
        return WorkshopServiceCompletionResponse(
            solicitud_id=request.id,
            incidente_id=incident.id,
            estado_solicitud=request.estado,
            estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
            tecnico_liberado_id=request.tecnico_id,
            transporte_liberado_id=request.transporte_id,
            metrica=_build_metric_payload(metric),
            mensaje="La solicitud ya se encontraba finalizada.",
        )

    if request.estado != "aceptada":
        raise InvalidIncidentFinalizationError(
            "Solo se puede finalizar una solicitud en estado aceptada."
        )

    if incident.taller_id != taller_id:
        raise InvalidIncidentFinalizationError(
            "El incidente no esta asignado al taller autenticado."
        )

    technician_id = request.tecnico_id
    transport_id = request.transporte_id
    duration_minutes = int(data.tiempo_minutos or 1)
    total_cost = float(data.costo_total or 0)
    workshop_commission = round(total_cost * 0.10, 2)
    distance_km = float(data.distancia_km) if data.distancia_km is not None else None
    resolved_actor_id = actor_id if actor_id is not None else taller_id
    normalized_actor = actor_tipo.strip().lower() if actor_tipo else "taller"

    try:
        if technician_id:
            technician = repository.get_technician_by_id(technician_id)
            if technician:
                repository.update_technician_state(technician, "disponible")

        if transport_id:
            transport = repository.get_transport_by_id(transport_id)
            if transport:
                repository.update_transport_state(transport, "disponible")

        repository.update_request(
            request,
            estado="finalizada",
            comentario=data.comentario_cierre,
        )

        attended_state = repository.get_or_create_service_state(
            name="atendido",
            description="Incidente finalizado y atendido por taller.",
        )
        repository.update_incident(
            incident,
            estado_servicio_id=attended_state.id,
        )

        repository.create_history(
            incidente_id=incident.id,
            taller_id=taller_id,
            cliente_id=incident.cliente_id,
            accion="servicio_finalizado",
            descripcion=(
                f"{normalized_actor.capitalize()} {resolved_actor_id} finalizo solicitud {request.id}. "
                f"Recursos liberados: tecnico={technician_id}, transporte={transport_id}."
            ),
            actor_usuario_id=resolved_actor_id,
        )

        metric = repository.upsert_metric(
            incidente_id=incident.id,
            solicitud_id=request.id,
            taller_id=taller_id,
            cliente_id=incident.cliente_id,
            tecnico_id=technician_id,
            transporte_id=transport_id,
            tiempo_minutos=duration_minutes,
            costo_total=total_cost,
            comision_plataforma=workshop_commission,
            distancia_km=distance_km,
            observaciones=data.comentario_cierre,
        )
        repository.create_history(
            incidente_id=incident.id,
            taller_id=taller_id,
            cliente_id=incident.cliente_id,
            accion="metrica_registrada",
            descripcion=(
                f"Metrica registrada: tiempo={duration_minutes}m, "
                f"costo={total_cost}, comision={workshop_commission}."
            ),
            actor_usuario_id=resolved_actor_id,
        )

        db.commit()
        db.refresh(request)
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    if normalized_actor == "tecnico":
        titulo = "Servicio finalizado por técnico"
        evento = "solicitud_finalizada_tecnico"
    else:
        titulo = "Servicio finalizado"
        evento = "servicio_finalizado"

    send_client_push_best_effort(
        cliente_id=incident.cliente_id,
        titulo=titulo,
        cuerpo="Tu asistencia fue finalizada. Ya puedes revisar las métricas del servicio.",
        data={
            "evento": evento,
            "solicitud_id": str(request.id),
            "incidente_id": str(incident.id),
            "estado_solicitud": str(request.estado),
            "estado_incidente": repository.get_service_state_name(incident.estado_servicio_id),
            "actor_tipo": normalized_actor,
            "actor_id": str(resolved_actor_id),
        },
        db=db,
    )

    return WorkshopServiceCompletionResponse(
        solicitud_id=request.id,
        incidente_id=incident.id,
        estado_solicitud=request.estado,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        tecnico_liberado_id=technician_id,
        transporte_liberado_id=transport_id,
        metrica=_build_metric_payload(metric),
        mensaje="Servicio finalizado y recursos liberados.",
    )


def finalize_service_by_technician(
    solicitud_id: int,
    data: WorkshopServiceCompletionRequest,
    *,
    tecnico_id: int,
    db: Session,
) -> WorkshopServiceCompletionResponse:
    # Permite al tecnico mobile finalizar servicio y registrar metrica.
    repository = IncidentRepository(db)
    request = repository.get_request_for_technician(solicitud_id, tecnico_id)
    if not request:
        raise TechnicianAccessDeniedError(
            "La solicitud no pertenece al tecnico autenticado."
        )

    incident = repository.get_incident_by_id(request.incidente_id)
    if not incident:
        raise IncidentNotFoundError("Incidente asociado no encontrado.")
    if request.taller_id != incident.taller_id:
        raise InvalidIncidentFinalizationError(
            "La solicitud no coincide con el taller asignado al incidente."
        )

    return finalize_workshop_service(
        solicitud_id,
        data,
        taller_id=request.taller_id,
        actor_tipo="tecnico",
        actor_id=tecnico_id,
        db=db,
    )


def reject_service_by_technician(
    solicitud_id: int,
    data: TechnicianRequestRejectRequest,
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianRequestRejectResponse:
    # Permite al tecnico rechazar una solicitud asignada y liberar recursos.
    repository = IncidentRepository(db)
    request = repository.get_request_for_technician(solicitud_id, tecnico_id)
    if not request:
        raise TechnicianAccessDeniedError(
            "La solicitud no pertenece al tecnico autenticado."
        )

    incident = repository.get_incident_by_id(request.incidente_id)
    if not incident:
        raise IncidentNotFoundError("Incidente asociado no encontrado.")

    if request.estado not in {"aceptada", "en_camino", "en_proceso"}:
        raise InvalidIncidentFinalizationError(
            "Solo puedes rechazar una solicitud activa asignada."
        )

    technician_id = request.tecnico_id or tecnico_id
    transport_id = request.transporte_id

    try:
        if technician_id:
            technician = repository.get_technician_by_id(technician_id)
            if technician:
                repository.update_technician_state(technician, "disponible")

        if transport_id:
            transport = repository.get_transport_by_id(transport_id)
            if transport:
                repository.update_transport_state(transport, "disponible")
        elif request.taller_id:
            # Fallback para estados legacy: libera cualquier transporte marcado como asignado.
            assigned_transports = repository.list_assigned_transports_for_workshop(request.taller_id)
            for assigned_transport in assigned_transports:
                repository.update_transport_state(assigned_transport, "disponible")

        repository.update_request(
            request,
            estado="rechazada_tecnico",
            comentario=data.comentario,
            tecnico_id=None,
            transporte_id=None,
        )

        pending_state = repository.get_or_create_service_state(
            name="pendiente",
            description="Incidente reportado pendiente de evaluacion.",
        )
        repository.update_incident(
            incident,
            estado_servicio_id=pending_state.id,
            taller_id=None,
        )

        repository.create_history(
            incidente_id=incident.id,
            taller_id=request.taller_id,
            cliente_id=incident.cliente_id,
            accion="solicitud_rechazada_tecnico",
            descripcion=(
                f"Tecnico {tecnico_id} rechazo solicitud {request.id}. "
                f"Recursos liberados: transporte={transport_id}."
            ),
            actor_usuario_id=tecnico_id,
        )

        from app.services.Tecnico.location_cache import ACTIVE_TECHNICIAN_LOCATIONS

        if technician_id in ACTIVE_TECHNICIAN_LOCATIONS:
            current = ACTIVE_TECHNICIAN_LOCATIONS[technician_id]
            ACTIVE_TECHNICIAN_LOCATIONS[technician_id] = current.model_copy(
                update={
                    "solicitud_id": None,
                    "actualizada_en": datetime.now(),
                }
            )

        db.commit()
        db.refresh(request)
        db.refresh(incident)
    except Exception:
        db.rollback()
        raise

    send_client_push_best_effort(
        cliente_id=incident.cliente_id,
        titulo="Solicitud rechazada por técnico",
        cuerpo=(
            "El técnico rechazó tu solicitud. "
            f"Motivo: {data.comentario.strip()}"
            if (data.comentario or "").strip()
            else "El técnico rechazó tu solicitud. Te notificaremos cuando se reasigne una nueva atención."
        ),
        data={
            "evento": "solicitud_rechazada_tecnico",
            "solicitud_id": str(request.id),
            "incidente_id": str(incident.id),
            "estado_solicitud": str(request.estado),
            "estado_incidente": repository.get_service_state_name(incident.estado_servicio_id),
            "motivo": (data.comentario or "").strip(),
        },
        db=db,
    )

    return TechnicianRequestRejectResponse(
        solicitud_id=request.id,
        incidente_id=incident.id,
        estado_solicitud=request.estado,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        tecnico_liberado_id=technician_id,
        transporte_liberado_id=transport_id,
        mensaje="Solicitud rechazada por el técnico y recursos liberados.",
    )


def update_technician_location(
    data: TechnicianLocationUpdateRequest,
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianLocationUpdateResponse:
    # Guarda ultima ubicacion reportada en memoria y en base de datos.
    repository = IncidentRepository(db)

    if data.solicitud_id:
        request = repository.get_request_for_technician(data.solicitud_id, tecnico_id)
        if not request:
            raise TechnicianAccessDeniedError(
                "La solicitud no pertenece al tecnico autenticado."
            )

    from app.services.Tecnico.location_cache import ACTIVE_TECHNICIAN_LOCATIONS, TechnicianLocationInMemory

    now = datetime.now()

    ACTIVE_TECHNICIAN_LOCATIONS[tecnico_id] = TechnicianLocationInMemory(
        tecnico_id=tecnico_id,
        solicitud_id=data.solicitud_id,
        latitud=data.latitud,
        longitud=data.longitud,
        precision_metros=data.precision_metros,
        actualizada_en=now,
    )

    try:
        repository.upsert_technician_location(
            tecnico_id=tecnico_id,
            latitud=data.latitud,
            longitud=data.longitud,
            solicitud_id=data.solicitud_id,
            precision_metros=data.precision_metros,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return TechnicianLocationUpdateResponse(
        tecnico_id=tecnico_id,
        solicitud_id=data.solicitud_id,
        latitud=data.latitud,
        longitud=data.longitud,
        precision_metros=data.precision_metros,
        mensaje="Ubicacion actualizada correctamente.",
    )


def list_technician_incoming_requests(
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianIncomingRequestsResponse:
    # Devuelve solicitudes activas asignadas al tecnico autenticado.
    repository = IncidentRepository(db)
    requests = repository.list_active_requests_for_technician(tecnico_id)

    items: list[TechnicianIncomingRequestItem] = []
    for request in requests:
        incident = repository.get_incident_by_id(request.incidente_id)
        if not incident:
            continue

        vehicle = repository.get_vehicle_by_plate(incident.vehiculo_placa)
        items.append(
            TechnicianIncomingRequestItem(
                solicitud_id=request.id,
                incidente_id=incident.id,
                estado_solicitud=request.estado,
                estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
                tipo_problema=incident.tipo_problema,
                prioridad=incident.prioridad,
                vehiculo_placa=incident.vehiculo_placa,
                vehiculo_marca=vehicle.marca if vehicle else None,
                vehiculo_modelo=vehicle.modelo if vehicle else None,
                vehiculo_anio=vehicle.anio if vehicle else None,
                ubicacion=incident.ubicacion,
                latitud=incident.latitud,
                longitud=incident.longitud,
                fecha_asignacion=request.fecha_asignacion,
            )
        )

    return TechnicianIncomingRequestsResponse(total=len(items), solicitudes=items)


def cancel_client_incident(
    incidente_id: int,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentCancelResponse:
    # Permite al cliente cancelar incidente propio antes del cierre definitivo.
    repository = IncidentRepository(db)
    incident = repository.get_incident_for_client(incidente_id, cliente_id)
    if not incident:
        raise IncidentNotOwnedError("Incidente no encontrado para el cliente autenticado.")

    current_state = repository.get_service_state_name(incident.estado_servicio_id)
    if current_state in {"atendido", "cancelado"}:
        raise IncidentCancellationError(
            "El incidente no se puede cancelar en su estado actual."
        )

    cancel_state = repository.get_or_create_service_state(
        name="cancelado",
        description="Incidente cancelado por el cliente.",
    )

    try:
        repository.update_incident(incident, estado_servicio_id=cancel_state.id)
        requests = repository.list_requests_for_incident(incident.id)
        for request in requests:
            if request.estado in {"enviada", "pendiente", "aceptada"}:
                repository.update_request(request, estado="cancelada_cliente")

        repository.create_history(
            incidente_id=incident.id,
            taller_id=incident.taller_id,
            cliente_id=cliente_id,
            accion="incidente_cancelado",
            descripcion="Cliente cancelo su incidente.",
            actor_usuario_id=cliente_id,
        )
        db.commit()
        db.refresh(incident)
    except Exception:
        db.rollback()
        raise

    return IncidentCancelResponse(
        incidente_id=incident.id,
        estado_incidente=repository.get_service_state_name(incident.estado_servicio_id),
        mensaje="Incidente cancelado correctamente.",
    )


def list_client_incident_history(
    *,
    cliente_id: int,
    db: Session,
) -> ClientIncidentHistoryResponse:
    # Devuelve historial completo del cliente con estados y metricas de sus incidentes.
    repository = IncidentRepository(db)
    incidents = repository.list_incidents_for_client(cliente_id)

    items: list[ClientIncidentHistoryItem] = []
    for incident in incidents:
        requests = repository.list_requests_for_incident(incident.id)
        items.append(
            _build_incident_history_item(
                repository,
                incident=incident,
                request_states={request.estado for request in requests},
            )
        )

    return ClientIncidentHistoryResponse(total=len(items), incidentes=items)


def list_workshop_incident_history(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopIncidentHistoryResponse:
    # Devuelve incidentes donde el taller fue solicitado.
    repository = IncidentRepository(db)
    requests = repository.list_requests_for_workshop(taller_id)

    statuses_by_incident: dict[int, set[str]] = {}
    for request in requests:
        statuses_by_incident.setdefault(request.incidente_id, set()).add(request.estado)

    incidents_with_date: list[tuple[Incidente, set[str]]] = []
    for incident_id, states in statuses_by_incident.items():
        incident = repository.get_incident_by_id(incident_id)
        if incident:
            incidents_with_date.append((incident, states))

    incidents_with_date.sort(key=lambda row: row[0].fecha_hora, reverse=True)

    items = [
        _build_incident_history_item(
            repository,
            incident=incident,
            request_states=states,
        )
        for incident, states in incidents_with_date
    ]
    return WorkshopIncidentHistoryResponse(total=len(items), incidentes=items)


def list_technician_incident_history(
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianIncidentHistoryResponse:
    # Devuelve incidentes en los que participo el tecnico autenticado.
    repository = IncidentRepository(db)
    requests = repository.list_requests_for_technician(tecnico_id)

    statuses_by_incident: dict[int, set[str]] = {}
    for request in requests:
        statuses_by_incident.setdefault(request.incidente_id, set()).add(request.estado)

    incidents_with_date: list[tuple[Incidente, set[str]]] = []
    for incident_id, states in statuses_by_incident.items():
        incident = repository.get_incident_by_id(incident_id)
        if incident:
            incidents_with_date.append((incident, states))

    incidents_with_date.sort(key=lambda row: row[0].fecha_hora, reverse=True)

    items = [
        _build_incident_history_item(
            repository,
            incident=incident,
            request_states=states,
        )
        for incident, states in incidents_with_date
    ]
    return TechnicianIncidentHistoryResponse(total=len(items), incidentes=items)

