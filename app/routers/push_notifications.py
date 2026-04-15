# Rutas de API para registro de notificaciones push en mobile cliente.

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.push_controller import register_client_push_token_controller
from app.database import get_db
from app.dependencies.auth import AuthenticatedUser, require_mobile_cliente
from app.models.push_schemas import PushTokenRegisterRequest, PushTokenRegisterResponse

router = APIRouter(prefix="/api/v1/notificaciones", tags=["Notificaciones"])


@router.post(
    "/push-token",
    response_model=PushTokenRegisterResponse,
    status_code=status.HTTP_200_OK,
)
def register_push_token_endpoint(
    payload: PushTokenRegisterRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> PushTokenRegisterResponse:
    # Registra token push del cliente autenticado para alertas de su solicitud.
    return register_client_push_token_controller(
        payload,
        cliente_id=current_user.user_id,
        db=db,
    )
