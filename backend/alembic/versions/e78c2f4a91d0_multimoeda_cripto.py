"""metadados cambiais por operação de cripto

Revision ID: e78c2f4a91d0
Revises: d7e4b2a9c610
Create Date: 2026-11-20
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e78c2f4a91d0"
down_revision: str | Sequence[str] | None = "d7e4b2a9c610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUNAS = {
    "cripto_valor_original": sa.Numeric(28, 8),
    "cripto_cambio_usd": sa.Numeric(28, 16),
    "cripto_cambio_usd_data_moeda": sa.Date(),
    "cripto_cambio_usd_data_usd": sa.Date(),
    "cripto_cambio_usd_fonte": sa.String(30),
    "cripto_valor_usd": sa.Numeric(28, 12),
    "taxas_moeda": sa.String(3),
    "taxas_cambio_brl": sa.Numeric(28, 16),
    "taxas_cambio_usd": sa.Numeric(28, 16),
    "taxas_cambio_usd_data_moeda": sa.Date(),
    "taxas_cambio_usd_data_usd": sa.Date(),
    "taxas_cambio_usd_fonte": sa.String(30),
    "taxas_valor_usd": sa.Numeric(28, 12),
}


def upgrade() -> None:
    with op.batch_alter_table("operacao") as batch:
        for nome, tipo in _COLUNAS.items():
            batch.add_column(sa.Column(nome, tipo, nullable=True))


def downgrade() -> None:
    colunas_com_dados = " OR ".join(f"{nome} IS NOT NULL" for nome in _COLUNAS)
    count = op.get_bind().execute(
        sa.text(f"SELECT count(*) FROM operacao WHERE {colunas_com_dados}")
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Downgrade indisponível: operações de cripto contêm metadados cambiais; "
            "exporte ou preserve esses dados antes de reverter."
        )
    with op.batch_alter_table("operacao") as batch:
        for nome in reversed(_COLUNAS):
            batch.drop_column(nome)
