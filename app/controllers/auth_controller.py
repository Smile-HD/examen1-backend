# Controlador HTTP para inicio de sesion.

from urllib.parse import parse_qs

from fastapi import HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.auth_schemas import UserLoginRequest, UserLoginResponse
from app.services.auth_service import (
    ChannelAccessDeniedError,
    InvalidCredentialsError,
    authenticate_user,
)


async def _parse_login_request(request: Request) -> UserLoginRequest:
    # Soportamos JSON y form-urlencoded para compatibilidad con Flutter y Web.
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        data = await request.json()
        return UserLoginRequest(**data)

    if "application/x-www-form-urlencoded" in content_type:
        raw_body = (await request.body()).decode("utf-8")
        parsed = parse_qs(raw_body)
        return UserLoginRequest(
            correo=(parsed.get("correo") or parsed.get("username") or [""])[0],
            password=(parsed.get("password") or [""])[0],
            canal=(parsed.get("canal") or ["mobile"])[0],
        )

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Content-Type no soportado. Usa application/json o application/x-www-form-urlencoded.",
    )


async def login_user_controller(request: Request, db: Session) -> UserLoginResponse:
    # Convierte request HTTP en caso de uso y traduce errores de dominio a codigos HTTP.
    try:
        payload = await _parse_login_request(request)
        return authenticate_user(payload, db)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ChannelAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc