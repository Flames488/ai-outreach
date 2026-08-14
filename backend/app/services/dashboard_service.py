"""Aggregate summary data — the single source both the `/dashboard` API
route and the Telegram morning/evening reports pull from, so the two
can't drift into reporting different numbers (Phase 2 §16).
"""

from __future__ import annotations

from flames_shared.enums import ApplicationStatus, JobStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.application_repository import ApplicationRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.job_repository import JobRepository
from app.schemas.dashboard import DashboardSummary


class DashboardService:
    def __init__(
        self, jobs: JobRepository, applications: ApplicationRepository, emails: EmailRepository
    ) -> None:
        self._jobs = jobs
        self._applications = applications
        self._emails = emails

    async def get_summary(self) -> DashboardSummary:
        return DashboardSummary(
            total_jobs=await self._jobs.count(),
            new_jobs_today=await self._jobs.count_discovered_today(),
            matched_jobs=await self._jobs.count_by_status(JobStatus.MATCHED),
            pending_review=await self._jobs.count_by_status(JobStatus.REVIEW),
            total_applications=await self._applications.count(),
            applications_today=await self._applications.count_today(),
            queued_applications=await self._applications.count_by_status(ApplicationStatus.QUEUED),
            unprocessed_emails=await self._emails.count_unprocessed(),
        )


def get_dashboard_service(db: AsyncSession) -> DashboardService:
    return DashboardService(
        jobs=JobRepository(db),
        applications=ApplicationRepository(db),
        emails=EmailRepository(db),
    )
