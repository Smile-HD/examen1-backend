# Rutas de API para gestion operativa del taller (tecnicos y unidades).

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers.workshop_controller import (
    assign_technician_to_workshop_controller,
    create_workshop_vehicle_controller,
    delete_workshop_vehicle_controller,
    get_workshop_profile_controller,
    list_workshop_history_controller,
    list_workshop_technician_locations_controller,
    list_workshop_technicians_controller,
    list_workshop_vehicles_controller,
    search_technicians_controller,
    unassign_technician_from_workshop_controller,
    update_workshop_profile_controller,
    update_workshop_vehicle_controller,
)
from app.database import get_db
from app.dependencies.auth import AuthenticatedUser, require_web_taller
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

router = APIRouter(prefix="/api/v1/taller", tags=["Taller"])


@router.get(
    "/perfil",
    response_model=WorkshopProfileResponse,
    status_code=status.HTTP_200_OK,
)
def get_workshop_profile_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopProfileResponse:
    # Devuelve perfil editable del taller autenticado.
    return get_workshop_profile_controller(taller_id=current_user.user_id, db=db)


@router.put(
    "/perfil",
    response_model=WorkshopProfileResponse,
    status_code=status.HTTP_200_OK,
)
def update_workshop_profile_endpoint(
    payload: WorkshopProfileUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopProfileResponse:
    # Actualiza datos generales y servicios ofrecidos por el taller.
    return update_workshop_profile_controller(
        payload,
        taller_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/tecnicos/buscar",
    response_model=list[WorkshopTechnicianCandidateResponse],
    status_code=status.HTTP_200_OK,
)
def search_technicians_endpoint(
    nombre: str = Query(..., min_length=2, max_length=120),
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> list[WorkshopTechnicianCandidateResponse]:
    # Busca tecnicos por nombre para asignacion desde panel de taller.
    _ = current_user
    return search_technicians_controller(nombre, db=db)


@router.post(
    "/tecnicos/asignar",
    response_model=WorkshopTechnicianAssignResponse,
    status_code=status.HTTP_200_OK,
)
def assign_technician_endpoint(
    payload: WorkshopTechnicianAssignRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopTechnicianAssignResponse:
    # Asigna tecnico existente al taller autenticado.
    return assign_technician_to_workshop_controller(
        payload,
        taller_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/tecnicos",
    response_model=list[WorkshopTechnicianListItemResponse],
    status_code=status.HTTP_200_OK,
)
def list_workshop_technicians_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> list[WorkshopTechnicianListItemResponse]:
    # Lista tecnicos que ya pertenecen al taller.
    return list_workshop_technicians_controller(taller_id=current_user.user_id, db=db)


@router.post(
    "/tecnicos/desasignar",
    response_model=WorkshopTechnicianUnassignResponse,
    status_code=status.HTTP_200_OK,
)
def unassign_technician_endpoint(
    payload: WorkshopTechnicianUnassignRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopTechnicianUnassignResponse:
    # Desasigna tecnico del taller autenticado.
    return unassign_technician_from_workshop_controller(
        payload,
        taller_id=current_user.user_id,
        db=db,
    )


@router.post(
    "/vehiculos",
    response_model=WorkshopVehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workshop_vehicle_endpoint(
    payload: WorkshopVehicleCreateRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopVehicleResponse:
    # Crea una unidad de servicio para el taller.
    return create_workshop_vehicle_controller(payload, taller_id=current_user.user_id, db=db)


@router.get(
    "/vehiculos",
    response_model=list[WorkshopVehicleResponse],
    status_code=status.HTTP_200_OK,
)
def list_workshop_vehicles_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> list[WorkshopVehicleResponse]:
    # Lista unidades de servicio registradas para el taller autenticado.
    return list_workshop_vehicles_controller(taller_id=current_user.user_id, db=db)


@router.put(
    "/vehiculos/{vehiculo_id}",
    response_model=WorkshopVehicleResponse,
    status_code=status.HTTP_200_OK,
)
def update_workshop_vehicle_endpoint(
    vehiculo_id: int,
    payload: WorkshopVehicleUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopVehicleResponse:
    # Actualiza una unidad de servicio del taller autenticado.
    return update_workshop_vehicle_controller(
        vehiculo_id,
        payload,
        taller_id=current_user.user_id,
        db=db,
    )


@router.delete(
    "/vehiculos/{vehiculo_id}",
    response_model=WorkshopVehicleDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_workshop_vehicle_endpoint(
    vehiculo_id: int,
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopVehicleDeleteResponse:
    # Elimina una unidad de servicio del taller autenticado.
    return delete_workshop_vehicle_controller(
        vehiculo_id,
        taller_id=current_user.user_id,
        db=db,
    )


@router.get(
    "/historial",
    response_model=WorkshopIncidentHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def list_workshop_history_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> WorkshopIncidentHistoryResponse:
    # Devuelve historial de incidentes donde el taller fue solicitado.
    return list_workshop_history_controller(taller_id=current_user.user_id, db=db)


@router.get(
    "/tecnicos/ubicaciones",
    response_model=list[WorkshopTechnicianLocationItem],
    status_code=status.HTTP_200_OK,
)
def list_workshop_technician_locations_endpoint(
    current_user: AuthenticatedUser = Depends(require_web_taller),
    db: Session = Depends(get_db),
) -> list[WorkshopTechnicianLocationItem]:
    # Devuelve ubicacion en tiempo real reportada por tecnicos del taller.
    return list_workshop_technician_locations_controller(taller_id=current_user.user_id, db=db)
