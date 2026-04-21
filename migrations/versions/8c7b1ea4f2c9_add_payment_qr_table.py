"""add payment qr table

Revision ID: 8c7b1ea4f2c9
Revises: 1fd620d9c01a
Create Date: 2026-04-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8c7b1ea4f2c9"
down_revision: Union[str, None] = "1fd620d9c01a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("taller_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("commission", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("proof_image_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["cliente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["taller_id"], ["taller.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index(op.f("ix_payment_incident_id"), "payment", ["incident_id"], unique=True)
    op.create_index(op.f("ix_payment_status"), "payment", ["status"], unique=False)
    op.create_index(op.f("ix_payment_taller_id"), "payment", ["taller_id"], unique=False)
    op.create_index(op.f("ix_payment_user_id"), "payment", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_user_id"), table_name="payment")
    op.drop_index(op.f("ix_payment_taller_id"), table_name="payment")
    op.drop_index(op.f("ix_payment_status"), table_name="payment")
    op.drop_index(op.f("ix_payment_incident_id"), table_name="payment")
    op.drop_table("payment")
