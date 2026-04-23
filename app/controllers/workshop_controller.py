# Controlador HTTP para gestion de tecnicos y unidades del taller.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.incident_schemas import WorkshopIncidentHistoryResponse
from app.models.workshop_schemas import (
    WorkshopProfileResponse,
    WorkshopProfileUpdateRequest,
    WorkshopTechnicianAssignRequest,
    WorkshopTechnicianAssignResponse,
    WorkshopTechnicianCandidateResponse,
    WorkshopTechnicianLocationItem,
    WorkshopTechnicianListItemResponse,
    WorkshopTechnicianUnassignRequest,
    WorkshopTechnicianUnassignResponse,
    WorkshopVehicleCreateRequest,
    WorkshopVehicleDeleteResponse,
    WorkshopVehicleResponse,
    WorkshopVehicleUpdateRequest,
)
from app.services.Taller.workshop_service import (
    InvalidWorkshopServiceSelectionError,
    TechnicianAlreadyAssignedError,
    TechnicianEmailMismatchError,
    TechnicianNotAssignedToWorkshopError,
    TechnicianNotFoundError,
    WorkshopProfileNotFoundError,
    WorkshopVehicleAlreadyExistsError,
    WorkshopVehicleNotFoundError,
    assign_technician_to_workshop,
    create_workshop_vehicle,
    delete_workshop_vehicle,
    get_workshop_profile,
    list_workshop_technician_locations,
    list_workshop_technicians,
    list_workshop_vehicles,
    search_technicians,
    unassign_technician_from_workshop,
    update_workshop_profile,
    update_workshop_vehicle,
)
from app.services.incident_service import list_workshop_incident_history


def search_technicians_controller(
    query: str,
    *,
    db: Session,
) -> list[WorkshopTechnicianCandidateResponse]:
    # Ejecuta busqueda de tecnicos por nombre.
    return search_technicians(query, db=db)


def assign_technician_to_workshop_controller(
    payload: WorkshopTechnicianAssignRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopTechnicianAssignResponse:
    # Traduce errores de dominio de asignacion de tecnico a respuestas HTTP.
    try:
        return assign_technician_to_workshop(
            payload.usuario_id,
            taller_id=taller_id,
            db=db,
        )
    except TechnicianNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TechnicianEmailMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TechnicianAlreadyAssignedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def list_workshop_technicians_controller(
    *,
    taller_id: int,
    db: Session,
) -> list[WorkshopTechnicianListItemResponse]:
    # Lista tecnicos asignados al taller autenticado.
    return list_workshop_technicians(taller_id=taller_id, db=db)


def unassign_technician_from_workshop_controller(
    payload: WorkshopTechnicianUnassignRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopTechnicianUnassignResponse:
    # Traduce errores de desasignacion de tecnico a respuestas HTTP.
    try:
        return unassign_technician_from_workshop(payload, taller_id=taller_id, db=db)
    except TechnicianNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TechnicianNotAssignedToWorkshopError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def create_workshop_vehicle_controller(
    payload: WorkshopVehicleCreateRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopVehicleResponse:
    # Traduce errores de dominio del registro de unidades a HTTP.
    try:
        return create_workshop_vehicle(payload, taller_id=taller_id, db=db)
    except WorkshopVehicleAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def list_workshop_vehicles_controller(
    *,
    taller_id: int,
    db: Session,
) -> list[WorkshopVehicleResponse]:
    # Lista unidades de servicio del taller.
    return list_workshop_vehicles(taller_id=taller_id, db=db)


def update_workshop_vehicle_controller(
    vehicle_id: int,
    payload: WorkshopVehicleUpdateRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopVehicleResponse:
    # Traduce errores de dominio de actualizacion a respuestas HTTP.
    try:
        return update_workshop_vehicle(
            vehicle_id,
            payload,
            taller_id=taller_id,
            db=db,
        )
    except WorkshopVehicleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkshopVehicleAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def delete_workshop_vehicle_controller(
    vehicle_id: int,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopVehicleDeleteResponse:
    # Traduce errores de dominio de eliminacion a respuestas HTTP.
    try:
        return delete_workshop_vehicle(
            vehicle_id,
            taller_id=taller_id,
            db=db,
        )
    except WorkshopVehicleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def list_workshop_history_controller(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopIncidentHistoryResponse:
    # Devuelve historial de incidentes donde el taller fue solicitado.
    return list_workshop_incident_history(taller_id=taller_id, db=db)


def list_workshop_technician_locations_controller(
    *,
    taller_id: int,
    db: Session,
) -> list[WorkshopTechnicianLocationItem]:
    # Devuelve ubicaciones reportadas por tecnicos del taller.
    return list_workshop_technician_locations(taller_id=taller_id, db=db)


def get_workshop_profile_controller(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopProfileResponse:
    # Devuelve el perfil editable del taller autenticado.
    try:
        return get_workshop_profile(taller_id=taller_id, db=db)
    except WorkshopProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def update_workshop_profile_controller(
    payload: WorkshopProfileUpdateRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopProfileResponse:
    # Actualiza el perfil del taller y sus servicios ofrecidos.
    try:
        return update_workshop_profile(payload, taller_id=taller_id, db=db)
    except WorkshopProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidWorkshopServiceSelectionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def upload_workshop_qr_controller(
    *,
    taller_id: int,
    file_bytes: bytes,
    original_file_name: str | None,
    content_type: str | None,
    base_url: str,
    db: Session,
) -> dict:
    from app.services.Taller.workshop_service import upload_workshop_qr
    try:
        return upload_workshop_qr(
            taller_id=taller_id,
            file_bytes=file_bytes,
            original_file_name=original_file_name,
            content_type=content_type,
            base_url=base_url,
            db=db,
        )
    except WorkshopProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
