# Repositorio para gestion operativa de talleres.

from sqlalchemy.orm import Session

from app.models.user import Cliente, Tecnico, Transporte, Usuario


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
