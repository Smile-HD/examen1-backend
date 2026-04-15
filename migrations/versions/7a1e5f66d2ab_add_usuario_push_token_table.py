"""add usuario push token table

Revision ID: 7a1e5f66d2ab
Revises: 5d7d2bb7a9fe
Create Date: 2026-04-15 12:10:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7a1e5f66d2ab"
down_revision: Union[str, None] = "5d7d2bb7a9fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Registra tokens push FCM para usuarios mobile.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS usuario_push_token (
            id SERIAL PRIMARY KEY,
            usuario_id INT NOT NULL,
            token VARCHAR(1024) NOT NULL UNIQUE,
            plataforma VARCHAR(40) NOT NULL DEFAULT 'flutter_mobile',
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_usuario_push_token_usuario
                FOREIGN KEY (usuario_id)
                REFERENCES usuario(id)
                ON DELETE CASCADE
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_usuario_push_token_usuario_id ON usuario_push_token(usuario_id);"
    )


def downgrade() -> None:
    # Elimina tabla de tokens push.
    op.execute("DROP TABLE IF EXISTS usuario_push_token;")
