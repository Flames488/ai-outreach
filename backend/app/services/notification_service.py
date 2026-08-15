"""Formats, persists, and dispatches all outbound alerts.

Writes a `notifications` row for every attempt, then routes to the right
channel (Telegram for now). `SYSTEM`-level alerts always send, bypassing
user notification preferences (Phase 1 Part 10 §156 / Phase 2 §16);
anything else is gated by the user's stored preferences
(`user_profiles.notification_preferences`).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flames_shared.dto import NotificationPayload
from flames_shared.enums import NotificationChannel, NotificationLevel
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.telegram.interface import NotificationProvider


class NotificationService:
    def __init__(
        self,
        db: AsyncSession,
        provider: NotificationProvider,
        notifications: NotificationRepository,
        user_profiles: UserProfileRepository,
    ) -> None:
        self._db = db
        self._provider = provider
        self._notifications = notifications
        self._user_profiles = user_profiles

    async def notify(
        self,
        title: str,
        body: str,
        level: NotificationLevel = NotificationLevel.INFO,
        user_id: uuid.UUID | None = None,
        notification_type: str = "general",
        action_url: str | None = None,
        action_label: str | None = None,
    ) -> bool:
        if level != NotificationLevel.SYSTEM and user_id is not None:
            profile = await self._user_profiles.get_by_user_id(user_id)
            if profile is not None and not profile.notification_preferences.get(
                notification_type, True
            ):
                return False  # user opted out of this notification type

        record = await self._notifications.create(
            type=notification_type,
            title=title,
            message=body,
            channel=NotificationChannel.TELEGRAM,
            status="pending",
        )
        metadata = {"action_url": action_url, "action_label": action_label} if action_url else {}
        sent = await self._provider.send(
            NotificationPayload(title=title, body=body, level=level, metadata=metadata)
        )
        record.status = "sent" if sent else "failed"
        record.sent_at = datetime.now(UTC) if sent else None
        await self._db.commit()
        return sent

    async def notify_error(self, title: str, body: str) -> bool:
        return await self.notify(title, body, level=NotificationLevel.ERROR)

    async def notify_success(self, title: str, body: str) -> bool:
        return await self.notify(title, body, level=NotificationLevel.SUCCESS)

    async def notify_system(self, title: str, body: str) -> bool:
        return await self.notify(title, body, level=NotificationLevel.SYSTEM)


def get_notification_service(db: AsyncSession) -> NotificationService:
    from app.telegram.client import TelegramProvider

    return NotificationService(
        db=db,
        provider=TelegramProvider(),
        notifications=NotificationRepository(db),
        user_profiles=UserProfileRepository(db),
    )
