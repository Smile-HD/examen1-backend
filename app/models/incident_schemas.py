# Esquemas para CU4: Reportar emergencia desde app movil.

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class IncidentReportRequest(BaseModel):
    # Datos del reporte inicial enviados desde app movil.

    vehiculo_placa: str = Field(min_length=5, max_length=10)
    ubicacion: str | None = Field(default=None, max_length=1000)
    referencia: str | None = Field(default=None, max_length=500)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    imagen_url: str | None = Field(default=None, max_length=2000)
    audio_url: str | None = Field(default=None, max_length=2000)
    texto_usuario: str | None = Field(default=None, max_length=5000)

    @field_validator("vehiculo_placa")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        # Estandariza placa para que coincida con registros del cliente.
        return value.strip().upper()

    @field_validator("imagen_url", "audio_url", "referencia")
    @classmethod
    def normalize_optional_urls(cls, value: str | None) -> str | None:
        # Limpia URLs opcionales para persistir referencias consistentes.
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    @field_validator("texto_usuario")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        # Limpia texto adicional enviado por el cliente.
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

class IncidentReportResponse(BaseModel):
    # Confirmacion de incidente registrado y procesamiento iniciado.

    incidente_id: int
    estado: str
    tipo_problema: str
    prioridad: int
    procesamiento_ia: str
    informacion_suficiente: bool
    info_reintentos: int
    solicitar_mas_informacion: bool
    resumen_incidente: str | None
    detalle_solicitud_info: str | None
    tipo_deducido_ia: bool
    audio_transcripcion_ia: str | None
    resumen_imagen_ia: str | None
    vehiculo_placa: str
    fecha_hora: datetime
    mensaje: str


class IncidentEvidenceResubmissionRequest(BaseModel):
    # Evidencia adicional enviada cuando el incidente quedo en requiere_info.

    ubicacion: str | None = Field(default=None, max_length=1000)
    referencia: str | None = Field(default=None, max_length=500)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    imagen_url: str | None = Field(default=None, max_length=2000)
    audio_url: str | None = Field(default=None, max_length=2000)
    texto_usuario: str | None = Field(default=None, max_length=5000)

    @field_validator("ubicacion", "referencia", "imagen_url", "audio_url", "texto_usuario")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        # Limpia entradas opcionales para evitar persistencia de cadenas vacias.
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    @model_validator(mode="after")
    def ensure_at_least_one_new_input(self) -> "IncidentEvidenceResubmissionRequest":
        # Exige al menos un dato nuevo para justificar el reenvio.
        has_payload = any(
            [
                self.ubicacion,
                self.referencia,
                self.latitud is not None,
                self.longitud is not None,
                self.imagen_url,
                self.audio_url,
                self.texto_usuario,
            ]
        )
        if not has_payload:
            raise ValueError("Debes reenviar al menos una evidencia o dato adicional.")

        only_one_coordinate = (self.latitud is None) != (self.longitud is None)
        if only_one_coordinate:
            raise ValueError("Si actualizas coordenadas, debes enviar latitud y longitud.")

        return self


class WorkshopCandidateItem(BaseModel):
    # Taller candidato calculado por el motor de matching.

    taller_id: int
    nombre_taller: str
    disponibilidad: str
    capacidad_disponible: bool
    cumple_tipo_problema: bool
    distancia_km: float | None
    puntuacion: float
    servicios: list[str]
    razon: str


class IncidentCandidatesResponse(BaseModel):
    # Lista ordenada de talleres candidatos para seleccion del cliente.

    incidente_id: int
    tipo_problema: str
    prioridad: int
    total_candidatos: int
    candidatos: list[WorkshopCandidateItem]


class IncidentCandidateSelectionRequest(BaseModel):
    # Talleres que el cliente elige para enviar la solicitud.

    talleres_ids: list[int] = Field(min_length=1, max_length=10)

    @field_validator("talleres_ids")
    @classmethod
    def validate_workshop_ids(cls, value: list[int]) -> list[int]:
        # Normaliza ids, elimina duplicados y valida enteros positivos.
        cleaned: list[int] = []
        seen: set[int] = set()
        for item in value:
            if item <= 0:
                raise ValueError("Todos los talleres_ids deben ser positivos.")
            if item in seen:
                continue
            seen.add(item)
            cleaned.append(item)

        if not cleaned:
            raise ValueError("Debes seleccionar al menos un taller.")
        return cleaned


