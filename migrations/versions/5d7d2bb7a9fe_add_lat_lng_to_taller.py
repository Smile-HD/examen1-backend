"""add lat lng to taller

Revision ID: 5d7d2bb7a9fe
Revises: 1fd620d9c01a
Create Date: 2026-04-15 10:35:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5d7d2bb7a9fe"
down_revision: Union[str, None] = "1fd620d9c01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Persiste coordenadas del taller en columnas dedicadas para seguimiento y perfil.
    op.execute("ALTER TABLE taller ADD COLUMN IF NOT EXISTS latitud NUMERIC(9,6);")
    op.execute("ALTER TABLE taller ADD COLUMN IF NOT EXISTS longitud NUMERIC(9,6);")

    # Migra coordenadas legacy embebidas en texto de ubicacion: "(lat: x, lng: y)".
    op.execute(
        """
        UPDATE taller
        SET
            latitud = ((regexp_match(ubicacion, '\\(lat:\\s*(-?\\d+(?:\\.\\d+)?)\\s*,\\s*lng:\\s*(-?\\d+(?:\\.\\d+)?)\\)'))[1])::numeric,
            longitud = ((regexp_match(ubicacion, '\\(lat:\\s*(-?\\d+(?:\\.\\d+)?)\\s*,\\s*lng:\\s*(-?\\d+(?:\\.\\d+)?)\\)'))[2])::numeric
        WHERE
            ubicacion IS NOT NULL
            AND ubicacion ~* '\\(lat:\\s*-?\\d+(?:\\.\\d+)?\\s*,\\s*lng:\\s*-?\\d+(?:\\.\\d+)?\\)'
            AND (latitud IS NULL OR longitud IS NULL);
        """
    )


def downgrade() -> None:
    # Revierte columnas agregadas para coordenadas del taller.
    op.execute("ALTER TABLE taller DROP COLUMN IF EXISTS latitud;")
    op.execute("ALTER TABLE taller DROP COLUMN IF EXISTS longitud;")
