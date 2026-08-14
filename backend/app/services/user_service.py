"""Current-user profile read/update (ROADMAP.md's "APIs: User" item)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_profile import UserProfile
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(
        self, db: AsyncSession, users: UserRepository, profiles: UserProfileRepository
    ) -> None:
        self._db = db
        self._users = users
        self._profiles = profiles

    async def get_profile(self, user_id: uuid.UUID) -> UserProfile | None:
        return await self._profiles.get_by_user_id(user_id)

    async def update_profile(self, user: User, **updates: object) -> UserProfile:
        existing = await self._profiles.get_by_user_id(user.id)
        fields = {key: value for key, value in updates.items() if value is not None}
        if existing is None:
            profile = await self._profiles.create(user_id=user.id, **fields)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
            profile = existing
        await self._db.commit()
        return profile


def get_user_service(db: AsyncSession) -> UserService:
    return UserService(db=db, users=UserRepository(db), profiles=UserProfileRepository(db))
