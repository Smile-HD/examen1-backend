# Servicio de negocio para gestion de tecnicos y unidades del taller.

import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workshop_schemas import (
    WorkshopProfileResponse,
    WorkshopProfileUpdateRequest,
    WorkshopServiceItemResponse,
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


class WorkshopProfileNotFoundError(Exception):
    # Error cuando no existe perfil taller para el usuario autenticado.
    pass


class InvalidWorkshopServiceSelectionError(Exception):
    # Error cuando se intenta guardar servicios inexistentes.
    pass


_LOCATION_COORDS_PATTERN = re.compile(
    r"\(lat:\s*(-?\d+(?:\.\d+)?)\s*,\s*lng:\s*(-?\d+(?:\.\d+)?)\)",
    flags=re.IGNORECASE,
)

_DEFAULT_WORKSHOP_SERVICES = [
    "llanta",
    "bateria",
    "motor",
    "grua",
    "frenos",
    "electricidad",
    "combustible",
    "cerrajeria",
]


def _ensure_workshop_service_catalog(repository: WorkshopRepository) -> list:
    # Asegura un catalogo base minimo para que el taller pueda marcar servicios.
    for raw_name in _DEFAULT_WORKSHOP_SERVICES:
        name = raw_name.strip().lower()
        if not repository.get_service_by_name(name):
            repository.create_service(name)
    return repository.list_services()


def _compose_workshop_location_text(
    *,
    ubicacion_texto: str | None,
    latitud: float | None,
    longitud: float | None,
) -> str | None:
    # Serializa la ubicacion del taller en un formato legible y parseable.
    text = (ubicacion_texto or "").strip()
    if latitud is None or longitud is None:
        return text or None

    coords_text = f"(lat: {latitud:.6f}, lng: {longitud:.6f})"
    if text:
        return f"{text} {coords_text}"
    return coords_text


def _parse_workshop_location_text(raw_location: str | None) -> tuple[str | None, float | None, float | None]:
    # Extrae coordenadas del texto de ubicacion del taller si estan presentes.
    if not raw_location:
        return None, None, None

    normalized = raw_location.strip()
    match = _LOCATION_COORDS_PATTERN.search(normalized)
    if not match:
        return normalized or None, None, None

    latitud = float(match.group(1))
    longitud = float(match.group(2))
    clean_text = _LOCATION_COORDS_PATTERN.sub("", normalized).strip()
    return (clean_text or None, latitud, longitud)


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


def get_workshop_profile(
    *,
    taller_id: int,
    db: Session,
) -> WorkshopProfileResponse:
    # Recupera perfil del taller y catalogo de servicios disponibles.
    repository = WorkshopRepository(db)
    workshop = repository.get_workshop_by_id(taller_id)
    if not workshop:
        raise WorkshopProfileNotFoundError("Perfil de taller no encontrado para el usuario autenticado.")

    services = _ensure_workshop_service_catalog(repository)
    offered_ids = repository.list_workshop_service_ids(taller_id)
    location_text, latitud, longitud = _parse_workshop_location_text(workshop.ubicacion)

    db.commit()

    return WorkshopProfileResponse(
        taller_id=workshop.id,
        nombre_taller=workshop.nombre,
        ubicacion_texto=location_text,
        latitud=latitud,
        longitud=longitud,
        servicios_catalogo=[
            WorkshopServiceItemResponse(id=item.id, nombre=item.nombre)
            for item in services
        ],
        servicios_ofrecidos_ids=offered_ids,
    )


def update_workshop_profile(
    payload: WorkshopProfileUpdateRequest,
    *,
    taller_id: int,
    db: Session,
) -> WorkshopProfileResponse:
    # Actualiza nombre/ubicacion y servicios ofrecidos por el taller.
    repository = WorkshopRepository(db)
    incident_repository = IncidentRepository(db)

    workshop = repository.get_workshop_by_id(taller_id)
    if not workshop:
        raise WorkshopProfileNotFoundError("Perfil de taller no encontrado para el usuario autenticado.")

    services = _ensure_workshop_service_catalog(repository)
    available_ids = {int(item.id) for item in services}

    requested_ids = [int(service_id) for service_id in payload.servicios_ofrecidos_ids]
    if any(service_id not in available_ids for service_id in requested_ids):
        raise InvalidWorkshopServiceSelectionError(
            "Uno o más servicios seleccionados no existen en el catálogo."
        )

    previous_name = workshop.nombre
    previous_location = workshop.ubicacion

    try:
        new_location = _compose_workshop_location_text(
            ubicacion_texto=payload.ubicacion_texto,
            latitud=payload.latitud,
            longitud=payload.longitud,
        )

        repository.update_workshop_profile(
            workshop,
            nombre=payload.nombre_taller,
            ubicacion=new_location,
        )
        repository.replace_workshop_services(taller_id, requested_ids)

        incident_repository.create_history(
            incidente_id=None,
            taller_id=taller_id,
            cliente_id=None,
            accion="perfil_taller_actualizado",
            descripcion=(
                f"Perfil actualizado: nombre '{previous_name}' -> '{payload.nombre_taller}', "
                f"ubicacion '{previous_location or '-'}' -> '{new_location or '-'}', "
                f"servicios={len(requested_ids)}."
            ),
            actor_usuario_id=taller_id,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return get_workshop_profile(taller_id=taller_id, db=db)

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
