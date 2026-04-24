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
    list_technician_incoming_requests_controller,
    list_technician_incident_history_controller,
    list_workshop_candidates_controller,
    list_workshop_incident_history_controller,
    list_workshop_incoming_requests_controller,
    report_incident_controller,
    resubmit_incident_evidence_controller,
    select_workshops_for_incident_controller,
    reject_technician_service_controller,
    update_technician_location_controller,
)
from app.database import get_db
from app.dependencies.auth import (
    AuthenticatedUser,
    require_mobile_cliente,
    require_mobile_tecnico,
    require_web_taller,
    require_web_superuser,
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
    TechnicianIncomingRequestsResponse,
    TechnicianRequestRejectRequest,
    TechnicianRequestRejectResponse,
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


@router.get(
    "/tecnico/solicitudes",
    response_model=TechnicianIncomingRequestsResponse,
    status_code=status.HTTP_200_OK,
)
def list_technician_incoming_requests_endpoint(
    current_user: AuthenticatedUser = Depends(require_mobile_tecnico),
    db: Session = Depends(get_db),
) -> TechnicianIncomingRequestsResponse:
    # Bandeja de solicitudes activas para tecnico autenticado.
    return list_technician_incoming_requests_controller(
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


@router.post(
    "/tecnico/solicitudes/{solicitud_id}/rechazar",
    response_model=TechnicianRequestRejectResponse,
    status_code=status.HTTP_200_OK,
)
def reject_technician_service_endpoint(
    solicitud_id: int,
    payload: TechnicianRequestRejectRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_tecnico),
    db: Session = Depends(get_db),
) -> TechnicianRequestRejectResponse:
    # Permite al tecnico rechazar solicitud activa y liberar recursos.
    return reject_technician_service_controller(
        solicitud_id,
        payload,
        tecnico_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/admin/historial",
    status_code=status.HTTP_200_OK,
)
def get_all_incidents_history_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_superuser),
    db: Session = Depends(get_db),
):
    """
    Obtiene el historial completo de todos los incidentes del sistema.
    Solo accesible para superusuarios.
    """
    from app.repositories.report_repository import ReportRepository
    from app.models.user import Usuario, Taller
    from app.models.incident import Incidente, EstadoServicio
    
    repository = ReportRepository(db)
    
    # Obtener todos los incidentes ordenados por fecha (más recientes primero)
    incidents = (
        db.query(Incidente)
        .order_by(Incidente.fecha_hora.desc())
        .all()
    )
    
    # Obtener información relacionada
    user_ids = {inc.cliente_id for inc in incidents}
    taller_ids = {inc.taller_id for inc in incidents if inc.taller_id}
    estado_ids = {inc.estado_servicio_id for inc in incidents}
    
    users = {u.id: u for u in db.query(Usuario).filter(Usuario.id.in_(user_ids)).all()}
    talleres = {t.id: t for t in db.query(Taller).filter(Taller.id.in_(taller_ids)).all()}
    estados = {e.id: e for e in db.query(EstadoServicio).filter(EstadoServicio.id.in_(estado_ids)).all()}
    
    # Construir respuesta
    result = []
    for inc in incidents:
        user = users.get(inc.cliente_id)
        taller = talleres.get(inc.taller_id) if inc.taller_id else None
        estado = estados.get(inc.estado_servicio_id)
        
        result.append({
            "incident_id": inc.id,
            "client_id": inc.cliente_id,
            "client_name": user.nombre if user else f"Cliente #{inc.cliente_id}",
            "client_email": user.correo if user else None,
            "vehicle_plate": inc.vehiculo_placa,
            "workshop_id": inc.taller_id,
            "workshop_name": taller.nombre if taller else None,
            "status": estado.nombre if estado else "desconocido",
            "problem_type": inc.tipo_problema,
            "description": inc.descripcion,
            "location": inc.ubicacion,
            "latitude": float(inc.latitud) if inc.latitud else None,
            "longitude": float(inc.longitud) if inc.longitud else None,
            "priority": inc.prioridad,
            "created_at": inc.fecha_hora,
        })
    
    return {
        "total": len(result),
        "incidents": result
    }
