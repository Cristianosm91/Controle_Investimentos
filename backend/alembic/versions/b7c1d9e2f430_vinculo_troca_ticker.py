"""Vincula as pernas de uma troca de ticker."""

import sqlalchemy as sa

from alembic import op

revision = "b7c1d9e2f430"
down_revision = "c4d2e8a1b76f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("operacao") as batch:
        batch.add_column(sa.Column("transferencia_pareada_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_operacao_transferencia_pareada",
            "operacao",
            ["transferencia_pareada_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint(
            "uq_operacao_transferencia_pareada",
            ["transferencia_pareada_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("operacao") as batch:
        batch.drop_constraint("uq_operacao_transferencia_pareada", type_="unique")
        batch.drop_constraint("fk_operacao_transferencia_pareada", type_="foreignkey")
        batch.drop_column("transferencia_pareada_id")
