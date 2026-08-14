"""`task_logs`. Per-attempt log lines for a scheduled task run, child of
`scheduled_tasks`."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class TaskLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "task_logs"

    scheduled_task_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("scheduled_tasks.id"), index=True
    )
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="INFO")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
