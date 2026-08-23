"""`application_rules` — replaces the earlier `job_rules` design.

`condition` is JSONB, validated against the field/op allowlist in
`RuleEngineService` at write time (never at evaluation time) — see
`app/rules/`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from flames_shared.enums import RulePriorityTier
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class ApplicationRule(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "application_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_tier: Mapped[RulePriorityTier] = mapped_column(
        SqlEnum(RulePriorityTier, name="rule_priority_tier", native_enum=True), index=True
    )
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
