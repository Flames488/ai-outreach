"""`provider_logs`. Job-source and ATS provider call history, for
debugging a specific provider's reliability over time."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class ProviderLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "provider_logs"

    provider: Mapped[str] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(50))
    success: Mapped[bool] = mapped_column(Boolean, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
