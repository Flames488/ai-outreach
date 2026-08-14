"""CRUD + email-specific queries for `EmailMessage`. Business logic
lives in app/services/email_service.py, never here."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.email_message import EmailMessage
from app.repositories.base_repository import BaseRepository


class EmailRepository(BaseRepository[EmailMessage]):
    model = EmailMessage

    async def get_by_gmail_message_id(self, gmail_message_id: str) -> EmailMessage | None:
        result = await self.db.execute(
            self._base_query().where(EmailMessage.gmail_message_id == gmail_message_id)
        )
        return result.scalar_one_or_none()

    async def count_unprocessed(self) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(EmailMessage)
            .where(EmailMessage.processed.is_(False), EmailMessage.deleted_at.is_(None))
        )
        return result.scalar_one()
