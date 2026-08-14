"""Telegram-specific auth: resolves a `User` by `telegram_chat_id`,
separate from the JWT dependency chain built for HTTP (Phase 2 §07) —
Telegram requests never go through `get_current_user`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


async def get_telegram_user(db: AsyncSession, chat_id: str) -> User | None:
    return await UserRepository(db).get_by_telegram_chat_id(chat_id)
