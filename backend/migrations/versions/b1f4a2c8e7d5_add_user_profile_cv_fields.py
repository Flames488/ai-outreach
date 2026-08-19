"""add user profile cv fields

Revision ID: b1f4a2c8e7d5
Revises: a7e3f8c1d9b2
Create Date: 2026-08-19 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b1f4a2c8e7d5'
down_revision: Union[str, None] = 'a7e3f8c1d9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('professional_summary', sa.Text(), nullable=True))
    op.add_column('user_profiles', sa.Column('skills', postgresql.JSONB(), nullable=True))
    op.add_column('user_profiles', sa.Column('desired_titles', postgresql.JSONB(), nullable=True))
    op.add_column('user_profiles', sa.Column('notable_projects', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'notable_projects')
    op.drop_column('user_profiles', 'desired_titles')
    op.drop_column('user_profiles', 'skills')
    op.drop_column('user_profiles', 'professional_summary')
