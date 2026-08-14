"""CRUD + lookup for `CVVersion`. No `user_id` column — Flames is
single-tenant (see `ApplicationRepository.count_today`), so there is one
default CV, not one per user."""

from __future__ import annotations

from app.models.cv_version import CVVersion
from app.repositories.base_repository import BaseRepository


class CVVersionRepository(BaseRepository[CVVersion]):
    model = CVVersion

    async def get_default(self) -> CVVersion | None:
        result = await self.db.execute(self._base_query().where(CVVersion.is_default.is_(True)))
        return result.scalars().first()
