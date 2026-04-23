# Servicio de negocio para CU3: Registrar vehiculo.

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.vehicle_schemas import (
    VehicleListItemResponse,
    VehicleRegistrationRequest,
    VehicleRegistrationResponse,
)
from app.repositories.vehicle_repository import VehicleRepository


class VehicleAlreadyExistsError(Exception):
    # Error de dominio cuando la placa ya esta registrada.
    pass


def register_vehicle(
    data: VehicleRegistrationRequest,
    *,
    cliente_id: int,
    db: Session,
) -> VehicleRegistrationResponse:
    # Valida reglas del CU3 y persiste el vehiculo asociado al cliente.
    repository = VehicleRepository(db)

    if repository.get_by_plate(data.placa):
        raise VehicleAlreadyExistsError("La placa ya se encuentra registrada.")

    try:
        vehicle = repository.create(
            cliente_id=cliente_id,
            placa=data.placa,
            marca=data.marca,
            modelo=data.modelo,
            anio=data.anio,
            tipo=data.tipo,
        )
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise VehicleAlreadyExistsError("La placa ya se encuentra registrada.") from exc
    except Exception:
        db.rollback()
        raise

    return VehicleRegistrationResponse(
        placa=vehicle.placa,
        cliente_id=vehicle.cliente_id,
        marca=vehicle.marca,
        modelo=vehicle.modelo,
        anio=vehicle.anio,
        tipo=vehicle.tipo,
        mensaje="Vehiculo registrado exitosamente.",
    )


def list_client_vehicles(*, cliente_id: int, db: Session) -> list[VehicleListItemResponse]:
    # Obtiene vehículos del cliente para selección en reportes móviles.
    repository = VehicleRepository(db)
    vehicles = repository.list_by_cliente_id(cliente_id)

    return [
        VehicleListItemResponse(
            placa=item.placa,
            marca=item.marca,
            modelo=item.modelo,
            anio=item.anio,
            tipo=item.tipo,
        )
        for item in vehicles
    ]
