# Repositorio para persistencia y consulta de tokens push de usuarios.

from sqlalchemy.orm import Session

from app.models.user import UsuarioPushToken


class PushRepository:
    # Encapsula CRUD de tokens push asociados a usuarios.

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_token(self, token: str) -> UsuarioPushToken | None:
        # Busca token exacto para reusar/actualizar su vinculacion.
        return (
            self.db.query(UsuarioPushToken)
            .filter(UsuarioPushToken.token == token)
            .first()
        )

    def upsert_user_token(self, *, usuario_id: int, token: str, plataforma: str) -> UsuarioPushToken:
        # Crea o reactiva token push para el usuario autenticado.
        row = self.get_by_token(token)
        if row:
            row.usuario_id = usuario_id
            row.plataforma = plataforma
            row.activo = True
            self.db.flush()
            return row

        row = UsuarioPushToken(
            usuario_id=usuario_id,
            token=token,
            plataforma=plataforma,
            activo=True,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_active_tokens_for_user(self, usuario_id: int) -> list[UsuarioPushToken]:
        # Lista tokens activos del usuario objetivo para envio push.
        return (
            self.db.query(UsuarioPushToken)
            .filter(
                UsuarioPushToken.usuario_id == usuario_id,
                UsuarioPushToken.activo == True,
            )
            .all()
        )

    def deactivate_tokens(self, token_ids: list[int]) -> None:
        # Inactiva tokens invalidos devueltos por FCM.
        if not token_ids:
            return

        (
            self.db.query(UsuarioPushToken)
            .filter(UsuarioPushToken.id.in_(token_ids))
            .update({UsuarioPushToken.activo: False}, synchronize_session=False)
        )
        self.db.flush()
