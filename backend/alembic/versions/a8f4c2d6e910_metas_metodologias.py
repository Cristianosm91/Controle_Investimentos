"""Metas individuais das metodologias de alocação."""

import sqlalchemy as sa

from alembic import op

revision = "a8f4c2d6e910"
down_revision = "f3a7c9d1e542"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_metodologia",
        sa.Column("investidor_id", sa.Integer(), sa.ForeignKey("investidor.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("metodologia", sa.String(10), primary_key=True),
        sa.Column("categoria", sa.String(30), primary_key=True),
        sa.Column("peso_alvo", sa.Numeric(20, 8), nullable=False),
        sa.CheckConstraint("peso_alvo >= 0 AND peso_alvo <= 1", name="ck_meta_metodologia_peso"),
    )


def downgrade() -> None:
    count = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM meta_metodologia")).scalar()
    if count:
        raise RuntimeError("Downgrade indisponível: existem metas de metodologia que seriam perdidas.")
    op.drop_table("meta_metodologia")
