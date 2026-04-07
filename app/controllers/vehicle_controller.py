# Controlador HTTP para CU3: Registrar vehiculo.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.vehicle_schemas import (
    VehicleListItemResponse,
    VehicleRegistrationRequest,
    VehicleRegistrationResponse,
)
from app.services.vehicle_service import (
    VehicleAlreadyExistsError,
    list_client_vehicles,
    register_vehicle,
)


def register_vehicle_controller(
    payload: VehicleRegistrationRequest,
    *,
    cliente_id: int,
    db: Session,
) -> VehicleRegistrationResponse:
    # Traduce errores de dominio del CU3 a respuestas HTTP.
    try:
        return register_vehicle(payload, cliente_id=cliente_id, db=db)
    except VehicleAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def list_client_vehicles_controller(
    *,
    cliente_id: int,
    db: Session,
) -> list[VehicleListItemResponse]:
    # Devuelve flota del cliente autenticado para selección en la app.
    return list_client_vehicles(cliente_id=cliente_id, db=db)
