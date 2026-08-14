"""CRUD + lookup for `UserProfile` (one-to-one with `User`)."""

from __future__ import annotations

import uuid

from app.models.user_profile import UserProfile
from app.repositories.base_repository import BaseRepository


class UserProfileRepository(BaseRepository[UserProfile]):
    model = UserProfile

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None:
        result = await self.db.execute(self._base_query().where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()
