# Esquemas de entrada/salida para el caso de uso CU1: Registrar usuario.

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegistrationRequest(BaseModel):
    # Payload esperado para registrar clientes y talleres.

    nombre: str = Field(min_length=2, max_length=120)
    correo: str = Field(max_length=150)
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=25)
    tipo_usuario: str = Field(description="Valores permitidos: cliente | taller | empleado | tecnico")
    nombre_taller: str | None = Field(default=None, max_length=150)
    ubicacion_taller: str | None = Field(default=None, max_length=500)

    @field_validator("correo")
    @classmethod
    def validate_email(cls, value: str) -> str:
        # Valida un formato basico de correo para evitar datos mal formados.
        email = value.strip().lower()
        if not EMAIL_REGEX.match(email):
            raise ValueError("El correo no tiene un formato valido.")
        return email

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        # Asegura una contrasena minima con letras y numeros para seguridad basica.
        has_letter = any(ch.isalpha() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        if not has_letter or not has_digit:
            raise ValueError("La contrasena debe incluir letras y numeros.")
        return value

    @field_validator("tipo_usuario")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        # Normaliza el tipo de usuario para manejar mayusculas/minusculas.
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_workshop_data(self) -> "UserRegistrationRequest":
        # Si el actor es taller, exigimos nombre del taller para integridad del dato.
        if self.tipo_usuario == "taller" and not self.nombre_taller:
            raise ValueError("Para registrar un taller debes enviar nombre_taller.")
        return self


class UserRegistrationResponse(BaseModel):
    # Respuesta estandar al completar registro exitoso.

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    correo: str
    tipo_usuario: str
    creado_en: datetime
    mensaje: str
