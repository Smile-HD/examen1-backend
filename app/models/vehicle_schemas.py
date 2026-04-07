# Esquemas de entrada/salida para CU3: Registrar vehiculo.

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


PLATE_REGEX = re.compile(r"^[A-Z0-9-]{5,10}$")


class VehicleRegistrationRequest(BaseModel):
    # Datos del vehiculo enviados por el cliente desde app movil.

    placa: str = Field(min_length=5, max_length=10)
    marca: str = Field(min_length=2, max_length=80)
    modelo: str = Field(min_length=1, max_length=80)
    anio: int = Field(ge=1950, le=datetime.now().year + 1)
    tipo: str = Field(min_length=3, max_length=30)

    @field_validator("placa")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        # Normaliza y valida placa para evitar duplicados por formato inconsistente.
        normalized = value.strip().upper()
        if not PLATE_REGEX.match(normalized):
            raise ValueError("La placa tiene formato invalido.")
        return normalized

    @field_validator("marca", "modelo", "tipo")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        # Limpia espacios para persistir datos uniformes.
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Este campo no puede estar vacio.")
        return cleaned


class VehicleRegistrationResponse(BaseModel):
    # Confirmacion de registro del vehiculo vinculado a cliente autenticado.

    placa: str
    cliente_id: int
    marca: str
    modelo: str
    anio: int
    tipo: str
    mensaje: str


class VehicleListItemResponse(BaseModel):
    # Item de vehículo para combos/listas en app móvil.

    placa: str
    marca: str
    modelo: str
    anio: int
    tipo: str
