# Servicio de negocio para gestion de tecnicos y unidades del taller.

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workshop_schemas import (
    WorkshopTechnicianAssignResponse,
    WorkshopTechnicianCandidateResponse,
    WorkshopTechnicianListItemResponse,
    WorkshopTechnicianLocationItem,
    WorkshopTechnicianUnassignRequest,
    WorkshopTechnicianUnassignResponse,
    WorkshopHistoryItem,
    WorkshopHistoryResponse,
    WorkshopVehicleCreateRequest,
    WorkshopVehicleDeleteResponse,
    WorkshopVehicleResponse,
    WorkshopVehicleUpdateRequest,
)
from app.repositories.incident_repository import IncidentRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workshop_repository import WorkshopRepository


class TechnicianNotFoundError(Exception):
    # Error cuando el tecnico no existe en la base de datos.
    pass


class TechnicianAlreadyAssignedError(Exception):
    # Error cuando el tecnico ya pertenece a otro taller.
    pass


class TechnicianEmailMismatchError(Exception):
    # Error cuando el correo no coincide con el tecnico seleccionado.
    pass


class TechnicianNotAssignedToWorkshopError(Exception):
    # Error cuando el tecnico no pertenece al taller autenticado.
    pass


class WorkshopVehicleAlreadyExistsError(Exception):
    # Error cuando la placa de la unidad ya existe.
    pass


class WorkshopVehicleNotFoundError(Exception):
    # Error cuando la unidad no pertenece al taller o no existe.
    pass


def search_technicians(
    query: str,
    *,
    db: Session,
) -> list[WorkshopTechnicianCandidateResponse]:
    # Busca clientes registrados por nombre para asignar como tecnicos
    repository = WorkshopRepository(db)
    users = repository.search_technicians_by_name(query)

    return [
        WorkshopTechnicianCandidateResponse(
            usuario_id=user.id,
            nombre=user.nombre,
            correo=user.correo,
        )
        for user in users
    ]

