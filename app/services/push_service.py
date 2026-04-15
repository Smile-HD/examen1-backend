# Servicio para registrar tokens y enviar notificaciones push via FCM.

import os

import httpx
from sqlalchemy.orm import Session

from app.models.push_schemas import PushTokenRegisterRequest, PushTokenRegisterResponse
from app.repositories.push_repository import PushRepository

_FCM_SEND_URL = "https://fcm.googleapis.com/fcm/send"
_INVALID_FCM_ERRORS = {
    "NotRegistered",
    "InvalidRegistration",
    "MismatchSenderId",
}


def register_client_push_token(
    payload: PushTokenRegisterRequest,
    *,
    cliente_id: int,
    db: Session,
) -> PushTokenRegisterResponse:
    # Registra token del cliente mobile para recibir eventos de su solicitud.
    repository = PushRepository(db)
    platform = (payload.plataforma or "flutter_mobile").strip().lower()

    try:
        repository.upsert_user_token(
            usuario_id=cliente_id,
            token=payload.token.strip(),
            plataforma=platform,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return PushTokenRegisterResponse(
        mensaje="Token push registrado correctamente.",
        token_registrado=True,
    )


def send_client_push_best_effort(
    *,
    cliente_id: int,
    titulo: str,
    cuerpo: str,
    data: dict[str, str] | None,
    db: Session,
) -> None:
    # Envia push al cliente; si falla no rompe flujo principal de negocio.
    server_key = os.getenv("FCM_SERVER_KEY", "").strip()
    if not server_key:
        return

    repository = PushRepository(db)
    rows = repository.list_active_tokens_for_user(cliente_id)
    if not rows:
        return

    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }

    invalid_ids: list[int] = []

    try:
        with httpx.Client(timeout=6.0) as client:
            for row in rows:
                payload = {
                    "to": row.token,
                    "priority": "high",
                    "notification": {
                        "title": titulo,
                        "body": cuerpo,
                        "sound": "default",
                    },
                    "data": data or {},
                }

                try:
                    response = client.post(_FCM_SEND_URL, headers=headers, json=payload)
                except Exception:
                    continue

                if response.status_code >= 400:
                    continue

                try:
                    result = response.json()
                except Exception:
                    continue

                details = result.get("results")
                if not isinstance(details, list) or not details:
                    continue

                first = details[0]
                if not isinstance(first, dict):
                    continue

                error_name = first.get("error")
                if isinstance(error_name, str) and error_name in _INVALID_FCM_ERRORS:
                    invalid_ids.append(int(row.id))

        if invalid_ids:
            repository.deactivate_tokens(invalid_ids)
            db.commit()
    except Exception:
        db.rollback()
