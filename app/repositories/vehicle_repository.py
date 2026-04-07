# Repositorio para operaciones de vehiculos.

from sqlalchemy.orm import Session

from app.models.vehicle import Vehiculo


class VehicleRepository:
    # Encapsula consultas y escrituras de la tabla vehiculo.

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_plate(self, plate: str) -> Vehiculo | None:
        # Verifica existencia de placa para garantizar unicidad.
        return self.db.query(Vehiculo).filter(Vehiculo.placa == plate).first()

    def list_by_cliente_id(self, cliente_id: int) -> list[Vehiculo]:
        # Retorna vehículos registrados del cliente ordenados por placa.
        return (
            self.db.query(Vehiculo)
            .filter(Vehiculo.cliente_id == cliente_id)
            .order_by(Vehiculo.placa.asc())
            .all()
        )

    def create(
        self,
        *,
        cliente_id: int,
        placa: str,
        marca: str,
        modelo: str,
        anio: int,
        tipo: str,
    ) -> Vehiculo:
        # Inserta vehiculo asociado al cliente autenticado.
        vehicle = Vehiculo(
            cliente_id=cliente_id,
            placa=placa,
            marca=marca,
            modelo=modelo,
            anio=anio,
            tipo=tipo,
        )
        self.db.add(vehicle)
        self.db.flush()
        return vehicle
