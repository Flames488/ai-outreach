"""CRUD + application-specific queries for `Application`. Business logic
lives in app/services/application_service.py, never here."""

from __future__ import annotations

import uuid

from flames_shared.enums import ApplicationStatus
from sqlalchemy import func, select

from app.models.application import Application
from app.repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    model = Application

    async def exists_for_job(self, job_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.job_id == job_id, Application.deleted_at.is_(None))
        )
        return result.scalar_one() > 0

    async def count_by_status(self, status: ApplicationStatus) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.application_status == status, Application.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def count_today(self) -> int:
        """Global count — used by DashboardService (Flames is single-tenant)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.deleted_at.is_(None),
                func.date(Application.created_at) == func.current_date(),
            )
        )
        return result.scalar_one()

    async def count_today_for_user(self, user_id: uuid.UUID) -> int:
        """Used by the Rule Engine's daily-limit rules (Phase 1 Part 10 §148)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user_id,
                Application.deleted_at.is_(None),
                func.date(Application.created_at) == func.current_date(),
            )
        )
        return result.scalar_one()
