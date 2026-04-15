# Servicio de negocio para CU1: Registrar usuario.

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user_schemas import UserRegistrationRequest, UserRegistrationResponse
from app.repositories.user_repository import UserRepository


class UserAlreadyExistsError(Exception):
    # Error de dominio cuando el correo ya existe en base de datos.
    pass


class UserRegistrationValidationError(Exception):
    # Error de dominio para reglas de validacion de CU1.
    pass


def register_user(data: UserRegistrationRequest, db: Session) -> UserRegistrationResponse:
    # Ejecuta el flujo principal de registro (validar, guardar y confirmar).
    repository = UserRepository(db)

    # Normalizamos el correo para evitar duplicados por mayusculas/minusculas.
    email = data.correo.strip().lower()
    if repository.get_user_by_email(email):
        raise UserAlreadyExistsError("El usuario ya existe con ese correo.")

    role = data.tipo_usuario.strip().lower()
    if role not in {"cliente", "taller", "empleado", "tecnico"}:
        raise UserRegistrationValidationError(
            "tipo_usuario invalido. Debe ser 'cliente', 'taller', 'empleado' o 'tecnico'."
        )

    stored_role = "tecnico" if role in {"empleado", "tecnico"} else role

    try:
        # 1) Guardamos el usuario base con contrasena cifrada.
        user = repository.create_user(
            nombre=data.nombre,
            correo=email,
            contrasena_hash=hash_password(data.password),
            telefono=data.telefono,
        )

        # 2) Creamos/obtenemos rol y lo vinculamos al usuario.
        role_entity = repository.get_or_create_role(
            stored_role,
            f"Rol de {stored_role} dentro de la plataforma de emergencias vehiculares.",
        )
        repository.assign_role_to_user(user.id, role_entity.id)

        if stored_role == "tecnico":
            cliente_role_entity = repository.get_or_create_role(
                "cliente",
                "Rol de cliente dentro de la plataforma de emergencias vehiculares.",
            )
            repository.assign_role_to_user(user.id, cliente_role_entity.id)

        # 3) Creamos especializacion segun actor iniciador del caso de uso.     
        if role == "cliente":
            repository.create_cliente_profile(user.id)
        elif role == "taller":
            workshop_name = data.nombre_taller or f"Taller de {data.nombre}"    
            repository.create_taller_profile(user.id, workshop_name, data.ubicacion_taller)
        else:
            repository.create_tecnico_profile(user.id)
            repository.create_cliente_profile(user.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserAlreadyExistsError("El usuario ya existe con ese correo.") from exc
    except Exception:
        db.rollback()
        raise

    return UserRegistrationResponse(
        id=user.id,
        nombre=user.nombre,
        correo=user.correo,
        tipo_usuario=role,
        creado_en=user.creado_en,
        mensaje="Registro exitoso.",
    )
