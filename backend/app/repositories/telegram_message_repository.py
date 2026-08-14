"""CRUD for `TelegramMessage`."""

from __future__ import annotations

from app.models.telegram_message import TelegramMessage
from app.repositories.base_repository import BaseRepository


class TelegramMessageRepository(BaseRepository[TelegramMessage]):
    model = TelegramMessage
