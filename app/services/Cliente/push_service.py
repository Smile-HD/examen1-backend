# Servicio para registrar tokens y enviar notificaciones push via FCM.

import json
import logging
import os

import httpx
from sqlalchemy.orm import Session

from app.models.push_schemas import PushTokenRegisterRequest, PushTokenRegisterResponse
from app.repositories.push_repository import PushRepository

_FCM_SEND_URL = "https://fcm.googleapis.com/fcm/send"
_FCM_V1_SCOPE = ["https://www.googleapis.com/auth/firebase.messaging"]
_FCM_ANDROID_CHANNEL_ID = os.getenv("FCM_ANDROID_CHANNEL_ID", "emergencias_push_foreground").strip() or "emergencias_push_foreground"
_INVALID_FCM_ERRORS = {
    "NotRegistered",
    "InvalidRegistration",
    "MismatchSenderId",
}
_INVALID_FCM_V1_ERRORS = {
    "UNREGISTERED",
    "INVALID_ARGUMENT",
}

logger = logging.getLogger(__name__)


def _load_service_account_info_from_env() -> dict[str, object] | None:
    # Carga JSON de cuenta de servicio desde variable de entorno para entornos cloud.
    raw_json = os.getenv("FCM_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw_json:
        return None

    try:
        info = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("FCM_SERVICE_ACCOUNT_JSON no es un JSON valido.")
        return None

    private_key = info.get("private_key")
    if isinstance(private_key, str) and "\\n" in private_key:
        info["private_key"] = private_key.replace("\\n", "\n")

    return info


def _resolve_fcm_v1_access_token_and_project() -> tuple[str, str] | None:
    # Obtiene access token OAuth2 para FCM HTTP v1 y el project id.
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except Exception:
        return None

    credentials = None
    service_info = _load_service_account_info_from_env()
    if service_info:
        try:
            credentials = service_account.Credentials.from_service_account_info(
                service_info,
                scopes=_FCM_V1_SCOPE,
            )
        except Exception:
            credentials = None
    else:
        service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if service_account_path:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=_FCM_V1_SCOPE,
                )
            except Exception:
                credentials = None

    if not credentials:
        return None

    try:
        credentials.refresh(GoogleAuthRequest())
    except Exception:
        return None

    access_token = (credentials.token or "").strip()
    project_id = (
        os.getenv("FCM_PROJECT_ID", "").strip()
        or str(getattr(credentials, "project_id", "") or "").strip()
    )

    if not access_token or not project_id:
        return None

    return (access_token, project_id)


def _is_invalid_fcm_v1_token_response(response: httpx.Response) -> bool:
    # Interpreta errores FCM v1 para inactivar tokens no registrados.
    try:
        payload = response.json()
    except Exception:
        return False

    error = payload.get("error")
    if not isinstance(error, dict):
        return False

    details = error.get("details")
    if not isinstance(details, list):
        return False

    for item in details:
        if not isinstance(item, dict):
            continue
        error_code = item.get("errorCode")
        if isinstance(error_code, str) and error_code.upper() in _INVALID_FCM_V1_ERRORS:
            return True

    return False


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
        logger.info(
            "Token push registrado para usuario_id=%s plataforma=%s",
            cliente_id,
            platform,
        )
    except Exception:
        db.rollback()
        logger.exception("Fallo al registrar token push para usuario_id=%s", cliente_id)
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
    fcm_v1_context = _resolve_fcm_v1_access_token_and_project()

    if not server_key and not fcm_v1_context:
        logger.warning(
            "Push omitido para cliente_id=%s: sin credenciales FCM.",
            cliente_id,
        )
        return

    repository = PushRepository(db)
    rows = repository.list_active_tokens_for_user(cliente_id)
    if not rows:
        logger.info(
            "Push omitido para cliente_id=%s: no hay tokens activos registrados.",
            cliente_id,
        )
        return

    use_v1 = fcm_v1_context is not None
    headers = {"Content-Type": "application/json"}
    send_url = _FCM_SEND_URL

    if use_v1:
        access_token, project_id = fcm_v1_context
        headers["Authorization"] = f"Bearer {access_token}"
        send_url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    else:
        headers["Authorization"] = f"key={server_key}"

    invalid_ids: list[int] = []

    try:
        with httpx.Client(timeout=6.0) as client:
            for row in rows:
                if use_v1:
                    payload = {
                        "message": {
                            "token": row.token,
                            "notification": {
                                "title": titulo,
                                "body": cuerpo,
                            },
                            "data": data or {},
                            "android": {
                                "priority": "HIGH",
                                "notification": {
                                    "channel_id": _FCM_ANDROID_CHANNEL_ID,
                                    "sound": "default",
                                    "notification_priority": "PRIORITY_HIGH",
                                },
                            },
                            "apns": {
                                "payload": {
                                    "aps": {
                                        "sound": "default",
                                    }
                                }
                            },
                        }
                    }
                else:
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
                    response = client.post(send_url, headers=headers, json=payload)
                except Exception:
                    logger.exception(
                        "Error de red enviando push a cliente_id=%s token_id=%s",
                        cliente_id,
                        row.id,
                    )
                    continue

                if response.status_code >= 400:
                    logger.warning(
                        "FCM rechazo push cliente_id=%s token_id=%s status=%s body=%s",
                        cliente_id,
                        row.id,
                        response.status_code,
                        response.text[:300],
                    )
                    if use_v1 and _is_invalid_fcm_v1_token_response(response):
                        invalid_ids.append(int(row.id))
                    continue

                try:
                    result = response.json()
                except Exception:
                    continue

                details = result.get("results")
                if not isinstance(details, list) or not details:
                    logger.info(
                        "Push enviado via FCM v1 a cliente_id=%s token_id=%s",
                        cliente_id,
                        row.id,
                    )
                    continue

                first = details[0]
                if not isinstance(first, dict):
                    continue

                error_name = first.get("error")
                if isinstance(error_name, str) and error_name in _INVALID_FCM_ERRORS:
                    invalid_ids.append(int(row.id))
                    logger.warning(
                        "Token invalido detectado por FCM legacy cliente_id=%s token_id=%s error=%s",
                        cliente_id,
                        row.id,
                        error_name,
                    )

        if invalid_ids:
            repository.deactivate_tokens(invalid_ids)
            db.commit()
            logger.info(
                "Tokens inactivos por errores FCM cliente_id=%s token_ids=%s",
                cliente_id,
                invalid_ids,
            )
    except Exception:
        db.rollback()
        logger.exception("Error inesperado durante envio push a cliente_id=%s", cliente_id)
