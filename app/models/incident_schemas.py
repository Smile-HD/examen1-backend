# Esquemas para CU4: Reportar emergencia desde app movil.

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class IncidentReportRequest(BaseModel):
    # Datos del reporte inicial enviados desde app movil.

    vehiculo_placa: str = Field(min_length=5, max_length=10)
    ubicacion: str | None = Field(default=None, max_length=1000)
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

    @field_validator("imagen_url", "audio_url")
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

    @model_validator(mode="after")
    def ensure_minimum_evidence(self) -> "IncidentReportRequest":
        # Exigimos al menos una fuente de evidencia para iniciar análisis IA.
        if not self.imagen_url and not self.audio_url and not self.texto_usuario:
            raise ValueError(
                "Debes enviar al menos una evidencia: imagen_url, audio_url o texto_usuario."
            )
        return self


class IncidentReportResponse(BaseModel):
    # Confirmacion de incidente registrado y procesamiento iniciado.

    incidente_id: int
    estado: str
    tipo_problema: str
    procesamiento_ia: str
    vehiculo_placa: str
    fecha_hora: datetime
    mensaje: str