def assign_technician_to_workshop(
    usuario_id: int,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopTechnicianAssignResponse:
    # Asigna tecnico existente al taller autenticado.
    repository = WorkshopRepository(db)
    incident_repository = IncidentRepository(db)
    user = repository.get_user_by_id(usuario_id)
    if not user:
        raise TechnicianNotFoundError("Tecnico no encontrado.")

    technician = repository.get_technician_by_id(usuario_id)
    if technician and technician.taller_id is not None:
        if technician.taller_id == taller_id:
            raise TechnicianAlreadyAssignedError("El tecnico ya esta asignado a este taller.")
        raise TechnicianAlreadyAssignedError("El tecnico ya esta asignado a otro taller.")

    from app.models.user import Tecnico
    from app.repositories.user_repository import UserRepository
    try:
        if technician and technician.taller_id is None:
            new_tech = repository.assign_technician_to_workshop(technician, taller_id)
        else:
            new_tech = Tecnico(id=user.id, taller_id=taller_id, estado="disponible")
            db.add(new_tech)
        
        # Asignar rol tecnico al usuario para el dashboard / login
        user_repo = UserRepository(db)
        tech_role = user_repo.get_or_create_role("tecnico", "Personal afiliado a un taller mecanico.")
        user_repo.assign_role_to_user(usuario_id, tech_role.id)

        incident_repository.create_history(
            incidente_id=None,
            taller_id=taller_id,
            cliente_id=None,
            accion="tecnico_contratado",
            descripcion=f"Taller vinculo tecnico {usuario_id}.",
            actor_usuario_id=taller_id,
        )
        db.commit()
        db.refresh(new_tech)
    except Exception:
        db.rollback()
        raise

    return WorkshopTechnicianAssignResponse(
        tecnico_id=new_tech.id,
        taller_id=taller_id,
        estado=new_tech.estado,
        mensaje="Tecnico asignado correctamente al taller.",
    )

def unassign_technician_from_workshop(
    payload: WorkshopTechnicianUnassignRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopTechnicianUnassignResponse:
    # Desasigna tecnico del taller autenticado para baja de plantilla.
    repository = WorkshopRepository(db)
    incident_repository = IncidentRepository(db)
    user_repository = UserRepository(db)

    technician = repository.get_technician_by_id(payload.tecnico_id)
    if not technician:
        raise TechnicianNotFoundError("Tecnico no encontrado.")
    if technician.taller_id != taller_id:
        raise TechnicianNotAssignedToWorkshopError(
            "El tecnico no esta asignado al taller autenticado."
        )

    try:
        repository.unassign_technician_from_workshop(technician)

        # Quitar cualquier variante del rol tecnico para evitar privilegios residuales.
        technician_roles = user_repository.get_roles_by_normalized_name("tecnico")
        for technician_role in technician_roles:
            user_repository.remove_role_from_user(technician.id, technician_role.id)

        incident_repository.create_history(
            incidente_id=None,
            taller_id=taller_id,
            cliente_id=None,
            accion="tecnico_desasignado",
            descripcion=(
                f"Taller desvinculo tecnico {payload.tecnico_id}."
                + (f" Motivo: {payload.motivo}" if payload.motivo else "")
            ),
            actor_usuario_id=taller_id,
        )
        db.commit()
        db.refresh(technician)
    except Exception:
        db.rollback()
        raise

    return WorkshopTechnicianUnassignResponse(
        tecnico_id=technician.id,
        taller_id=taller_id,
        estado=technician.estado,
        mensaje="Tecnico desasignado correctamente del taller.",
    )


def list_workshop_technicians(*, taller_id: int, db: Session) -> list[WorkshopTechnicianListItemResponse]:
    # Lista tecnicos ya vinculados al taller autenticado.
    repository = WorkshopRepository(db)
    rows = repository.list_workshop_technicians(taller_id)

    return [
        WorkshopTechnicianListItemResponse(
            tecnico_id=tecnico.id,
            nombre=user.nombre,
            correo=user.correo,
            estado=tecnico.estado,
        )
        for tecnico, user in rows
    ]


def create_workshop_vehicle(
    payload: WorkshopVehicleCreateRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopVehicleResponse:
    # Crea unidad de servicio para el taller autenticado.
    repository = WorkshopRepository(db)
    incident_repository = IncidentRepository(db)
    plate = payload.placa.strip().upper()
    if repository.get_vehicle_by_plate(plate):
        raise WorkshopVehicleAlreadyExistsError("La placa de la unidad ya se encuentra registrada.")

    state = (payload.estado or "disponible").strip().lower()
    if state not in {"disponible", "asignado", "mantenimiento", "inactivo"}:
        state = "disponible"

    try:
        vehicle = repository.create_workshop_vehicle(
            taller_id=taller_id,
            tipo=payload.tipo.strip().lower(),
            placa=plate,
            estado=state,
        )
        incident_repository.create_history(
            incidente_id=None,
            taller_id=taller_id,
            cliente_id=None,
            accion="vehiculo_servicio_registrado",
            descripcion=f"Taller registro unidad {plate} tipo={payload.tipo.strip().lower()}.",
            actor_usuario_id=taller_id,
        )
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise WorkshopVehicleAlreadyExistsError("La placa de la unidad ya se encuentra registrada.") from exc
    except Exception:
        db.rollback()
        raise

    return WorkshopVehicleResponse(
        id=vehicle.id,
        taller_id=vehicle.taller_id,
        tipo=vehicle.tipo,
        placa=vehicle.placa,
        estado=vehicle.estado,
    )


def list_workshop_vehicles(*, taller_id: int, db: Session) -> list[WorkshopVehicleResponse]:
    # Lista unidades de servicio del taller.
    repository = WorkshopRepository(db)
    rows = repository.list_workshop_vehicles(taller_id)

    return [
        WorkshopVehicleResponse(
            id=item.id,
            taller_id=item.taller_id,
            tipo=item.tipo,
            placa=item.placa,
            estado=item.estado,
        )
        for item in rows
    ]


def update_workshop_vehicle(
    vehicle_id: int,
    payload: WorkshopVehicleUpdateRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopVehicleResponse:
    # Actualiza datos de una unidad del taller autenticado.
    repository = WorkshopRepository(db)
    incident_repository = IncidentRepository(db)
    vehicle = repository.get_vehicle_by_id_for_workshop(vehicle_id, taller_id)
    if not vehicle:
        raise WorkshopVehicleNotFoundError("Unidad no encontrada para el taller autenticado.")

    next_plate = payload.placa.strip().upper() if payload.placa else None
    if next_plate and next_plate != vehicle.placa and repository.get_vehicle_by_plate(next_plate):
        raise WorkshopVehicleAlreadyExistsError("La placa de la unidad ya se encuentra registrada.")

    next_state = payload.estado.strip().lower() if payload.estado else None
    if next_state and next_state not in {"disponible", "asignado", "mantenimiento", "inactivo"}:
        next_state = "disponible"

    try:
        previous_tipo = vehicle.tipo
        previous_placa = vehicle.placa
        previous_estado = vehicle.estado
        repository.update_workshop_vehicle(
            vehicle,
            tipo=payload.tipo.strip().lower() if payload.tipo else None,
            placa=next_plate,
            estado=next_state,
        )
        incident_repository.create_history(
            incidente_id=None,
            taller_id=taller_id,
            cliente_id=None,
            accion="vehiculo_servicio_actualizado",
            descripcion=(
                "Actualizacion unidad "
                f"{previous_placa}->{vehicle.placa}, tipo {previous_tipo}->{vehicle.tipo}, "
                f"estado {previous_estado}->{vehicle.estado}."
            ),
            actor_usuario_id=taller_id,
        )
        db.commit()
        db.refresh(vehicle)
    except IntegrityError as exc:
        db.rollback()
        raise WorkshopVehicleAlreadyExistsError("La placa de la unidad ya se encuentra registrada.") from exc
    except Exception:
        db.rollback()
        raise

    return WorkshopVehicleResponse(
        id=vehicle.id,
        taller_id=vehicle.taller_id,
        tipo=vehicle.tipo,
        placa=vehicle.placa,
        estado=vehicle.estado,
    )


def delete_workshop_vehicle(
    vehicle_id: int,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopVehicleDeleteResponse:
    # Elimina unidad del taller autenticado.
    repository = WorkshopRepository(db)
    incident_repository = IncidentRepository(db)
    vehicle = repository.get_vehicle_by_id_for_workshop(vehicle_id, taller_id)
    if not vehicle:
        raise WorkshopVehicleNotFoundError("Unidad no encontrada para el taller autenticado.")

    deleted_id = vehicle.id
    deleted_plate = vehicle.placa
    try:
        repository.delete_workshop_vehicle(vehicle)
        incident_repository.create_history(
            incidente_id=None,
            taller_id=taller_id,
            cliente_id=None,
            accion="vehiculo_servicio_eliminado",
            descripcion=f"Taller elimino unidad {deleted_plate}.",
            actor_usuario_id=taller_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return WorkshopVehicleDeleteResponse(
        id=deleted_id,
        mensaje="Unidad eliminada correctamente.",
    )


def list_workshop_history(*, taller_id: int, db: Session) -> WorkshopHistoryResponse:
    # Devuelve historial operativo del taller autenticado.
    repository = IncidentRepository(db)
    rows = repository.list_workshop_history(taller_id)
    return WorkshopHistoryResponse(
        total=len(rows),
        eventos=[
            WorkshopHistoryItem(
                historial_id=item.id,
                incidente_id=item.incidente_id,
                accion=item.accion,
                descripcion=item.descripcion,
                fecha_hora=item.fecha_hora.isoformat(),
                actor_usuario_id=item.actor_usuario_id,
            )
            for item in rows
        ],
    )


def list_workshop_technician_locations(
    *,
    taller_id: int,
    db: Session,
) -> list[WorkshopTechnicianLocationItem]:
    # Lista ubicaciones reportadas en la memoria local, ocultando quienes no compartan.
    repository = WorkshopRepository(db)
    technicians = repository.list_workshop_technicians(taller_id)
    
    from app.services.location_cache import ACTIVE_TECHNICIAN_LOCATIONS
    
    result: list[WorkshopTechnicianLocationItem] = []
    
    for tecnico, user in technicians:
        mem_loc = ACTIVE_TECHNICIAN_LOCATIONS.get(tecnico.id)
        if mem_loc:
            # Solo los guardamos si activaron su ubicacion y esta en memoria activa
            result.append(
                WorkshopTechnicianLocationItem(
                    tecnico_id=tecnico.id,
                    nombre=user.nombre,
                    correo=user.correo,
                    estado=tecnico.estado,
                    solicitud_id=mem_loc.solicitud_id,
                    latitud=mem_loc.latitud,
                    longitud=mem_loc.longitud,
                    precision_metros=mem_loc.precision_metros,
                    actualizada_en=mem_loc.actualizada_en.isoformat(),
                )
            )
            
    return result
