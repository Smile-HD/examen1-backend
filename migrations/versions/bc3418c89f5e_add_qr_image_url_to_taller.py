"""add qr image url to taller

Revision ID: bc3418c89f5e
Revises: 8c7b1ea4f2c9
Create Date: 2026-04-21 00:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bc3418c89f5e"
down_revision: Union[str, None] = "8c7b1ea4f2c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("taller", sa.Column("qr_image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("taller", "qr_image_url")
