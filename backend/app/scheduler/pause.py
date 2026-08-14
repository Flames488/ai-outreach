"""Checked by `search_tasks`/`ai_tasks` before doing work — set via the
Telegram `/pause` and `/resume` commands (`app/telegram/handlers.py`),
backed by a `feature_flags` row rather than an in-memory flag so it
survives a worker restart.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.feature_flag_repository import FeatureFlagRepository

PAUSE_FLAG_KEY = "operations_paused"


async def is_paused(db: AsyncSession) -> bool:
    flag = await FeatureFlagRepository(db).get_by_key(PAUSE_FLAG_KEY)
    return flag is not None and flag.enabled
