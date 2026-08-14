"""CRUD for `SystemLog`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete

from app.models.system_log import SystemLog
from app.repositories.base_repository import BaseRepository


class SystemLogRepository(BaseRepository[SystemLog]):
    model = SystemLog

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self.db.execute(delete(SystemLog).where(SystemLog.created_at < cutoff))
        return result.rowcount or 0
