"""Adiciona histórico local de alterações de lançamentos."""

import sqlalchemy as sa

from alembic import op

revision = "f3a7c9d1e542"
down_revision = "e78c2f4a91d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historico_lancamento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entidade", sa.String(length=20), nullable=False),
        sa.Column("registro_id", sa.Integer(), nullable=False),
        sa.Column("acao", sa.String(length=10), nullable=False),
        sa.Column("investidor_id", sa.Integer(), nullable=True),
        sa.Column("ativo_id", sa.Integer(), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("anterior_json", sa.Text(), nullable=True),
        sa.Column("novo_json", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_historico_lancamento_investidor_data",
        "historico_lancamento",
        ["investidor_id", "ocorrido_em"],
    )
    op.create_index(
        "ix_historico_lancamento_registro",
        "historico_lancamento",
        ["entidade", "registro_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_historico_lancamento_registro", table_name="historico_lancamento")
    op.drop_index("ix_historico_lancamento_investidor_data", table_name="historico_lancamento")
    op.drop_table("historico_lancamento")
