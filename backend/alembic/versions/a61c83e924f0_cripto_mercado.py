"""identificador CoinGecko e cache local de mercado cripto"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a61c83e924f0"
down_revision: str | Sequence[str] | None = "d2745cfb6a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ativo") as batch:
        batch.add_column(sa.Column("coingecko_id", sa.String(120), nullable=True))
        batch.create_unique_constraint("uq_ativo_coingecko_id", ["coingecko_id"])
    op.create_table(
        "cripto_mercado",
        sa.Column("ativo_id", sa.Integer(), sa.ForeignKey("ativo.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preco_usd", sa.Numeric(20, 8), nullable=False),
        sa.Column("market_cap_usd", sa.Numeric(30, 8), nullable=True),
        sa.Column("variacao_24h", sa.Numeric(20, 8), nullable=True),
        sa.Column("variacao_7d", sa.Numeric(20, 8), nullable=True),
        sa.Column("variacao_30d", sa.Numeric(20, 8), nullable=True),
        sa.Column("fonte", sa.String(30), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cripto_mercado")
    with op.batch_alter_table("ativo") as batch:
        batch.drop_constraint("uq_ativo_coingecko_id", type_="unique")
        batch.drop_column("coingecko_id")
