"""snapshots de fundamentos por ativo e fonte

Revision ID: c8715a0f4e2b
Revises: 281775d6ea3d
Create Date: 2026-10-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8715a0f4e2b"
down_revision: Union[str, Sequence[str], None] = "281775d6ea3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fundamento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ativo_id", sa.Integer(), nullable=False),
        sa.Column("data_ref", sa.Date(), nullable=False),
        sa.Column("fonte", sa.String(length=30), nullable=False),
        sa.Column("preco_lucro", sa.Numeric(20, 8), nullable=True),
        sa.Column("preco_valor_patrimonial", sa.Numeric(20, 8), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(20, 8), nullable=True),
        sa.Column("psr", sa.Numeric(20, 8), nullable=True),
        sa.Column("roe", sa.Numeric(20, 8), nullable=True),
        sa.Column("roic", sa.Numeric(20, 8), nullable=True),
        sa.Column("margem_bruta", sa.Numeric(20, 8), nullable=True),
        sa.Column("margem_ebit", sa.Numeric(20, 8), nullable=True),
        sa.Column("margem_liquida", sa.Numeric(20, 8), nullable=True),
        sa.Column("liquidez_corrente", sa.Numeric(20, 8), nullable=True),
        sa.Column("liquidez_media_2m", sa.Numeric(20, 8), nullable=True),
        sa.Column("patrimonio_liquido", sa.Numeric(20, 8), nullable=True),
        sa.Column("valor_mercado", sa.Numeric(20, 8), nullable=True),
        sa.Column("divida_liquida_patrimonio", sa.Numeric(20, 8), nullable=True),
        sa.Column("crescimento_receita_5a", sa.Numeric(20, 8), nullable=True),
        sa.Column("segmento_fii", sa.String(length=120), nullable=True),
        sa.Column("fii_dividendos_meses_12m", sa.Integer(), nullable=True),
        sa.Column("fii_dividend_yield_2a", sa.Numeric(20, 8), nullable=True),
        sa.Column("fii_dividendos_meses_2a", sa.Integer(), nullable=True),
        sa.Column("fii_ffo_yield", sa.Numeric(20, 8), nullable=True),
        sa.Column("fii_liquidez", sa.Numeric(20, 8), nullable=True),
        sa.Column("fii_area_m2", sa.Numeric(20, 8), nullable=True),
        sa.Column("fii_preco_m2", sa.Numeric(20, 8), nullable=True),
        sa.Column("fii_numero_imoveis", sa.Integer(), nullable=True),
        sa.Column("fii_numero_unidades", sa.Integer(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ativo_id"], ["ativo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ativo_id", "data_ref", "fonte", name="uq_fundamento_ativo_data_fonte"),
    )
    op.create_index("ix_fundamento_ativo_data", "fundamento", ["ativo_id", "data_ref"])


def downgrade() -> None:
    op.drop_index("ix_fundamento_ativo_data", table_name="fundamento")
    op.drop_table("fundamento")
