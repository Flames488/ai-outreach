"""Gmail sync orchestration, AI classification, and dedup on
`gmail_message_id`. This is the only thing that talks to both
`app/gmail/` and `app/repositories/email_repository.py`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flames_shared.enums import EmailCategory, NotificationLevel
from sqlalchemy.ext.asyncio import AsyncSession

from app.gmail.client import GmailClient
from app.models.email_message import EmailMessage
from app.models.user import User
from app.repositories.email_repository import EmailRepository
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService
from app.utils.encryption import decrypt, encrypt

_HIGH_PRIORITY_CATEGORIES = {
    EmailCategory.INTERVIEW,
    EmailCategory.JOB_OFFER,
    EmailCategory.ASSESSMENT,
    EmailCategory.TECHNICAL_TEST,
}


class GmailAuthError(Exception):
    """The stored refresh token is missing or no longer valid — the
    connection needs to be re-established via /gmail/connect."""


class EmailService:
    def __init__(
        self,
        db: AsyncSession,
        emails: EmailRepository,
        users: UserRepository,
        ai: AIService,
        notifications: NotificationService,
    ) -> None:
        self._db = db
        self._emails = emails
        self._users = users
        self._ai = ai
        self._notifications = notifications

    async def connect_gmail(self, user: User, refresh_token: str) -> None:
        """Persists the OAuth refresh token — encrypted, never the raw
        value (Phase 2 §15) — after a successful /gmail/callback exchange."""
        user.google_refresh_token_encrypted = encrypt(refresh_token)
        user.gmail_connected = True
        await self._db.commit()

    async def list_emails(self, limit: int = 50, offset: int = 0) -> list[EmailMessage]:
        return await self._emails.list(limit=limit, offset=offset)

    async def get_email(self, email_id: uuid.UUID) -> EmailMessage | None:
        return await self._emails.get(email_id)

    async def sync_inbox_for_user(self, user: User) -> list[EmailMessage]:
        if not user.google_refresh_token_encrypted:
            raise GmailAuthError("Gmail is not connected for this user")

        try:
            refresh_token = decrypt(user.google_refresh_token_encrypted)
            client = GmailClient(refresh_token)
            raw_messages = client.fetch_messages_since(user.gmail_last_synced_at)
        except GmailAuthError:
            raise
        except Exception as exc:
            # invalid_grant and friends -> the connection is broken, not a
            # transient failure. Mark it and raise a SYSTEM alert rather
            # than failing the sync task silently (Phase 2 §15).
            user.gmail_connected = False
            await self._db.commit()
            await self._notifications.notify_system(
                title="Gmail disconnected",
                body=f"Gmail sync failed for {user.email}: {exc}. Reconnect via /gmail/connect.",
            )
            raise GmailAuthError(str(exc)) from exc

        stored: list[EmailMessage] = []
        for raw in raw_messages:
            gmail_message_id = raw["id"]
            if await self._emails.get_by_gmail_message_id(gmail_message_id) is not None:
                continue  # dedup

            headers = {
                header["name"]: header["value"]
                for header in raw.get("payload", {}).get("headers", [])
            }
            email = await self._emails.create(
                gmail_message_id=gmail_message_id,
                thread_id=raw.get("threadId"),
                sender=headers.get("From", ""),
                recipient=headers.get("To"),
                subject=headers.get("Subject", ""),
                snippet=raw.get("snippet", ""),
                received_at=_parse_internal_date(raw.get("internalDate")),
                category=EmailCategory.UNKNOWN,
                processed=False,
                raw_payload=raw,
            )
            stored.append(email)

        user.gmail_last_synced_at = datetime.now(UTC)
        await self._db.commit()
        return stored

    async def classify_email(self, email: EmailMessage) -> EmailMessage:
        content = f"Subject: {email.subject}\nFrom: {email.sender}\n\n{email.snippet}"
        result = await self._ai.classify_email(content)
        email.category = result.category
        email.processed = True
        await self._db.commit()

        if email.category in _HIGH_PRIORITY_CATEGORIES or result.important:
            await self._notifications.notify(
                title=f"New {email.category.value.replace('_', ' ')} email",
                body=f"{email.subject} — from {email.sender}",
                level=NotificationLevel.SUCCESS,
                notification_type="email_classified",
            )
        return email


def get_email_service(db: AsyncSession) -> EmailService:
    from app.services.ai_service import get_ai_service
    from app.services.notification_service import get_notification_service

    return EmailService(
        db=db,
        emails=EmailRepository(db),
        users=UserRepository(db),
        ai=get_ai_service(db),
        notifications=get_notification_service(db),
    )


def _parse_internal_date(internal_date: object) -> datetime:
    if isinstance(internal_date, str) and internal_date.isdigit():
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=UTC)
    return datetime.now(UTC)
