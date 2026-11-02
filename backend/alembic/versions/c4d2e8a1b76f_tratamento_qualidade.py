"""Persist reviewed data-quality findings."""

import sqlalchemy as sa

from alembic import op

revision = "c4d2e8a1b76f"
down_revision = "a9b5e7c1d204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tratamento_qualidade",
        sa.Column("fingerprint", sa.String(length=64), primary_key=True),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("severidade", sa.String(length=10), nullable=False),
        sa.Column("descricao", sa.String(length=500), nullable=False),
        sa.Column("itens", sa.String(length=4000), nullable=False),
        sa.Column("operacao_ids", sa.String(length=2000), nullable=False),
        sa.Column("provento_ids", sa.String(length=2000), nullable=False),
        sa.Column("caixa_ids", sa.String(length=2000), nullable=False),
        sa.Column("ativo_ids", sa.String(length=2000), nullable=False),
        sa.Column("investidor_ids", sa.String(length=2000), nullable=False),
        sa.Column("tratado_em", sa.String(length=40), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tratamento_qualidade")
