"""Preserva nomes de corretoras unificadas.

Revision ID: a2e6c19b407d
Revises: c0d3a8b7f1e2
"""
import sqlalchemy as sa

from alembic import op

revision = "a2e6c19b407d"
down_revision = "c0d3a8b7f1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corretora_apelido",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(60), nullable=False, unique=True),
        sa.Column("corretora_id", sa.Integer(), sa.ForeignKey("corretora.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_corretora_apelido_corretora_id", "corretora_apelido", ["corretora_id"])


def downgrade() -> None:
    # Remover os apelidos faria importações futuras recriarem corretoras unificadas.
    raise RuntimeError("Downgrade indisponível: restaurar backup anterior à migração para preservar os apelidos.")
