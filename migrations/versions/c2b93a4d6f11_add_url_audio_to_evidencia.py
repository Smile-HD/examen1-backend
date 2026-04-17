"""add url_audio to evidencia

Revision ID: c2b93a4d6f11
Revises: 7a1e5f66d2ab
Create Date: 2026-04-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c2b93a4d6f11"
down_revision: Union[str, None] = "7a1e5f66d2ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Permite guardar audio e imagen dentro del mismo registro de evidencia.
    op.execute("ALTER TABLE evidencia ADD COLUMN IF NOT EXISTS url_audio TEXT;")


def downgrade() -> None:
    # Revierte el soporte de URL de audio separado en evidencia.
    op.execute("ALTER TABLE evidencia DROP COLUMN IF EXISTS url_audio;")
