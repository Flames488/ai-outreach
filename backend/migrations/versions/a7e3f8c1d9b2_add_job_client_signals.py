"""add job client signals

Revision ID: a7e3f8c1d9b2
Revises: c4f1a9e2b6d3
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7e3f8c1d9b2'
down_revision: Union[str, None] = 'c4f1a9e2b6d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('client_total_spend', sa.Numeric(12, 2), nullable=True))
    op.add_column('jobs', sa.Column('client_rating', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('client_payment_verified', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'client_payment_verified')
    op.drop_column('jobs', 'client_rating')
    op.drop_column('jobs', 'client_total_spend')
