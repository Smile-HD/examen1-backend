# Rutas de API para gestion de usuarios.

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.user_controller import register_user_controller
from app.database import get_db
from app.models.user_schemas import UserRegistrationRequest, UserRegistrationResponse

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuarios"])


@router.post(
    "/registro",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user_endpoint(
    payload: UserRegistrationRequest,
    db: Session = Depends(get_db),
) -> UserRegistrationResponse:
    # Endpoint CU1: recibe datos del usuario y devuelve confirmacion de registro.
    return register_user_controller(payload, db)
