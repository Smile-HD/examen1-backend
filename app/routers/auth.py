# Rutas de autenticacion para login en mobile y web.

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.controllers.auth_controller import login_user_controller
from app.database import get_db
from app.models.auth_schemas import UserLoginResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login_user_endpoint(
    request: Request,
    db: Session = Depends(get_db),
) -> UserLoginResponse:
    # Endpoint de inicio de sesion con separacion por canal.
    return await login_user_controller(request, db)