# Repositorio para persistencia de incidentes y trazabilidad del CU4.

from sqlalchemy.orm import Session

from app.models.incident import EstadoServicio, Evidencia, Historial, Incidente
from app.models.vehicle import Vehiculo


class IncidentRepository:
    # Encapsula acceso a tablas incidente/evidencia/historial.

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_vehicle_for_client(self, placa: str, cliente_id: int) -> Vehiculo | None:
        # Verifica que el vehiculo pertenezca al cliente autenticado.
        return (
            self.db.query(Vehiculo)
            .filter(
                Vehiculo.placa == placa,
                Vehiculo.cliente_id == cliente_id,
            )
            .first()
        )

    def get_or_create_service_state(self, *, name: str, description: str) -> EstadoServicio:
        # Obtiene estado del catalogo o lo crea en ambientes nuevos.
        state = self.db.query(EstadoServicio).filter(EstadoServicio.nombre == name).first()
        if state:
            return state

        state = EstadoServicio(nombre=name, descripcion=description)
        self.db.add(state)
        self.db.flush()
        return state

    def create_incident(
        self,
        *,
        cliente_id: int,
        vehiculo_placa: str,
        estado_servicio_id: int,
        tipo_problema: str,
        descripcion: str | None,
        ubicacion: str | None,
        latitud: float,
        longitud: float,
        prioridad: int = 2,
    ) -> Incidente:
        # Inserta registro principal del incidente con datos del reporte inicial.
        incident = Incidente(
            cliente_id=cliente_id,
            vehiculo_placa=vehiculo_placa,
            estado_servicio_id=estado_servicio_id,
            tipo_problema=tipo_problema,
            descripcion=descripcion,
            ubicacion=ubicacion,
            latitud=latitud,
            longitud=longitud,
            prioridad=prioridad,
        )
        self.db.add(incident)
        self.db.flush()
        return incident

    def create_evidence(
        self,
        *,
        incidente_id: int,
        tipo: str,
        url: str | None,
        texto_extraido: str | None,
    ) -> Evidencia:
        # Guarda evidencia adjunta para enriquecer el procesamiento del incidente.
        evidence = Evidencia(
            incidente_id=incidente_id,
            tipo=tipo,
            url=url,
            texto_extraido=texto_extraido,
        )
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def create_history(
        self,
        *,
        incidente_id: int,
        accion: str,
        descripcion: str,
        actor_usuario_id: int,
    ) -> Historial:
        # Registra evento de auditoria para trazabilidad completa del flujo.
        history = Historial(
            incidente_id=incidente_id,
            accion=accion,
            descripcion=descripcion,
            actor_usuario_id=actor_usuario_id,
        )
        self.db.add(history)
        self.db.flush()
        return history

    def get_service_state_name(self, state_id: int) -> str:
        # Recupera nombre legible del estado para respuesta de API.
        state = self.db.query(EstadoServicio).filter(EstadoServicio.id == state_id).first()
        return state.nombre if state else "pendiente"
