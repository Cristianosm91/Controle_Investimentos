"""Armazena CDI diario oficial e intervalos consultados, sem converter historico."""

import sqlalchemy as sa

from alembic import op

revision = "d7e4b2a9c610"
down_revision = "a2e6c19b407d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cdi_diario",
        sa.Column("data", sa.Date(), primary_key=True),
        sa.Column("taxa", sa.Numeric(20, 12, asdecimal=True), nullable=False),
    )
    op.create_table(
        "cobertura_cdi",
        sa.Column("inicio", sa.Date(), primary_key=True),
        sa.Column("fim", sa.Date(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cobertura_cdi")
    op.drop_table("cdi_diario")
