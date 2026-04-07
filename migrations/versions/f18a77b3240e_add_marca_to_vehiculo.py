# add marca to vehiculo
#
# Revision ID: f18a77b3240e
# Revises: 9dbe4db6a4e1
# Create Date: 2026-04-06 17:05:00.000000

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f18a77b3240e"
down_revision: Union[str, None] = "9dbe4db6a4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agrega marca para almacenar datos completos del vehiculo (marca, modelo, placa, etc.).
    op.execute("ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS marca VARCHAR(80);")
    op.execute("UPDATE vehiculo SET marca = 'No especificada' WHERE marca IS NULL;")
    op.execute("ALTER TABLE vehiculo ALTER COLUMN marca SET NOT NULL;")


def downgrade() -> None:
    # Permite revertir la migracion si se requiere rollback.
    op.execute("ALTER TABLE vehiculo DROP COLUMN IF EXISTS marca;")
