"""`feature_flags` — Part 4 §37. DB-backed runtime override on top of the
ENABLE_* env vars in app/config/settings.py (Part 3 §31) — the env vars
remain the boot-time defaults/fail-safe; this table lets a flag flip
without a redeploy."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class FeatureFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
