"""CRUD + lookup for `ScheduledTask`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from app.models.scheduled_task import ScheduledTask
from app.repositories.base_repository import BaseRepository


class ScheduledTaskRepository(BaseRepository[ScheduledTask]):
    model = ScheduledTask

    async def get_latest_by_name(self, task_name: str) -> ScheduledTask | None:
        result = await self.db.execute(
            select(ScheduledTask)
            .where(ScheduledTask.task_name == task_name)
            .order_by(ScheduledTask.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def archive_completed_older_than(self, cutoff: datetime) -> int:
        """Marks (never deletes) old finished runs so "current queue"
        views stay fast without losing history (Phase 2 §18)."""
        result = await self.db.execute(
            update(ScheduledTask)
            .where(
                ScheduledTask.completed_at.is_not(None),
                ScheduledTask.completed_at < cutoff,
                ScheduledTask.archived.is_(False),
            )
            .values(archived=True)
        )
        return result.rowcount or 0
