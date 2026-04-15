# Controlador HTTP para CU4: reportar emergencia vehicular.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.incident_schemas import (
    ClientIncidentHistoryResponse,
    ClientRequestsResponse,
    WorkshopIncidentHistoryResponse,
    TechnicianIncidentHistoryResponse,
    TechnicianIncomingRequestsResponse,
    TechnicianRequestRejectRequest,
    TechnicianRequestRejectResponse,
    IncidentDetailResponse,
    IncidentCancelResponse,
    IncidentCandidateSelectionRequest,
    IncidentCandidateSelectionResponse,
    IncidentCandidatesResponse,
    IncidentEvidenceResubmissionRequest,
    IncidentReportRequest,
    IncidentReportResponse,
    TechnicianLocationUpdateRequest,
    TechnicianLocationUpdateResponse,
    WorkshopIncomingRequestsResponse,
    WorkshopServiceCompletionRequest,
    WorkshopServiceCompletionResponse,
    WorkshopRequestDecisionRequest,
    WorkshopRequestDecisionResponse,
)
from app.services.incident_service import (
    IncidentNotFoundError,
    IncidentNeedsMoreEvidenceError,
    IncidentNotOwnedError,
    IncidentCancellationError,
    InvalidIncidentFinalizationError,
    InvalidWorkshopSelectionError,
    LocationRequiredError,
    NoWorkshopCandidatesError,
    TechnicianAccessDeniedError,
    VehicleNotOwnedError,
    WorkshopIncidentAccessDeniedError,
    WorkshopResourceSelectionError,
    WorkshopRequestNotFoundError,
    WorkshopResourcesUnavailableError,
    decide_workshop_request,
    cancel_client_incident,
    finalize_service_by_technician,
    reject_service_by_technician,
    finalize_workshop_service,
    get_incident_detail_for_client,
    get_incident_detail_for_workshop,
    list_client_incident_history,
    list_client_requests,
    list_workshop_incident_history,
    list_technician_incident_history,
    list_workshop_candidates,
    list_technician_incoming_requests,
    list_workshop_incoming_requests,
    report_incident,
    resubmit_incident_evidence,
    select_workshops_for_incident,
    update_technician_location,
)


