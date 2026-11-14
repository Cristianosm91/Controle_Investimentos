"""Corrige a moeda do ativo INTR para USD.

Revision ID: c0d3a8b7f1e2
Revises: f1a6c3d8b502, b7c1d9e2f430
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c0d3a8b7f1e2"
down_revision: str | Sequence[str] | None = ("f1a6c3d8b502", "b7c1d9e2f430")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE ativo SET moeda = 'USD' WHERE ticker = 'INTR'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE ativo SET moeda = 'BRL' WHERE ticker = 'INTR' AND moeda = 'USD'"))