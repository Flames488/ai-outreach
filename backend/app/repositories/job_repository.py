"""CRUD + job-specific queries for `Job`. Business logic lives in
app/services/job_service.py, never here."""

from __future__ import annotations

from flames_shared.enums import JobStatus
from sqlalchemy import func, select

from app.models.job import Job
from app.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    async def get_by_provider_and_external_id(
        self, provider: str, external_job_id: str
    ) -> Job | None:
        result = await self.db.execute(
            self._base_query().where(
                Job.provider == provider, Job.external_job_id == external_job_id
            )
        )
        return result.scalar_one_or_none()

    async def count_by_status(self, status: JobStatus) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Job)
            .where(Job.status == status, Job.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def list_filtered(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: JobStatus | None = None,
        provider: str | None = None,
        remote: bool | None = None,
        country: str | None = None,
        employment_type: str | None = None,
        min_score: float | None = None,
    ) -> list[Job]:
        query = self._base_query()
        if status is not None:
            query = query.where(Job.status == status)
        if provider is not None:
            query = query.where(Job.provider == provider)
        if remote is not None:
            query = query.where(Job.remote == remote)
        if country is not None:
            query = query.where(Job.country == country)
        if employment_type is not None:
            query = query.where(Job.employment_type == employment_type)
        if min_score is not None:
            query = query.where(Job.ai_score >= min_score)
        query = query.order_by(Job.discovered_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_discovered_today(self) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Job)
            .where(
                Job.deleted_at.is_(None),
                func.date(Job.discovered_at) == func.current_date(),
            )
        )
        return result.scalar_one()
