"""`cv_versions`. Every uploaded CV is a new row; never overwrite an old
one. `job_type_tag` is used by CV auto-selection logic in a later phase's
Application Engine — this phase only needs the column and a way to set it
via API, not the selection logic itself."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class CVVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cv_versions"

    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer)
    job_type_tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
