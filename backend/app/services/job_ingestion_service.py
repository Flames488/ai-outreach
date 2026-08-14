"""Maps a provider-normalized `StandardJob` onto a stored `jobs` row
(Phase 2 §13's "missing piece Phase 1 flagged and never wrote down").

Providers only ever produce `StandardJob` — they never touch the database
directly, which keeps them testable without one. This is the only thing
that does.
"""

from __future__ import annotations

from datetime import UTC, datetime

from flames_shared.enums import JobStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.job import Job
from app.providers.models import StandardJob
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_skill_repository import JobSkillRepository


class JobIngestionService:
    def __init__(
        self,
        db: AsyncSession,
        jobs: JobRepository,
        companies: CompanyRepository,
        job_skills: JobSkillRepository,
    ) -> None:
        self._db = db
        self._jobs = jobs
        self._companies = companies
        self._job_skills = job_skills

    async def ingest(self, normalized: StandardJob) -> Job:
        """Idempotent: re-ingesting a job already seen (same provider +
        external id) returns the existing row unchanged rather than
        duplicating it (Phase 1 Part 9 §127's duplicate-job protection)."""
        existing = await self._jobs.get_by_provider_and_external_id(
            normalized.provider, normalized.id
        )
        if existing is not None:
            return existing

        company = await self._get_or_create_company(normalized.company)

        job = await self._jobs.create(
            provider=normalized.provider,
            external_job_id=normalized.id,
            title=normalized.job_title,
            description=normalized.description,
            company_id=company.id if company else None,
            location=normalized.location,
            country=normalized.country,
            city=normalized.city,
            salary_min=normalized.salary_min,
            salary_max=normalized.salary_max,
            currency=normalized.currency,
            employment_type=normalized.employment_type,
            experience_level=normalized.experience_level,
            remote=normalized.is_remote,
            application_url=normalized.application_url,
            posted_date=normalized.posted_date,
            discovered_at=datetime.now(UTC),
            expires_at=normalized.closing_date,
            status=JobStatus.NEW,
        )

        for skill in normalized.skills:
            await self._job_skills.create(job_id=job.id, skill_name=skill)

        await self._db.commit()
        return job

    async def _get_or_create_company(self, company_name: str) -> Company | None:
        if not company_name:
            return None
        existing = await self._companies.get_by_name(company_name)
        if existing is not None:
            return existing
        return await self._companies.create(company_name=company_name)


def get_job_ingestion_service(db: AsyncSession) -> JobIngestionService:
    return JobIngestionService(
        db=db,
        jobs=JobRepository(db),
        companies=CompanyRepository(db),
        job_skills=JobSkillRepository(db),
    )
