"""`email_messages`. Gmail data."""

from __future__ import annotations

from datetime import datetime

from flames_shared.enums import EmailCategory
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, SoftDeleteMixin, UUIDPrimaryKeyMixin


class EmailMessage(UUIDPrimaryKeyMixin, SoftDeleteMixin, Base):
    __tablename__ = "email_messages"

    gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender: Mapped[str] = mapped_column(String(255))
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(500))
    snippet: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    category: Mapped[EmailCategory] = mapped_column(
        SqlEnum(EmailCategory, name="email_category", native_enum=True),
        default=EmailCategory.UNKNOWN,
        index=True,
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
