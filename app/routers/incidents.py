# Rutas de API para incidentes reportados por clientes moviles.

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.controllers.incident_controller import (
    cancel_client_incident_controller,
    decide_workshop_request_controller,
    finalize_technician_service_controller,
    finalize_workshop_service_controller,
    get_incident_detail_for_client_controller,
    get_incident_detail_for_workshop_controller,
    list_client_incident_history_controller,
    list_client_requests_controller,
    list_technician_incident_history_controller,
    list_workshop_candidates_controller,
    list_workshop_incident_history_controller,
    list_workshop_incoming_requests_controller,
    report_incident_controller,
    resubmit_incident_evidence_controller,
    select_workshops_for_incident_controller,
    update_technician_location_controller,
)
from app.database import get_db
from app.dependencies.auth import (
    AuthenticatedUser,
    require_mobile_cliente,
    require_mobile_tecnico,
    require_web_taller,
)
from app.core.evidence_storage import (
    allowed_extensions_for_kind,
    build_evidence_urls,
    resolve_evidence_directory,
    safe_file_extension,
)
from app.models.incident_schemas import (
    ClientIncidentHistoryResponse,
    ClientRequestsResponse,
    WorkshopIncidentHistoryResponse,
    TechnicianIncidentHistoryResponse,
    IncidentCancelResponse,
    IncidentDetailResponse,
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

router = APIRouter(prefix="/api/v1/incidentes", tags=["Incidentes"])


@router.post(
    "/evidencias/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_incident_evidence_endpoint(
    request: Request,
    tipo: str = Form(...),
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
) -> dict[str, object]:
    # Recibe archivo de evidencia y devuelve URL accesible para reporte de incidente.
    del current_user

    normalized_type = tipo.strip().lower()
    try:
        allowed_extensions_for_kind(normalized_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if file.content_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo determinar el tipo de archivo.",
        )

    max_size_bytes = 15 * 1024 * 1024 if normalized_type == "imagen" else 25 * 1024 * 1024
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de evidencia esta vacio.",
        )
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el limite permitido.",
        )

    extension = safe_file_extension(file.filename, file.content_type, normalized_type)
    file_name = f"{normalized_type}_{uuid4().hex}{extension}"
    storage_dir = resolve_evidence_directory()
    target_path = storage_dir / file_name

    with target_path.open("wb") as output_file:
        output_file.write(content)

    relative_url, absolute_url = build_evidence_urls(str(request.base_url).rstrip("/"), file_name)
    return {
        "tipo": normalized_type,
        "url": relative_url,
        "url_absoluta": absolute_url,
        "nombre_archivo": file_name,
        "size_bytes": len(content),
    }


@router.get(
    "/evidencias/{file_name}",
    status_code=status.HTTP_200_OK,
)
def get_incident_evidence_file_endpoint(file_name: str) -> FileResponse:
    # Sirve archivos de evidencia subidos para visualizacion y analisis IA.
    if Path(file_name).name != file_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de archivo invalido.",
        )

    file_path = resolve_evidence_directory() / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo de evidencia no encontrado.",
        )

    return FileResponse(path=file_path)


