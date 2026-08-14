"""CRUD + lookup for `FeatureFlag`."""

from __future__ import annotations

from app.models.feature_flag import FeatureFlag
from app.repositories.base_repository import BaseRepository


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    model = FeatureFlag

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        result = await self.db.execute(self._base_query().where(FeatureFlag.key == key))
        return result.scalar_one_or_none()
