"""add commission tables

Revision ID: add_commission_tables
Revises: 0363db79e428
Create Date: 2026-04-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_commission_tables"
down_revision: Union[str, None] = "0363db79e428"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla plataforma_config
    op.create_table(
        "plataforma_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("qr_image_url", sa.Text(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Crear tabla comision_pago
    op.create_table(
        "comision_pago",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("taller_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("proof_image_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["taller_id"], ["taller.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_comision_pago_taller_id"), "comision_pago", ["taller_id"], unique=False
    )
    op.create_index(
        op.f("ix_comision_pago_status"), "comision_pago", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_comision_pago_status"), table_name="comision_pago")
    op.drop_index(op.f("ix_comision_pago_taller_id"), table_name="comision_pago")
    op.drop_table("comision_pago")
    op.drop_table("plataforma_config")
