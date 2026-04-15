# Esquemas para gestion de tecnicos y vehiculos de taller.

from pydantic import BaseModel, Field, field_validator


class WorkshopTechnicianCandidateResponse(BaseModel):
    usuario_id: int
    nombre: str
    correo: str

class WorkshopTechnicianAssignRequest(BaseModel):
    usuario_id: int = Field(gt=0)

class WorkshopTechnicianAssignResponse(BaseModel):
    tecnico_id: int
    taller_id: int
    estado: str
    mensaje: str

class WorkshopTechnicianUnassignRequest(BaseModel):
    # Payload para desasignar tecnico del taller.

    tecnico_id: int = Field(gt=0)
    motivo: str | None = Field(default=None, max_length=500)


class WorkshopTechnicianUnassignResponse(BaseModel):
    # Confirmacion de desasignacion del tecnico.

    tecnico_id: int
    taller_id: int
    estado: str
    mensaje: str


class WorkshopTechnicianListItemResponse(BaseModel):
    # Item de tecnico ya asignado al taller autenticado.

    tecnico_id: int
    nombre: str
    correo: str
    estado: str


class WorkshopVehicleCreateRequest(BaseModel):
    # Payload para registrar unidad de servicio del taller.

    tipo: str = Field(min_length=2, max_length=40)
    placa: str = Field(min_length=5, max_length=10)
    estado: str | None = Field(default="disponible", max_length=20)

    @field_validator("tipo", "placa", "estado")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned


class WorkshopVehicleUpdateRequest(BaseModel):
    # Payload de actualizacion parcial para unidad del taller.

    tipo: str | None = Field(default=None, min_length=2, max_length=40)
    placa: str | None = Field(default=None, min_length=5, max_length=10)
    estado: str | None = Field(default=None, max_length=20)

    @field_validator("tipo", "placa", "estado")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned


class WorkshopVehicleResponse(BaseModel):
    # Representacion de unidad registrada del taller.

    id: int
    taller_id: int
    tipo: str
    placa: str
    estado: str


class WorkshopVehicleDeleteResponse(BaseModel):
    # Confirmacion de eliminacion de unidad del taller.

    id: int
    mensaje: str


class WorkshopHistoryItem(BaseModel):
    # Evento historico filtrado por taller autenticado.

    historial_id: int
    incidente_id: int | None
    accion: str
    descripcion: str | None
    fecha_hora: str
    actor_usuario_id: int | None


class WorkshopHistoryResponse(BaseModel):
    # Historial operativo del taller.

    total: int
    eventos: list[WorkshopHistoryItem]


class WorkshopTechnicianLocationItem(BaseModel):
    # Posicion reportada por tecnico para seguimiento en panel de taller.

    tecnico_id: int
    nombre: str
    correo: str
    estado: str
    solicitud_id: int | None
    latitud: float | None
    longitud: float | None
    precision_metros: float | None
    actualizada_en: str | None
