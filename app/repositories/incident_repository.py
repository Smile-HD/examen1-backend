# Repositorio para persistencia de incidentes y trazabilidad del CU4.

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.incident import (
    EstadoServicio,
    Evidencia,
    Historial,
    Incidente,
    MetricaServicio,
    Solicitud,
    TecnicoUbicacion,
)
from app.models.user import Servicio, Taller, TallerServicio, Tecnico, Transporte, Usuario
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

    def get_incident_for_client(self, incidente_id: int, cliente_id: int) -> Incidente | None:
        # Obtiene incidente garantizando pertenencia al cliente autenticado.
        return (
            self.db.query(Incidente)
            .filter(
                Incidente.id == incidente_id,
                Incidente.cliente_id == cliente_id,
            )
            .first()
        )

    def get_incident_by_id(self, incidente_id: int) -> Incidente | None:
        # Obtiene incidente por id sin filtrar actor.
        return self.db.query(Incidente).filter(Incidente.id == incidente_id).first()

    def get_vehicle_by_plate(self, placa: str) -> Vehiculo | None:
        # Recupera vehiculo por placa para enriquecer detalle de incidente.
        return self.db.query(Vehiculo).filter(Vehiculo.placa == placa).first()

    def list_client_requests(self, cliente_id: int) -> list[dict[str, object]]:
        # Lista solicitudes de talleres para incidentes del cliente autenticado.
        rows = (
            self.db.query(Solicitud, Incidente, Taller)
            .join(Incidente, Incidente.id == Solicitud.incidente_id)
            .outerjoin(Taller, Taller.id == Solicitud.taller_id)
            .filter(Incidente.cliente_id == cliente_id)
            .order_by(Solicitud.fecha_asignacion.desc())
            .all()
        )

        data: list[dict[str, object]] = []
        for solicitud, incidente, taller in rows:
            data.append(
                {
                    "solicitud": solicitud,
                    "incidente": incidente,
                    "taller_nombre": taller.nombre if taller else None,
                }
            )
        return data

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
        info_reintentos: int = 0,
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
            info_reintentos=info_reintentos,
        )
        self.db.add(incident)
        self.db.flush()
        return incident

    def update_incident(self, incident: Incidente, **fields: object) -> Incidente:
        # Actualiza campos puntuales del incidente para evitar duplicar registros.
        for field_name, field_value in fields.items():
            setattr(incident, field_name, field_value)
        self.db.flush()
        return incident

    def list_incident_evidence(self, incidente_id: int) -> list[Evidencia]:
        # Recupera evidencias en orden cronologico para armar detalle a cliente/taller.
        return (
            self.db.query(Evidencia)
            .filter(Evidencia.incidente_id == incidente_id)
            .order_by(Evidencia.fecha_subida.asc())
            .all()
        )

    def list_incident_history(self, incidente_id: int) -> list[Historial]:
        # Recupera timeline completo del incidente para cliente/taller.
        return (
            self.db.query(Historial)
            .filter(Historial.incidente_id == incidente_id)
            .order_by(Historial.fecha_hora.asc())
            .all()
        )

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

    def list_active_workshops_with_context(self) -> list[dict[str, object]]:
        # Recupera talleres activos con carga actual y servicios para fase de candidatos.
        workshops = self.db.query(Taller).filter(Taller.estado == "activo").all()
        if not workshops:
            return []

        workshop_ids = [workshop.id for workshop in workshops]

        # Carga operativa: solicitudes activas por taller.
        active_states = ["enviada", "pendiente", "aceptada"]
        load_rows = (
            self.db.query(Solicitud.taller_id, func.count(Solicitud.id))
            .filter(
                Solicitud.taller_id.in_(workshop_ids),
                Solicitud.estado.in_(active_states),
            )
            .group_by(Solicitud.taller_id)
            .all()
        )
        open_requests_by_workshop = {taller_id: int(count) for taller_id, count in load_rows}

        # Servicios disponibles por taller.
        service_rows = (
            self.db.query(TallerServicio.taller_id, Servicio.nombre)
            .join(Servicio, Servicio.id == TallerServicio.servicio_id)
            .filter(TallerServicio.taller_id.in_(workshop_ids))
            .all()
        )
        services_by_workshop: dict[int, set[str]] = {workshop_id: set() for workshop_id in workshop_ids}
        for workshop_id, service_name in service_rows:
            services_by_workshop.setdefault(workshop_id, set()).add(service_name.strip().lower())

        response: list[dict[str, object]] = []
        for workshop in workshops:
            response.append(
                {
                    "taller_id": workshop.id,
                    "nombre_taller": workshop.nombre,
                    "ubicacion": workshop.ubicacion,
                    "estado": workshop.estado,
                    "open_requests": open_requests_by_workshop.get(workshop.id, 0),
                    "services": sorted(services_by_workshop.get(workshop.id, set())),
                }
            )

        return response

    def list_incoming_requests_for_workshop(self, taller_id: int) -> list[dict[str, object]]:
        # Lista solicitudes activas para la bandeja de notificaciones y en proceso.
        incoming_states = ["enviada", "pendiente", "aceptada", "en_camino", "en_proceso"]
        rows = (
            self.db.query(Solicitud, Incidente, Vehiculo)
            .join(Incidente, Incidente.id == Solicitud.incidente_id)
            .join(Vehiculo, Vehiculo.placa == Incidente.vehiculo_placa)
            .filter(
                Solicitud.taller_id == taller_id,
                Solicitud.estado.in_(incoming_states),
            )
            .order_by(Solicitud.fecha_asignacion.desc())
            .all()
        )

        data: list[dict[str, object]] = []
        for solicitud, incidente, vehiculo in rows:
            data.append(
                {
                    "solicitud": solicitud,
                    "incidente": incidente,
                    "vehiculo": vehiculo,
                }
            )
        return data

    def get_request_for_workshop(self, solicitud_id: int, taller_id: int) -> Solicitud | None:
        # Busca una solicitud que pertenezca al taller autenticado.
        return (
            self.db.query(Solicitud)
            .filter(
                Solicitud.id == solicitud_id,
                Solicitud.taller_id == taller_id,
            )
            .first()
        )

    def get_request_by_id(self, solicitud_id: int) -> Solicitud | None:
        # Obtiene solicitud por id sin filtrar actor.
        return self.db.query(Solicitud).filter(Solicitud.id == solicitud_id).first()

    def has_workshop_request_for_incident(self, *, taller_id: int, incidente_id: int) -> bool:
        # Valida si el taller participo en solicitudes del incidente.
        exists = (
            self.db.query(Solicitud.id)
            .filter(
                Solicitud.taller_id == taller_id,
                Solicitud.incidente_id == incidente_id,
            )
            .first()
        )
        return exists is not None

    def get_primary_assigned_request_for_incident(self, incidente_id: int) -> Solicitud | None:
        # Recupera la solicitud principal asignada/aceptada para mostrar detalle actual.
        priority_states = ["aceptada", "en_camino", "en_proceso", "finalizada"]

        for state in priority_states:
            row = (
                self.db.query(Solicitud)
                .filter(
                    Solicitud.incidente_id == incidente_id,
                    Solicitud.estado == state,
                )
                .order_by(Solicitud.id.asc())
                .first()
            )
            if row:
                return row

        return None

    def list_requests_for_incident(self, incidente_id: int) -> list[Solicitud]:
        # Recupera todas las solicitudes del incidente para aplicar reglas de concurrencia.
        return self.db.query(Solicitud).filter(Solicitud.incidente_id == incidente_id).all()

    def list_incidents_for_client(self, cliente_id: int) -> list[Incidente]:
        # Recupera incidentes del cliente para historial consolidado.
        return (
            self.db.query(Incidente)
            .filter(Incidente.cliente_id == cliente_id)
            .order_by(Incidente.fecha_hora.desc())
            .all()
        )

    def get_request_for_technician(self, solicitud_id: int, tecnico_id: int) -> Solicitud | None:
        # Busca solicitud por tecnico asignado para operaciones mobile del tecnico.
        return (
            self.db.query(Solicitud)
            .filter(
                Solicitud.id == solicitud_id,
                Solicitud.tecnico_id == tecnico_id,
            )
            .first()
        )

    def list_requests_for_technician(self, tecnico_id: int) -> list[Solicitud]:
        # Recupera solicitudes donde participo el tecnico autenticado.
        return (
            self.db.query(Solicitud)
            .filter(Solicitud.tecnico_id == tecnico_id)
            .order_by(Solicitud.fecha_asignacion.desc())
            .all()
        )

    def list_active_requests_for_technician(self, tecnico_id: int) -> list[Solicitud]:
        # Recupera solicitudes activas asignadas al tecnico autenticado.
        active_states = ["aceptada", "en_camino", "en_proceso"]
        return (
            self.db.query(Solicitud)
            .filter(
                Solicitud.tecnico_id == tecnico_id,
                Solicitud.estado.in_(active_states),
            )
            .order_by(Solicitud.fecha_asignacion.desc())
            .all()
        )

    def list_requests_for_workshop(self, taller_id: int) -> list[Solicitud]:
        # Recupera todas las solicitudes de un taller para metricas operativas.
        return (
            self.db.query(Solicitud)
            .filter(Solicitud.taller_id == taller_id)
            .order_by(Solicitud.fecha_asignacion.desc())
            .all()
        )

    def get_workshop_by_id(self, taller_id: int) -> Taller | None:
        # Obtiene informacion del taller por id.
        return self.db.query(Taller).filter(Taller.id == taller_id).first()

    def get_available_technician_for_workshop(self, taller_id: int) -> Tecnico | None:
        # Selecciona tecnico disponible dentro del taller.
        return (
            self.db.query(Tecnico)
            .filter(
                Tecnico.taller_id == taller_id,
                Tecnico.estado == "disponible",
            )
            .first()
        )

    def get_available_transport_for_workshop(self, taller_id: int) -> Transporte | None:
        # Selecciona unidad de transporte disponible dentro del taller.
        return (
            self.db.query(Transporte)
            .filter(
                Transporte.taller_id == taller_id,
                Transporte.estado == "disponible",
            )
            .first()
        )

    def update_request(self, request: Solicitud, **fields: object) -> Solicitud:
        # Actualiza campos puntuales de solicitud.
        for field_name, field_value in fields.items():
            setattr(request, field_name, field_value)
        self.db.flush()
        return request

    def update_technician_state(self, technician: Tecnico, estado: str) -> Tecnico:
        # Actualiza disponibilidad del tecnico asignado.
        technician.estado = estado
        self.db.flush()
        return technician

    def get_technician_by_id(self, technician_id: int) -> Tecnico | None:
        # Recupera tecnico por id para liberar recursos al finalizar servicio.
        return self.db.query(Tecnico).filter(Tecnico.id == technician_id).first()

    def update_transport_state(self, transport: Transporte, estado: str) -> Transporte:
        # Actualiza disponibilidad del transporte asignado.
        transport.estado = estado
        self.db.flush()
        return transport

    def get_transport_by_id(self, transport_id: int) -> Transporte | None:
        # Recupera transporte por id para liberar recursos al finalizar servicio.
        return self.db.query(Transporte).filter(Transporte.id == transport_id).first()

    def list_assigned_transports_for_workshop(self, taller_id: int) -> list[Transporte]:
        # Lista transportes marcados como asignados para saneo de estado operativo.
        return (
            self.db.query(Transporte)
            .filter(
                Transporte.taller_id == taller_id,
                Transporte.estado == "asignado",
            )
            .all()
        )

    def get_metric_by_incident(self, incidente_id: int) -> MetricaServicio | None:
        # Obtiene metrica final del incidente si existe.
        return (
            self.db.query(MetricaServicio)
            .filter(MetricaServicio.incidente_id == incidente_id)
            .first()
        )

    def upsert_metric(
        self,
        *,
        incidente_id: int,
        solicitud_id: int,
        taller_id: int,
        cliente_id: int,
        tecnico_id: int | None,
        transporte_id: int | None,
        tiempo_minutos: int,
        costo_total: float,
        comision_plataforma: float,
        distancia_km: float | None,
        observaciones: str | None,
    ) -> MetricaServicio:
        # Crea o actualiza metrica de servicio para consulta de cliente y taller.
        metric = self.get_metric_by_incident(incidente_id)
        if not metric:
            metric = MetricaServicio(
                incidente_id=incidente_id,
                solicitud_id=solicitud_id,
                taller_id=taller_id,
                cliente_id=cliente_id,
                tecnico_id=tecnico_id,
                transporte_id=transporte_id,
                tiempo_minutos=tiempo_minutos,
                costo_total=costo_total,
                comision_plataforma=comision_plataforma,
                distancia_km=distancia_km,
                observaciones=observaciones,
            )
            self.db.add(metric)
            self.db.flush()
            return metric

        metric.solicitud_id = solicitud_id
        metric.taller_id = taller_id
        metric.cliente_id = cliente_id
        metric.tecnico_id = tecnico_id
        metric.transporte_id = transporte_id
        metric.tiempo_minutos = tiempo_minutos
        metric.costo_total = costo_total
        metric.comision_plataforma = comision_plataforma
        metric.distancia_km = distancia_km
        metric.observaciones = observaciones
        self.db.flush()
        return metric

    def upsert_technician_location(
        self,
        *,
        tecnico_id: int,
        latitud: float,
        longitud: float,
        solicitud_id: int | None,
        precision_metros: float | None,
    ) -> TecnicoUbicacion:
        # Registra/actualiza posicion actual enviada por el tecnico desde mobile.
        location = self.db.query(TecnicoUbicacion).filter(TecnicoUbicacion.tecnico_id == tecnico_id).first()
        if not location:
            location = TecnicoUbicacion(
                tecnico_id=tecnico_id,
                latitud=latitud,
                longitud=longitud,
                solicitud_id=solicitud_id,
                precision_metros=precision_metros,
            )
            self.db.add(location)
            self.db.flush()
            return location

        location.latitud = latitud
        location.longitud = longitud
        location.solicitud_id = solicitud_id
        location.precision_metros = precision_metros
        location.actualizada_en = func.now()
        self.db.flush()
        return location

    def get_technician_location(self, tecnico_id: int) -> TecnicoUbicacion | None:
        # Recupera la ultima ubicacion persistida del tecnico.
        return (
            self.db.query(TecnicoUbicacion)
            .filter(TecnicoUbicacion.tecnico_id == tecnico_id)
            .first()
        )

    def list_workshop_technician_locations(self, taller_id: int) -> list[dict[str, object]]:
        # Devuelve ubicacion reportada de tecnicos del taller autenticado.
        rows = (
            self.db.query(Tecnico, Usuario, TecnicoUbicacion)
            .join(Usuario, Usuario.id == Tecnico.id)
            .outerjoin(TecnicoUbicacion, TecnicoUbicacion.tecnico_id == Tecnico.id)
            .filter(Tecnico.taller_id == taller_id)
            .order_by(Usuario.nombre.asc())
            .all()
        )
        data: list[dict[str, object]] = []
        for tecnico, usuario, ubicacion in rows:
            data.append(
                {
                    "tecnico": tecnico,
                    "usuario": usuario,
                    "ubicacion": ubicacion,
                }
            )
        return data

    def list_workshop_history(self, taller_id: int) -> list[Historial]:
        # Historial operativo filtrado por taller.
        return (
            self.db.query(Historial)
            .filter(Historial.taller_id == taller_id)
            .order_by(Historial.fecha_hora.desc())
            .all()
        )

    def list_client_history(self, cliente_id: int) -> list[Historial]:
        # Historial del cliente autenticado.
        return (
            self.db.query(Historial)
            .filter(Historial.cliente_id == cliente_id)
            .order_by(Historial.fecha_hora.desc())
            .all()
        )

    def get_existing_active_request(
        self,
        *,
        incidente_id: int,
        taller_id: int,
    ) -> Solicitud | None:
        # Evita duplicar solicitudes activas al mismo taller para un incidente.
        active_states = ["enviada", "pendiente", "aceptada"]
        return (
            self.db.query(Solicitud)
            .filter(
                Solicitud.incidente_id == incidente_id,
                Solicitud.taller_id == taller_id,
                Solicitud.estado.in_(active_states),
            )
            .first()
        )

    def create_request_to_workshop(
        self,
        *,
        incidente_id: int,
        taller_id: int,
        estado: str = "enviada",
    ) -> Solicitud:
        # Inserta solicitud dirigida al taller seleccionado por el cliente.
        request = Solicitud(
            incidente_id=incidente_id,
            taller_id=taller_id,
            estado=estado,
        )
        self.db.add(request)
        self.db.flush()
        return request

    def create_history(
        self,
        *,
        incidente_id: int | None,
        taller_id: int | None = None,
        cliente_id: int | None = None,
        accion: str,
        descripcion: str | None,
        actor_usuario_id: int | None,
    ) -> Historial:
        # Registra evento de auditoria para trazabilidad completa del flujo.
        history = Historial(
            incidente_id=incidente_id,
            taller_id=taller_id,
            cliente_id=cliente_id,
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
