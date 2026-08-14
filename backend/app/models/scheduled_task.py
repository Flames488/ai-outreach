"""`scheduled_tasks`. Every scheduled task run — written automatically by
the `@track_scheduled_task` decorator (`app/scheduler/tracking.py`), never
by hand in each task body."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class ScheduledTask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "scheduled_tasks"

    task_name: Mapped[str] = mapped_column(String(255), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    worker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    # Not in the original field list — `archive_completed_tasks` (Phase 2
    # §18) marks rather than deletes, so the "current queue" view can
    # filter this out without losing history.
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
