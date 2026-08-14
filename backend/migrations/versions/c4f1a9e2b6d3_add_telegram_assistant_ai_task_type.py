"""add telegram_assistant ai task type

Revision ID: c4f1a9e2b6d3
Revises: 8b39d399c5b2
Create Date: 2026-08-14 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = 'c4f1a9e2b6d3'
down_revision: Union[str, None] = '8b39d399c5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres can't add an enum value inside the same transaction Alembic
    # normally wraps a migration in — autocommit_block() runs this DDL on
    # its own, outside that transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE ai_task_type ADD VALUE IF NOT EXISTS 'telegram_assistant'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE — removing one requires
    # rebuilding the whole enum type. Not worth it for an additive-only
    # value; left as a no-op, same as this project's other enum-only
    # migrations would.
    pass
