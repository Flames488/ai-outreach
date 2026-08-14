"""`notifications` — Part 4 §45. Every notification sent, across any channel."""

from __future__ import annotations

from datetime import datetime

from flames_shared.enums import NotificationChannel
from sqlalchemy import DateTime, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    type: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[NotificationChannel] = mapped_column(
        SqlEnum(NotificationChannel, native_enum=False), index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
