"""`system_logs`. Important system events that shouldn't live only in
text log files: application failed, Groq unavailable, provider timeout,
Gmail disconnected, Playwright crashed, migration ran, worker restarted."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class SystemLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "system_logs"

    event: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    service: Mapped[str] = mapped_column(String(50), index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