@router.post(
    "/reportar",
    response_model=IncidentReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_incident_endpoint(
    payload: IncidentReportRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentReportResponse:
    # Endpoint CU4: recibe solicitud de emergencia desde cliente autenticado.
    return report_incident_controller(payload, cliente_id=current_user.user_id, db=db)


@router.post(
    "/{incidente_id}/reenviar-evidencia",
    response_model=IncidentReportResponse,
    status_code=status.HTTP_200_OK,
)
def resubmit_incident_evidence_endpoint(
    incidente_id: int,
    payload: IncidentEvidenceResubmissionRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentReportResponse:
    # Reenvia evidencia cuando el incidente requiere mas informacion.
    return resubmit_incident_evidence_controller(
        incidente_id,
        payload,
        cliente_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/{incidente_id}/candidatos",
    response_model=IncidentCandidatesResponse,
    status_code=status.HTTP_200_OK,
)
def list_workshop_candidates_endpoint(
    incidente_id: int,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentCandidatesResponse:
    # Devuelve talleres candidatos para seleccion del cliente.
    return list_workshop_candidates_controller(
        incidente_id,
        cliente_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/{incidente_id}/detalle",
    response_model=IncidentDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_incident_detail_for_client_endpoint(
    incidente_id: int,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    # Devuelve detalle completo del incidente al cliente propietario.
    return get_incident_detail_for_client_controller(
        incidente_id,
        cliente_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/{incidente_id}/seleccionar-talleres",
    response_model=IncidentCandidateSelectionResponse,
    status_code=status.HTTP_200_OK,
)
def select_workshops_for_incident_endpoint(
    incidente_id: int,
    payload: IncidentCandidateSelectionRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentCandidateSelectionResponse:
    # Crea solicitudes para talleres elegidos por el cliente desde la fase de candidatos.
    return select_workshops_for_incident_controller(
        incidente_id,
        payload,
        cliente_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/mis-solicitudes",
    response_model=ClientRequestsResponse,
    status_code=status.HTTP_200_OK,
)
def list_client_requests_endpoint(
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> ClientRequestsResponse:
    # Permite al cliente visualizar sus solicitudes y su estado.
    return list_client_requests_controller(
        cliente_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/mi-historial",
    response_model=ClientIncidentHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_client_incident_history_endpoint(
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> ClientIncidentHistoryResponse:
    # Historial del cliente con incidentes y metricas de cierre.
    return list_client_incident_history_controller(
        cliente_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/taller/mi-historial",
    response_model=WorkshopIncidentHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_workshop_incident_history_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopIncidentHistoryResponse:
    # Historial de incidentes donde el taller fue solicitado.
    return list_workshop_incident_history_controller(
        taller_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/tecnico/mi-historial",
    response_model=TechnicianIncidentHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_technician_incident_history_endpoint(
    current_user: AuthenticatedUser = Depends(require_mobile_tecnico),
    db: Session = Depends(get_db),
) -> TechnicianIncidentHistoryResponse:
    # Historial de incidentes en los que participo el tecnico.
    return list_technician_incident_history_controller(
        tecnico_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/{incidente_id}/cancelar",
    response_model=IncidentCancelResponse,
    status_code=status.HTTP_200_OK,
)
def cancel_client_incident_endpoint(
    incidente_id: int,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentCancelResponse:
    # Cancela incidente del cliente antes de su cierre final.
    return cancel_client_incident_controller(
        incidente_id,
        cliente_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/taller/solicitudes",
    response_model=WorkshopIncomingRequestsResponse,
    status_code=status.HTTP_200_OK,
)
def list_workshop_incoming_requests_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopIncomingRequestsResponse:
    # Entrega bandeja de solicitudes al taller con informacion completa del incidente.
    return list_workshop_incoming_requests_controller(
        taller_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/taller/solicitudes/{solicitud_id}/decision",
    response_model=WorkshopRequestDecisionResponse,
    status_code=status.HTTP_200_OK,
)
def decide_workshop_request_endpoint(
    solicitud_id: int,
    payload: WorkshopRequestDecisionRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopRequestDecisionResponse:
    # Permite al taller aceptar/rechazar solicitud. Solo el primero en aceptar es valido.
    return decide_workshop_request_controller(
        solicitud_id,
        payload,
        taller_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/taller/incidentes/{incidente_id}/detalle",
    response_model=IncidentDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_incident_detail_for_workshop_endpoint(
    incidente_id: int,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    # Devuelve detalle completo de incidente para taller participante.
    return get_incident_detail_for_workshop_controller(
        incidente_id,
        taller_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/taller/solicitudes/{solicitud_id}/finalizar",
    response_model=WorkshopServiceCompletionResponse,
    status_code=status.HTTP_200_OK,
)
def finalize_workshop_service_endpoint(
    solicitud_id: int,
    payload: WorkshopServiceCompletionRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopServiceCompletionResponse:
    # Finaliza servicio y libera tecnico/transporte asignados.
    return finalize_workshop_service_controller(
        solicitud_id,
        payload,
        taller_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/tecnico/ubicacion",
    response_model=TechnicianLocationUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_technician_location_endpoint(
    payload: TechnicianLocationUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_tecnico),
    db: Session = Depends(get_db),
) -> TechnicianLocationUpdateResponse:
    # Actualiza ubicacion de tecnico para seguimiento en panel web del taller.
    return update_technician_location_controller(
        payload,
        tecnico_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/tecnico/solicitudes/{solicitud_id}/finalizar",
    response_model=WorkshopServiceCompletionResponse,
    status_code=status.HTTP_200_OK,
)
def finalize_technician_service_endpoint(
    solicitud_id: int,
    payload: WorkshopServiceCompletionRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_tecnico),
    db: Session = Depends(get_db),
) -> WorkshopServiceCompletionResponse:
    # Finaliza servicio desde tecnico mobile y registra metricas.
    return finalize_technician_service_controller(
        solicitud_id,
        payload,
        tecnico_id=current_user.user_id,
        db=db,
    )
