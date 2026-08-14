"""`email_labels` — Part 4 §37. Gmail labels attached to a message,
child of `email_messages`."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class EmailLabel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "email_labels"

    email_message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("email_messages.id"), index=True
    )
    label: Mapped[str] = mapped_column(String(100), index=True)
