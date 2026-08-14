"""Writes `audit_logs` rows — insert-only, never edited (Part 4 §48).
This is what makes "why didn't Flames apply for this job?" answerable
later (Phase 2 §17's rule-blocked audit trail, among other events).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(self, db: AsyncSession, repo: AuditLogRepository) -> None:
        self._db = db
        self._repo = repo

    async def log(
        self,
        entity: str,
        entity_id: uuid.UUID | str,
        action: str,
        *,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        performed_by: str | None = None,
        commit: bool = True,
    ) -> AuditLog:
        """`commit=False` lets a caller that's already orchestrating a
        multi-step unit of work (e.g. ApplicationService.create_application)
        fold this write into its own single commit at the end."""
        entry = await self._repo.create(
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            old_value=old_value,
            new_value=new_value,
            performed_by=performed_by,
        )
        if commit:
            await self._db.commit()
        return entry


def get_audit_service(db: AsyncSession) -> AuditService:
    return AuditService(db=db, repo=AuditLogRepository(db))
