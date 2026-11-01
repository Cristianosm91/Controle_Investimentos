"""preserva as premissas em cada cálculo salvo de valuation

Revision ID: a9b5e7c1d204
Revises: f1a6c3d8b502
Create Date: 2026-10-31
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9b5e7c1d204"
down_revision: str | Sequence[str] | None = "f1a6c3d8b502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CAMPOS_PREMISSAS = (
    "lpa",
    "vpa",
    "dividendo_anual",
    "roe",
    "payout",
    "g",
    "ke",
    "pl_historico",
    "pl_setor",
    "fcfe_1",
    "fcfe_2",
    "fcfe_3",
    "fcfe_4",
    "fcfe_5",
)


def upgrade() -> None:
    for campo in _CAMPOS_PREMISSAS:
        op.add_column("valuation_historico", sa.Column(f"premissa_{campo}", sa.Numeric(20, 8), nullable=True))


def downgrade() -> None:
    for campo in reversed(_CAMPOS_PREMISSAS):
        op.drop_column("valuation_historico", f"premissa_{campo}")
