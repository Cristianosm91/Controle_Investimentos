"""histórico dos últimos cálculos de valuation por ativo

Revision ID: f1a6c3d8b502
Revises: e4b9d07c2a13
Create Date: 2026-10-31
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a6c3d8b502"
down_revision: str | Sequence[str] | None = "e4b9d07c2a13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "valuation_historico",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ativo_id", sa.Integer(), nullable=False),
        sa.Column("calculado_em", sa.DateTime(), nullable=False),
        sa.Column("cotacao", sa.Numeric(20, 8), nullable=True),
        sa.Column("preco_mediano", sa.Numeric(20, 8), nullable=True),
        sa.Column("modelos_disponiveis", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("graham", sa.Numeric(20, 8), nullable=True),
        sa.Column("bazin", sa.Numeric(20, 8), nullable=True),
        sa.Column("dcf_fcfe", sa.Numeric(20, 8), nullable=True),
        sa.Column("gordon", sa.Numeric(20, 8), nullable=True),
        sa.Column("pl_historico", sa.Numeric(20, 8), nullable=True),
        sa.Column("pl_setor", sa.Numeric(20, 8), nullable=True),
        sa.Column("pvp_justificado", sa.Numeric(20, 8), nullable=True),
        sa.ForeignKeyConstraint(["ativo_id"], ["ativo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_valuation_historico_ativo", "valuation_historico", ["ativo_id", "calculado_em"])


def downgrade() -> None:
    op.drop_index("ix_valuation_historico_ativo", table_name="valuation_historico")
    op.drop_table("valuation_historico")
