"""CRUD for `TaskLog`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete

from app.models.task_log import TaskLog
from app.repositories.base_repository import BaseRepository


class TaskLogRepository(BaseRepository[TaskLog]):
    model = TaskLog

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self.db.execute(delete(TaskLog).where(TaskLog.created_at < cutoff))
        return result.rowcount or 0
