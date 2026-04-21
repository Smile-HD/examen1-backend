"""merge heads

Revision ID: 0363db79e428
Revises: c2b93a4d6f11, bc3418c89f5e
Create Date: 2026-04-21 18:30:38.186644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0363db79e428'
down_revision: Union[str, None] = ('c2b93a4d6f11', 'bc3418c89f5e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
