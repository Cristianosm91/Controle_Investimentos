"""planejamento: vencimento de renda fixa, lotes de importação, preço-alvo no radar e metas

Revision ID: e4b9d07c2a13
Revises: a61c83e924f0
Create Date: 2026-10-31
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4b9d07c2a13"
down_revision: str | Sequence[str] | None = "a61c83e924f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LANCAMENTOS = ("operacao", "provento", "mov_caixa")


def upgrade() -> None:
    with op.batch_alter_table("ativo") as batch:
        batch.add_column(sa.Column("data_vencimento", sa.Date(), nullable=True))
        batch.add_column(sa.Column("isento_ir", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "lote_importacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("arquivo", sa.String(200), nullable=True),
        sa.Column("investidor_id", sa.Integer(), sa.ForeignKey("investidor.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("desfeito_em", sa.DateTime(), nullable=True),
        sa.Column("operacoes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proventos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("caixa", sa.Integer(), nullable=False, server_default="0"),
    )
    for tabela in _LANCAMENTOS:
        with op.batch_alter_table(tabela) as batch:
            batch.add_column(sa.Column("lote_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{tabela}_lote_id", "lote_importacao", ["lote_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index(f"ix_{tabela}_lote_id", ["lote_id"])

    with op.batch_alter_table("ativo_radar") as batch:
        batch.add_column(sa.Column("preco_alvo", sa.Numeric(20, 8), nullable=True))

    op.create_table(
        "meta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("valor_alvo", sa.Numeric(20, 8), nullable=False),
        sa.Column("data_alvo", sa.Date(), nullable=False),
        sa.Column("aporte_mensal", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("rentabilidade_aa", sa.Numeric(20, 8), nullable=False),
        sa.Column("rendimento_aa", sa.Numeric(20, 8), nullable=True),
        sa.Column("investidores", sa.String(200), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("meta")
    with op.batch_alter_table("ativo_radar") as batch:
        batch.drop_column("preco_alvo")
    for tabela in _LANCAMENTOS:
        with op.batch_alter_table(tabela) as batch:
            batch.drop_index(f"ix_{tabela}_lote_id")
            batch.drop_constraint(f"fk_{tabela}_lote_id", type_="foreignkey")
            batch.drop_column("lote_id")
    op.drop_table("lote_importacao")
    with op.batch_alter_table("ativo") as batch:
        batch.drop_column("isento_ir")
        batch.drop_column("data_vencimento")
