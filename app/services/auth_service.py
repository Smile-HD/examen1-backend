# Servicio de negocio para inicio de sesion y separacion de canales.

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.auth_schemas import UserLoginRequest, UserLoginResponse
from app.repositories.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    # Error de dominio cuando correo o contrasena no corresponden a un usuario valido.
    pass


class ChannelAccessDeniedError(Exception):
    # Error de dominio cuando el rol del usuario no corresponde al canal solicitado.
    pass


def _resolve_effective_roles(
    *,
    role_names: set[str],
    specialization_flags: dict[str, bool],
) -> set[str]:
    # Consolida roles por catalogo y por perfiles para robustecer reglas de acceso.
    effective_roles = {role.strip().lower() for role in role_names}

    if specialization_flags.get("cliente"):
        effective_roles.add("cliente")
    if specialization_flags.get("taller"):
        effective_roles.add("taller")
    if specialization_flags.get("tecnico"):
        effective_roles.add("tecnico")

    return effective_roles


def _resolve_primary_profile(*, effective_roles: set[str], channel: str) -> str:
    # En mobile priorizamos tecnico sobre cliente; en web siempre prioriza taller.
    if channel == "web":
        if "taller" in effective_roles:
            return "taller"
        if "tecnico" in effective_roles:
            return "tecnico"
        return "cliente"

    if "tecnico" in effective_roles:
        return "tecnico"
    if "cliente" in effective_roles:
        return "cliente"
    if "taller" in effective_roles:
        return "taller"
    return "cliente"


def authenticate_user(data: UserLoginRequest, db: Session) -> UserLoginResponse:
    # Ejecuta autenticacion y autorizacion por canal para separar mobile de web.
    repository = UserRepository(db)
    user = repository.get_user_by_email(data.correo)
    if not user:
        raise InvalidCredentialsError("Credenciales invalidas.")

    if not verify_password(data.password, user.contrasena_hash):
        raise InvalidCredentialsError("Credenciales invalidas.")

    role_names = repository.get_role_names_by_user_id(user.id)
    specialization_flags = repository.get_specialization_flags(user.id)
    effective_roles = _resolve_effective_roles(
        role_names=role_names,
        specialization_flags=specialization_flags,
    )

    # Regla de separacion: mobile para cliente/tecnico; web solo para taller.
    if data.canal == "mobile" and not ({"cliente", "tecnico"} & effective_roles):
        raise ChannelAccessDeniedError(
            "Este usuario no tiene acceso al canal mobile."
        )
    if data.canal == "web" and "taller" not in effective_roles:
        raise ChannelAccessDeniedError(
            "Este usuario no tiene acceso al canal web de talleres."
        )

    # Nota de negocio: un tecnico inicia como cliente y luego puede sumar rol tecnico.
    # Por eso se conservan todos los roles efectivos en la sesion.
    sorted_roles = sorted(effective_roles)
    profile = _resolve_primary_profile(effective_roles=effective_roles, channel=data.canal)

    token = create_access_token(
        user_id=user.id,
        email=user.correo,
        roles=sorted_roles,
        canal=data.canal,
    )

    return UserLoginResponse(
        access_token=token,
        token_type="bearer",
        usuario_id=user.id,
        nombre=user.nombre,
        correo=user.correo,
        roles=sorted_roles,
        perfil_principal=profile,
        canal=data.canal,
        mensaje="Inicio de sesion exitoso.",
    )