# Controlador HTTP para registro de token push del cliente mobile.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.push_schemas import PushTokenRegisterRequest, PushTokenRegisterResponse
from app.services.push_service import register_client_push_token


def register_client_push_token_controller(
    payload: PushTokenRegisterRequest,
    *,
    cliente_id: int,
    db: Session,
) -> PushTokenRegisterResponse:
    # Traduce errores de registro push a HTTP para el cliente mobile.
    try:
        return register_client_push_token(payload, cliente_id=cliente_id, db=db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar el token push.",
        ) from exc
