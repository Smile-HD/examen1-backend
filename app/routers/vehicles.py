# Rutas de API para gestion de vehiculos de cliente.

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.vehicle_controller import (
    list_client_vehicles_controller,
    register_vehicle_controller,
)
from app.database import get_db
from app.dependencies.auth import AuthenticatedUser, require_mobile_cliente
from app.models.vehicle_schemas import (
    VehicleListItemResponse,
    VehicleRegistrationRequest,
    VehicleRegistrationResponse,
)

router = APIRouter(prefix="/api/v1/vehiculos", tags=["Vehiculos"])


@router.post(
    "/registro",
    response_model=VehicleRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_vehicle_endpoint(
    payload: VehicleRegistrationRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> VehicleRegistrationResponse:
    # Endpoint CU3: registra vehiculo para cliente autenticado en canal mobile.
    return register_vehicle_controller(payload, cliente_id=current_user.user_id, db=db)


@router.get(
    "/mis-vehiculos",
    response_model=list[VehicleListItemResponse],
    status_code=status.HTTP_200_OK,
)
def list_my_vehicles_endpoint(
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> list[VehicleListItemResponse]:
    # Endpoint para que la app móvil obtenga vehículos del cliente autenticado.
    return list_client_vehicles_controller(cliente_id=current_user.user_id, db=db)
