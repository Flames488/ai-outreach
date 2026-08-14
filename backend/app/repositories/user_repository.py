"""CRUD + user-specific queries for `User`."""

from __future__ import annotations

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(self._base_query().where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_telegram_chat_id(self, telegram_chat_id: str) -> User | None:
        result = await self.db.execute(
            self._base_query().where(User.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()
