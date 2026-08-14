"""`ai_usage_logs` — Part 6 §73. Protects the Groq free tier against
exhaustion: every AI call is logged here regardless of outcome."""

from __future__ import annotations

from datetime import datetime

from flames_shared.enums import AITaskType
from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class AIUsageLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_usage_logs"

    provider: Mapped[str] = mapped_column(String(50), index=True)
    model: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[AITaskType] = mapped_column(
        SqlEnum(AITaskType, name="ai_task_type", native_enum=True), index=True
    )
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
