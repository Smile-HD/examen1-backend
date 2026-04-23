# Repositorio de acceso a datos para el registro de usuarios.

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import Cliente, Rol, RolUsuario, Taller, Tecnico, Usuario


class UserRepository:
    # Encapsula lecturas/escrituras SQL para mantener la logica de negocio limpia.

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> Usuario | None:
        # Busca usuario por correo para validar precondicion de unicidad.
        return self.db.query(Usuario).filter(Usuario.correo == email).first()

    def create_user(
        self,
        *,
        nombre: str,
        correo: str,
        contrasena_hash: str,
        telefono: str | None,
    ) -> Usuario:
        # Crea el registro principal en tabla usuario.
        user = Usuario(
            nombre=nombre.strip(),
            correo=correo.strip().lower(),
            contrasena_hash=contrasena_hash,
            telefono=telefono.strip() if telefono else None,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_or_create_role(self, role_name: str, description: str) -> Rol:
        # Obtiene rol existente o lo crea para soportar entornos vacios.
        role = self.db.query(Rol).filter(Rol.nombre == role_name).first()
        if role:
            return role

        role = Rol(nombre=role_name, descripcion=description)
        self.db.add(role)
        self.db.flush()
        return role

    def get_role_by_name(self, role_name: str) -> Rol | None:
        # Recupera un rol por nombre si existe en catalogo.
        return self.db.query(Rol).filter(Rol.nombre == role_name).first()

    def get_roles_by_normalized_name(self, role_name: str) -> list[Rol]:
        # Recupera roles comparando en minusculas para evitar variantes legacy.
        normalized = role_name.strip().lower()
        if not normalized:
            return []

        return (
            self.db.query(Rol)
            .filter(func.lower(Rol.nombre) == normalized)
            .all()
        )

    def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        # Asocia usuario y rol en tabla puente rol_usuario.
        exists = (
            self.db.query(RolUsuario)
            .filter(
                RolUsuario.usuario_id == user_id,
                RolUsuario.rol_id == role_id,
            )
            .first()
        )
        if exists:
            return

        self.db.add(RolUsuario(usuario_id=user_id, rol_id=role_id))
        self.db.flush()

    def remove_role_from_user(self, user_id: int, role_id: int) -> None:
        # Quita asociacion usuario-rol cuando exista.
        relation = (
            self.db.query(RolUsuario)
            .filter(
                RolUsuario.usuario_id == user_id,
                RolUsuario.rol_id == role_id,
            )
            .first()
        )
        if not relation:
            return

        self.db.delete(relation)
        self.db.flush()

    def create_cliente_profile(self, user_id: int) -> None:
        # Crea especializacion de usuario como cliente.
        exists = self.db.query(Cliente).filter(Cliente.id == user_id).first()
        if exists:
            return
        self.db.add(Cliente(id=user_id))
        self.db.flush()

    def create_taller_profile(self, user_id: int, workshop_name: str, workshop_location: str | None) -> None:
        # Crea especializacion de usuario como taller.
        self.db.add(
            Taller(
                id=user_id,
                nombre=workshop_name.strip(),
                ubicacion=workshop_location.strip() if workshop_location else None,
                estado="activo",
            )
        )
        self.db.flush()

    def create_tecnico_profile(
        self,
        user_id: int,
        estado: str = "disponible",
        taller_id: int | None = None,
    ) -> None:
        # Crea especializacion de usuario como tecnico para uso futuro en modulo web.
        exists = self.db.query(Tecnico).filter(Tecnico.id == user_id).first()
        if exists:
            return

        self.db.add(Tecnico(id=user_id, estado=estado, taller_id=taller_id))
        self.db.flush()

    def get_role_names_by_user_id(self, user_id: int) -> set[str]:
        # Obtiene todos los nombres de rol asociados al usuario autenticado.
        rows = (
            self.db.query(Rol.nombre)
            .join(RolUsuario, RolUsuario.rol_id == Rol.id)
            .filter(RolUsuario.usuario_id == user_id)
            .all()
        )
        return {name for (name,) in rows}

    def get_specialization_flags(self, user_id: int) -> dict[str, bool]:
        # Permite separar acceso por tipo de actor sin depender solo del catalogo de roles.
        is_cliente = self.db.query(Cliente.id).filter(Cliente.id == user_id).first() is not None
        is_taller = self.db.query(Taller.id).filter(Taller.id == user_id).first() is not None
        # Un tecnico solo se considera activo si tiene taller asignado.
        is_tecnico = (
            self.db.query(Tecnico.id)
            .filter(
                Tecnico.id == user_id,
                Tecnico.taller_id.isnot(None),
            )
            .first()
            is not None
        )

        return {
            "cliente": is_cliente,
            "taller": is_taller,
            "tecnico": is_tecnico,
        }

    def delete_user(self, user_id: int) -> None:
        # Elimina un usuario del sistema. Las relaciones en cascada se encargan de limpiar datos relacionados.
        user = self.db.query(Usuario).filter(Usuario.id == user_id).first()
        if user:
            self.db.delete(user)
            self.db.flush()

    def get_user_by_id(self, user_id: int) -> Usuario | None:
        # Obtiene un usuario por su ID.
        return self.db.query(Usuario).filter(Usuario.id == user_id).first()
