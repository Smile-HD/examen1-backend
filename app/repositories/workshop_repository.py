# Repositorio para gestion operativa de talleres.

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import Cliente, Servicio, Taller, TallerServicio, Tecnico, Transporte, Usuario


class WorkshopRepository:
    # Encapsula acceso de datos para tecnicos y unidades del taller.

    def __init__(self, db: Session) -> None:
        self.db = db

    def search_technicians_by_name(self, full_name_query: str) -> list[Usuario]:
        # Busca usuarios elegibles para plantilla del taller por nombre.
        # Incluye tecnicos sin taller y clientes sin perfil tecnico.
        normalized = "%" + " ".join(full_name_query.strip().split()) + "%"      
        return (
            self.db.query(Usuario)
            .join(Cliente, Usuario.id == Cliente.id)
            .outerjoin(Tecnico, Usuario.id == Tecnico.id)
            .filter(Usuario.nombre.ilike(normalized))
            .filter(Tecnico.taller_id == None)
            .order_by(Usuario.nombre.asc())
            .all()
        )

    def get_technician_by_id(self, tecnico_id: int) -> Tecnico | None:
        # Obtiene perfil tecnico para asignacion al taller.
        return self.db.query(Tecnico).filter(Tecnico.id == tecnico_id).first()

    def get_user_by_id(self, user_id: int) -> Usuario | None:
        # Obtiene datos base del usuario por id.
        return self.db.query(Usuario).filter(Usuario.id == user_id).first()

    def get_workshop_by_id(self, taller_id: int) -> Taller | None:
        # Obtiene el perfil del taller autenticado.
        return self.db.query(Taller).filter(Taller.id == taller_id).first()

    def list_services(self) -> list[Servicio]:
        # Lista catalogo de servicios disponibles para talleres.
        return self.db.query(Servicio).order_by(Servicio.nombre.asc()).all()

    def get_service_by_name(self, name: str) -> Servicio | None:
        # Busca servicio por nombre normalizado.
        return self.db.query(Servicio).filter(Servicio.nombre == name).first()

    def get_service_by_normalized_name(self, name: str) -> Servicio | None:
        # Busca servicio ignorando mayusculas/minusculas para evitar duplicados semanticos.
        normalized = name.strip().lower()
        return (
            self.db.query(Servicio)
            .filter(func.lower(Servicio.nombre) == normalized)
            .first()
        )

    def create_service(self, name: str) -> Servicio:
        # Crea un servicio en el catalogo global.
        service = Servicio(nombre=name)
        self.db.add(service)
        self.db.flush()
        return service

    def list_workshop_service_ids(self, taller_id: int) -> list[int]:
        # Lista ids de servicios ofrecidos por el taller.
        rows = (
            self.db.query(TallerServicio.servicio_id)
            .filter(TallerServicio.taller_id == taller_id)
            .all()
        )
        return [int(row[0]) for row in rows]

    def replace_workshop_services(self, taller_id: int, service_ids: list[int]) -> None:
        # Reemplaza por completo los servicios ofrecidos por el taller.
        (
            self.db.query(TallerServicio)
            .filter(TallerServicio.taller_id == taller_id)
            .delete(synchronize_session=False)
        )

        unique_service_ids: list[int] = []
        seen: set[int] = set()
        for service_id in service_ids:
            if service_id in seen:
                continue
            seen.add(service_id)
            unique_service_ids.append(service_id)

        for service_id in unique_service_ids:
            self.db.add(TallerServicio(taller_id=taller_id, servicio_id=service_id))

        self.db.flush()

    def update_workshop_profile(
        self,
        workshop: Taller,
        *,
        nombre: str,
        qr_image_url: str | None,
        ubicacion: str | None,
        latitud: float | None,
        longitud: float | None,
    ) -> Taller:
        # Actualiza nombre y ubicacion textual del taller.
        workshop.nombre = nombre
        workshop.qr_image_url = qr_image_url
        workshop.ubicacion = ubicacion
        workshop.latitud = latitud
        workshop.longitud = longitud
        self.db.flush()
        return workshop

    def list_workshop_technicians(self, taller_id: int) -> list[tuple[Tecnico, Usuario]]:
        # Lista tecnicos asignados al taller autenticado.
        return (
            self.db.query(Tecnico, Usuario)
            .join(Usuario, Usuario.id == Tecnico.id)
            .filter(Tecnico.taller_id == taller_id)
            .order_by(Usuario.nombre.asc())
            .all()
        )

    def assign_technician_to_workshop(self, tecnico: Tecnico, taller_id: int) -> Tecnico:
        # Asigna tecnico al taller y lo deja disponible para atenciones.
        tecnico.taller_id = taller_id
        if tecnico.estado not in {"disponible", "asignado"}:
            tecnico.estado = "disponible"
        self.db.flush()
        return tecnico

    def unassign_technician_from_workshop(self, tecnico: Tecnico) -> Tecnico:
        # Desvincula tecnico del taller para baja de plantilla.
        tecnico.taller_id = None
        tecnico.estado = "disponible"
        self.db.flush()
        return tecnico

    def create_workshop_vehicle(
        self,
        *,
        taller_id: int,
        tipo: str,
        placa: str,
        estado: str,
    ) -> Transporte:
        # Registra una unidad de servicio del taller.
        vehicle = Transporte(
            taller_id=taller_id,
            tipo=tipo,
            placa=placa,
            estado=estado,
        )
        self.db.add(vehicle)
        self.db.flush()
        return vehicle

    def list_workshop_vehicles(self, taller_id: int) -> list[Transporte]:
        # Lista las unidades registradas para el taller.
        return (
            self.db.query(Transporte)
            .filter(Transporte.taller_id == taller_id)
            .order_by(Transporte.id.asc())
            .all()
        )

    def get_vehicle_by_id_for_workshop(self, vehicle_id: int, taller_id: int) -> Transporte | None:
        # Obtiene unidad por id restringida al taller autenticado.
        return (
            self.db.query(Transporte)
            .filter(
                Transporte.id == vehicle_id,
                Transporte.taller_id == taller_id,
            )
            .first()
        )

    def get_vehicle_by_plate(self, plate: str) -> Transporte | None:
        # Verifica unicidad global de placa de transporte.
        return self.db.query(Transporte).filter(Transporte.placa == plate).first()

    def update_workshop_vehicle(
        self,
        vehicle: Transporte,
        *,
        tipo: str | None,
        placa: str | None,
        estado: str | None,
    ) -> Transporte:
        # Actualiza datos de la unidad del taller.
        if tipo is not None:
            vehicle.tipo = tipo
        if placa is not None:
            vehicle.placa = placa
        if estado is not None:
            vehicle.estado = estado
        self.db.flush()
        return vehicle

    def delete_workshop_vehicle(self, vehicle: Transporte) -> None:
        # Elimina unidad del taller.
        self.db.delete(vehicle)
        self.db.flush()

    def update_workshop_status(self, workshop: Taller, estado: str) -> Taller:
        # Actualiza el estado del taller (activo/inactivo).
        workshop.estado = estado
        self.db.flush()
        return workshop
