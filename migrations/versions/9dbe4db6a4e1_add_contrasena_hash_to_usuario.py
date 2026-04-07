# add contrasena_hash to usuario
#
# Revision ID: 9dbe4db6a4e1
# Revises: 63af4037119c
# Create Date: 2026-04-06 14:10:00.000000

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9dbe4db6a4e1"
down_revision: Union[str, None] = "63af4037119c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregamos columna para guardar hash de contrasena de forma segura.
    op.execute(
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS contrasena_hash VARCHAR(255);"
    )
    op.execute(
        "UPDATE usuario SET contrasena_hash = 'pendiente_configurar' WHERE contrasena_hash IS NULL;"
    )
    op.execute("ALTER TABLE usuario ALTER COLUMN contrasena_hash SET NOT NULL;")


def downgrade() -> None:
    # Permite volver atras si se necesita revertir el cambio.
    op.execute("ALTER TABLE usuario DROP COLUMN IF EXISTS contrasena_hash;")
