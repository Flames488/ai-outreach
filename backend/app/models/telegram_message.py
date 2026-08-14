"""`telegram_messages`. Raw log of bot traffic — protocol-level "what
happened on the wire", separate from `notifications` (business-level
"what was sent")."""

from __future__ import annotations

import uuid
from datetime import datetime

from flames_shared.enums import TelegramDirection
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class TelegramMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "telegram_messages"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    direction: Mapped[TelegramDirection] = mapped_column(
        SqlEnum(TelegramDirection, name="telegram_direction", native_enum=True)
    )
    command: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
