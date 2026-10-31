"""watchlist para o radar de ativos

Revision ID: 9f3c2a7b1d6e
Revises: c8715a0f4e2b
Create Date: 2026-10-31
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9f3c2a7b1d6e"
down_revision: str | Sequence[str] | None = "c8715a0f4e2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ativo_radar",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ativo_id", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ativo_id"], ["ativo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ativo_id", name="uq_ativo_radar_ativo"),
    )


def downgrade() -> None:
    op.drop_table("ativo_radar")
