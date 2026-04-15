# Esquemas para registro de tokens push del cliente mobile.

from pydantic import BaseModel, Field, field_validator


class PushTokenRegisterRequest(BaseModel):
    # Payload para registrar/actualizar token FCM del dispositivo.

    token: str = Field(min_length=20, max_length=1024)
    plataforma: str | None = Field(default="flutter_mobile", max_length=40)

    @field_validator("token", "plataforma")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PushTokenRegisterResponse(BaseModel):
    # Confirmacion de token push registrado para el cliente.

    mensaje: str
    token_registrado: bool
