"""CRUD for `ProviderLog`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete

from app.models.provider_log import ProviderLog
from app.repositories.base_repository import BaseRepository


class ProviderLogRepository(BaseRepository[ProviderLog]):
    model = ProviderLog

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self.db.execute(delete(ProviderLog).where(ProviderLog.created_at < cutoff))
        return result.rowcount or 0
