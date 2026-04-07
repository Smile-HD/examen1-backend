# Controlador HTTP para CU1: Registrar usuario.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user_schemas import UserRegistrationRequest, UserRegistrationResponse
from app.services.user_service import (
    UserAlreadyExistsError,
    UserRegistrationValidationError,
    register_user,
)


def register_user_controller(
    payload: UserRegistrationRequest,
    db: Session,
) -> UserRegistrationResponse:
    # Coordina el caso de uso y mapea errores de negocio a codigos HTTP.
    try:
        return register_user(payload, db)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UserRegistrationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