class IncidentCandidateSelectionResponse(BaseModel):
    # Confirmacion de solicitudes enviadas a talleres elegidos por el cliente.

    incidente_id: int
    estado_incidente: str
    solicitudes_enviadas: int
    talleres_enviados: list[int]
    mensaje: str


class ClientRequestItem(BaseModel):
    # Vista resumida de solicitudes vinculadas a incidentes del cliente.

    solicitud_id: int
    incidente_id: int
    taller_id: int
    nombre_taller: str | None
    estado_solicitud: str
    estado_incidente: str
    tipo_problema: str
    prioridad: int
    fecha_asignacion: datetime
    tecnico_id: int | None = None
    tecnico_latitud: float | None = None
    tecnico_longitud: float | None = None
    tecnico_precision_metros: float | None = None
    tecnico_ubicacion_actualizada_en: datetime | None = None
    metrica: dict[str, float | int | str | None] | None = None


class ClientRequestsResponse(BaseModel):
    # Listado de solicitudes visibles para el cliente autenticado.

    total: int
    solicitudes: list[ClientRequestItem]


class WorkshopEvidenceItem(BaseModel):
    # Evidencia enviada al taller para evaluar la solicitud.

    evidencia_id: int
    tipo: str
    url: str | None
    texto_extraido: str | None


class WorkshopIncomingRequestItem(BaseModel):
    # Solicitud entrante para taller con contexto completo del incidente.

    solicitud_id: int
    incidente_id: int
    estado_solicitud: str
    estado_incidente: str
    tipo_problema: str
    prioridad: int
    ubicacion: str | None
    latitud: float | None
    longitud: float | None
    vehiculo_placa: str
    vehiculo_marca: str | None
    vehiculo_modelo: str | None
    vehiculo_anio: int | None
    cliente_id: int
    fecha_asignacion: datetime
    evidencias: list[WorkshopEvidenceItem]
    tecnico_id: int | None = None
    tecnico_latitud: float | None = None
    tecnico_longitud: float | None = None
    tecnico_precision_metros: float | None = None
    tecnico_ubicacion_actualizada_en: datetime | None = None


class WorkshopIncomingRequestsResponse(BaseModel):
    # Bandeja de solicitudes para taller autenticado.

    total: int
    solicitudes: list[WorkshopIncomingRequestItem]


class WorkshopRequestDecisionRequest(BaseModel):
    # Accion de taller sobre una solicitud: aceptar o rechazar.

    accion: str = Field(description="Valores: aceptar | rechazar")
    comentario: str | None = Field(default=None, max_length=1000)
    transporte_id: int | None = Field(default=None, ge=1)

    @field_validator("accion")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        action = value.strip().lower()
        if action not in {"aceptar", "rechazar"}:
            raise ValueError("accion invalida. Usa 'aceptar' o 'rechazar'.")
        return action

    @field_validator("comentario")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class WorkshopRequestDecisionResponse(BaseModel):
    # Resultado de decision del taller sobre la solicitud.

    solicitud_id: int
    incidente_id: int
    estado_solicitud: str
    estado_incidente: str
    tecnico_id: int | None
    transporte_id: int | None
    mensaje: str


class IncidentHistoryItem(BaseModel):
    # Evento de trazabilidad del incidente.

    historial_id: int
    accion: str
    descripcion: str | None
    fecha_hora: datetime
    actor_usuario_id: int | None


class IncidentDetailResponse(BaseModel):
    # Detalle completo de incidente para cliente o taller.

    incidente_id: int
    estado_incidente: str
    tipo_problema: str
    prioridad: int
    info_reintentos: int
    cliente_id: int
    taller_asignado_id: int | None
    solicitud_aceptada_id: int | None
    tecnico_asignado_id: int | None
    transporte_asignado_id: int | None
    tecnico_latitud: float | None
    tecnico_longitud: float | None
    tecnico_precision_metros: float | None
    tecnico_ubicacion_actualizada_en: datetime | None
    vehiculo_placa: str
    vehiculo_marca: str | None
    vehiculo_modelo: str | None
    vehiculo_anio: int | None
    ubicacion: str | None
    latitud: float | None
    longitud: float | None
    descripcion: str | None
    fecha_hora: datetime
    metrica: dict[str, float | int | str | None] | None
    evidencias: list[WorkshopEvidenceItem]
    historial: list[IncidentHistoryItem]


class WorkshopServiceCompletionRequest(BaseModel):
    # Payload para cerrar atencion de solicitud aceptada.

    comentario_cierre: str | None = Field(default=None, max_length=1000)
    tiempo_minutos: int | None = Field(default=None, ge=1, le=1440)
    costo_total: float | None = Field(default=None, ge=0)
    distancia_km: float | None = Field(default=None, ge=0)

    @field_validator("comentario_cierre")
    @classmethod
    def normalize_close_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class WorkshopServiceCompletionResponse(BaseModel):
    # Resultado de cierre de servicio con liberacion de recursos.

    solicitud_id: int
    incidente_id: int
    estado_solicitud: str
    estado_incidente: str
    tecnico_liberado_id: int | None
    transporte_liberado_id: int | None
    metrica: dict[str, float | int | str | None] | None
    mensaje: str


class IncidentCancelResponse(BaseModel):
    # Confirmacion de cancelacion del incidente por cliente.

    incidente_id: int
    estado_incidente: str
    mensaje: str


class TechnicianLocationUpdateRequest(BaseModel):
    # Payload enviado por tecnico movil para actualizar su ubicacion.

    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    solicitud_id: int | None = Field(default=None, gt=0)
    precision_metros: float | None = Field(default=None, ge=0)


class TechnicianLocationUpdateResponse(BaseModel):
    # Confirmacion de posicion actualizada.

    tecnico_id: int
    solicitud_id: int | None
    latitud: float
    longitud: float
    precision_metros: float | None
    mensaje: str


class TechnicianIncomingRequestItem(BaseModel):
    # Solicitud activa visible para el tecnico asignado.

    solicitud_id: int
    incidente_id: int
    estado_solicitud: str
    estado_incidente: str
    tipo_problema: str
    prioridad: int
    vehiculo_placa: str
    vehiculo_marca: str | None
    vehiculo_modelo: str | None
    vehiculo_anio: int | None
    ubicacion: str | None
    latitud: float | None
    longitud: float | None
    fecha_asignacion: datetime


class TechnicianIncomingRequestsResponse(BaseModel):
    # Bandeja de solicitudes activas para tecnico mobile.

    total: int
    solicitudes: list[TechnicianIncomingRequestItem]


class TechnicianRequestRejectRequest(BaseModel):
    # Payload para que el tecnico rechace y libere la solicitud asignada.

    comentario: str | None = Field(default=None, max_length=1000)

    @field_validator("comentario")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class TechnicianRequestRejectResponse(BaseModel):
    # Resultado del rechazo de solicitud por parte del tecnico.

    solicitud_id: int
    incidente_id: int
    estado_solicitud: str
    estado_incidente: str
    tecnico_liberado_id: int | None
    transporte_liberado_id: int | None
    mensaje: str


class ClientIncidentHistoryItem(BaseModel):
    # Historial consolidado de incidentes del cliente.

    incidente_id: int
    solicitud_id: int | None = None
    vehiculo_placa: str
    tipo_problema: str
    estado_incidente: str
    fecha_hora: datetime
    estados_solicitud: list[str]
    metrica: dict[str, float | int | str | None] | None


class ClientIncidentHistoryResponse(BaseModel):
    # Listado de historial del cliente autenticado.

    total: int
    incidentes: list[ClientIncidentHistoryItem]


class WorkshopIncidentHistoryResponse(BaseModel):
    # Listado de incidentes donde el taller fue solicitado.

    total: int
    incidentes: list[ClientIncidentHistoryItem]


class TechnicianIncidentHistoryResponse(BaseModel):
    # Listado de incidentes en los que participo el tecnico.

    total: int
    incidentes: list[ClientIncidentHistoryItem]
