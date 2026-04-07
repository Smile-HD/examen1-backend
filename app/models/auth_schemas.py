# Esquemas de entrada/salida para autenticacion.

import re

from pydantic import BaseModel, Field, field_validator


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserLoginRequest(BaseModel):
    # Datos minimos para autenticarse desde mobile o web.

    correo: str = Field(max_length=150)
    password: str = Field(min_length=8, max_length=128)
    canal: str = Field(default="mobile", description="Valores permitidos: mobile | web")

    @field_validator("correo")
    @classmethod
    def validate_email(cls, value: str) -> str:
        # Verifica correo valido para evitar consultas innecesarias a base de datos.
        email = value.strip().lower()
        if not EMAIL_REGEX.match(email):
            raise ValueError("El correo no tiene un formato valido.")
        return email

    @field_validator("canal")
    @classmethod
    def normalize_channel(cls, value: str) -> str:
        # Normaliza canal y restringe acceso a los dos frontends definidos.
        channel = value.strip().lower()
        if channel not in {"mobile", "web"}:
            raise ValueError("canal invalido. Debe ser 'mobile' o 'web'.")
        return channel


class UserLoginResponse(BaseModel):
    # Respuesta de sesion para consumir desde Flutter o Angular.

    access_token: str
    token_type: str
    usuario_id: int
    nombre: str
    correo: str
    roles: list[str]
    perfil_principal: str
    canal: str
    mensaje: str