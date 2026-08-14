"""`cover_letters` — Part 4 §43. Every generated letter is stored for
regeneration and auditing."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class CoverLetter(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "cover_letters"

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id"), index=True
    )
    cv_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cv_versions.id")
    )
    generated_text: Mapped[str] = mapped_column(Text)
    ai_provider: Mapped[str] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