def report_incident_controller(
    payload: IncidentReportRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentReportResponse:
    # Traduce errores de negocio del CU4 a respuestas HTTP claras para la app movil.
    try:
        return report_incident(payload, cliente_id=cliente_id, db=db)
    except LocationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VehicleNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def resubmit_incident_evidence_controller(
    incidente_id: int,
    payload: IncidentEvidenceResubmissionRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentReportResponse:
    # Gestiona reenvio de evidencia cuando el incidente quedo en requiere_info.
    try:
        return resubmit_incident_evidence(
            incidente_id,
            payload,
            cliente_id=cliente_id,
            db=db,
        )
    except IncidentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def list_workshop_candidates_controller(
    incidente_id: int,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentCandidatesResponse:
    # Expone lista de talleres candidatos para que el cliente decida el envio.
    try:
        return list_workshop_candidates(incidente_id, cliente_id=cliente_id, db=db)
    except IncidentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNeedsMoreEvidenceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NoWorkshopCandidatesError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def select_workshops_for_incident_controller(
    incidente_id: int,
    payload: IncidentCandidateSelectionRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentCandidateSelectionResponse:
    # Recibe la seleccion del cliente y crea solicitudes hacia talleres elegidos.
    try:
        return select_workshops_for_incident(
            incidente_id,
            payload,
            cliente_id=cliente_id,
            db=db,
        )
    except IncidentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNeedsMoreEvidenceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidWorkshopSelectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def list_client_requests_controller(
    *,
    cliente_id: int,
    db: Session,
) -> ClientRequestsResponse:
    # Devuelve solicitudes asociadas a incidentes del cliente autenticado.
    return list_client_requests(cliente_id=cliente_id, db=db)


def list_client_incident_history_controller(
    *,
    cliente_id: int,
    db: Session,
) -> ClientIncidentHistoryResponse:
    # Devuelve historial completo de incidentes del cliente autenticado.
    return list_client_incident_history(cliente_id=cliente_id, db=db)


def list_workshop_incident_history_controller(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopIncidentHistoryResponse:
    # Devuelve incidentes en los que el taller fue solicitado.
    return list_workshop_incident_history(taller_id=taller_id, db=db)


def list_technician_incident_history_controller(
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianIncidentHistoryResponse:
    # Devuelve incidentes en los que participo el tecnico autenticado.
    return list_technician_incident_history(tecnico_id=tecnico_id, db=db)


def list_technician_incoming_requests_controller(
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianIncomingRequestsResponse:
    # Devuelve bandeja activa del tecnico autenticado.
    return list_technician_incoming_requests(tecnico_id=tecnico_id, db=db)


def cancel_client_incident_controller(
    incidente_id: int,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentCancelResponse:
    # Cancela incidente del cliente y actualiza historial.
    try:
        return cancel_client_incident(incidente_id, cliente_id=cliente_id, db=db)
    except IncidentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentCancellationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def list_workshop_incoming_requests_controller(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopIncomingRequestsResponse:
    # Devuelve bandeja de solicitudes para taller autenticado en canal web.
    return list_workshop_incoming_requests(taller_id=taller_id, db=db)


def decide_workshop_request_controller(
    solicitud_id: int,
    payload: WorkshopRequestDecisionRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopRequestDecisionResponse:
    # Ejecuta decision de taller sobre solicitud (aceptar/rechazar).
    try:
        return decide_workshop_request(
            solicitud_id,
            payload,
            taller_id=taller_id,
            db=db,
        )
    except WorkshopRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkshopResourceSelectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WorkshopResourcesUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def get_incident_detail_for_client_controller(
    incidente_id: int,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentDetailResponse:
    # Devuelve detalle de incidente al cliente propietario.
    try:
        return get_incident_detail_for_client(
            incidente_id,
            cliente_id=cliente_id,
            db=db,
        )
    except IncidentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def get_incident_detail_for_workshop_controller(
    incidente_id: int,
    *,
    taller_id: int,
    db: Session,
) -> IncidentDetailResponse:
    # Devuelve detalle de incidente a taller participante.
    try:
        return get_incident_detail_for_workshop(
            incidente_id,
            taller_id=taller_id,
            db=db,
        )
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkshopIncidentAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def finalize_workshop_service_controller(
    solicitud_id: int,
    payload: WorkshopServiceCompletionRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopServiceCompletionResponse:
    # Cierra servicio y libera recursos asignados.
    try:
        return finalize_workshop_service(
            solicitud_id,
            payload,
            taller_id=taller_id,
            db=db,
        )
    except WorkshopRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidIncidentFinalizationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def finalize_technician_service_controller(
    solicitud_id: int,
    payload: WorkshopServiceCompletionRequest,
    *,
    tecnico_id: int,
    db: Session,
) -> WorkshopServiceCompletionResponse:
    # Cierra servicio desde canal mobile del tecnico asignado.
    try:
        return finalize_service_by_technician(
            solicitud_id,
            payload,
            tecnico_id=tecnico_id,
            db=db,
        )
    except TechnicianAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except WorkshopRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidIncidentFinalizationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def reject_technician_service_controller(
    solicitud_id: int,
    payload: TechnicianRequestRejectRequest,
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianRequestRejectResponse:
    # Permite al tecnico rechazar solicitud activa y liberar recursos.
    try:
        return reject_service_by_technician(
            solicitud_id,
            payload,
            tecnico_id=tecnico_id,
            db=db,
        )
    except TechnicianAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except WorkshopRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidIncidentFinalizationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def update_technician_location_controller(
    payload: TechnicianLocationUpdateRequest,
    *,
    tecnico_id: int,
    db: Session,
) -> TechnicianLocationUpdateResponse:
    # Registra ubicacion del tecnico en tiempo real para visualizacion del taller.
    try:
        return update_technician_location(payload, tecnico_id=tecnico_id, db=db)
    except TechnicianAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
