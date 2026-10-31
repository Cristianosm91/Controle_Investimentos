"""premissas salvas da calculadora de valuation

Revision ID: d2745cfb6a91
Revises: 9f3c2a7b1d6e
Create Date: 2026-11-02
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2745cfb6a91"
down_revision: str | Sequence[str] | None = "9f3c2a7b1d6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "valuation_premissa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ativo_id", sa.Integer(), nullable=False),
        sa.Column("lpa", sa.Numeric(20, 8), nullable=True),
        sa.Column("vpa", sa.Numeric(20, 8), nullable=True),
        sa.Column("dividendo_anual", sa.Numeric(20, 8), nullable=True),
        sa.Column("roe", sa.Numeric(20, 8), nullable=True),
        sa.Column("payout", sa.Numeric(20, 8), nullable=True),
        sa.Column("g", sa.Numeric(20, 8), nullable=True),
        sa.Column("ke", sa.Numeric(20, 8), nullable=True),
        sa.Column("pl_historico", sa.Numeric(20, 8), nullable=True),
        sa.Column("pl_setor", sa.Numeric(20, 8), nullable=True),
        sa.Column("fcfe_1", sa.Numeric(20, 8), nullable=True),
        sa.Column("fcfe_2", sa.Numeric(20, 8), nullable=True),
        sa.Column("fcfe_3", sa.Numeric(20, 8), nullable=True),
        sa.Column("fcfe_4", sa.Numeric(20, 8), nullable=True),
        sa.Column("fcfe_5", sa.Numeric(20, 8), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ativo_id"], ["ativo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ativo_id", name="uq_valuation_premissa_ativo"),
    )


def downgrade() -> None:
    op.drop_table("valuation_premissa")
