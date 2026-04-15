# Dependencias de autenticacion/autorizacion para endpoints protegidos.

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    # Estructura simple con datos utiles del usuario autenticado.
    user_id: int
    email: str
    roles: set[str]
    canal: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    # Valida el Bearer token y transforma claims en objeto tipado.
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido.",
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Esquema de autenticacion invalido.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub", 0))
        email = str(payload.get("email", ""))
        canal = str(payload.get("canal", ""))
        roles_raw = payload.get("roles", [])
        roles = {str(role).strip().lower() for role in roles_raw}
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado.",
        )

    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador de usuario valido.",
        )

    return AuthenticatedUser(user_id=user_id, email=email, roles=roles, canal=canal)


def require_mobile_cliente(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    # En CU3 exigimos cliente autenticado desde canal mobile.
    if current_user.canal != "mobile":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es solo para canal mobile.",
        )

    repository = UserRepository(db)
    flags = repository.get_specialization_flags(current_user.user_id)
    is_cliente = flags.get("cliente", False)

    if not is_cliente:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo usuarios cliente pueden registrar vehiculos.",
        )

    return current_user


def require_web_taller(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    # Exige taller autenticado desde canal web para operar solicitudes.
    if current_user.canal != "web":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es solo para canal web de talleres.",
        )

    repository = UserRepository(db)
    flags = repository.get_specialization_flags(current_user.user_id)
    is_taller = flags.get("taller", False)

    if not is_taller and "taller" in current_user.roles:
        # Recupera cuentas legacy con rol "taller" pero sin fila en tabla `taller`.
        try:
            workshop_name = f"Taller de {current_user.email}" if current_user.email else f"Taller {current_user.user_id}"
            repository.create_taller_profile(
                current_user.user_id,
                workshop_name,
                None,
            )
            db.commit()
            is_taller = True
        except Exception:
            db.rollback()

    if not is_taller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo talleres pueden ejecutar esta operacion.",
        )

    return current_user


def require_mobile_tecnico(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    # Exige tecnico autenticado desde canal mobile para operaciones en campo.
    if current_user.canal != "mobile":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint es solo para canal mobile de tecnicos.",
        )

    repository = UserRepository(db)
    flags = repository.get_specialization_flags(current_user.user_id)
    is_tecnico = flags.get("tecnico", False)

    if not is_tecnico:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo tecnicos pueden ejecutar esta operacion.",
        )

    return current_user
