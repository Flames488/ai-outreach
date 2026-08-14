"""Application business logic: creation, retry, and read access.

This is the only thing that talks to both `app/playwright/` and
`app/repositories/application_repository.py` — and the only thing that
combines `RuleEngineService` with application creation.
"""

from __future__ import annotations

import uuid

from flames_shared.dto import ApplicationRecord, CoverLetterDraft, JobPosting
from flames_shared.enums import ApplicationStatus, ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FlamesAPIError
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.playwright.application_runner import PlaywrightApplicationRunner
from app.playwright.interface import ApplicationRunnerInterface
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.job_repository import JobRepository
from app.services.audit_service import AuditService, get_audit_service
from app.services.rule_engine_service import RuleEngineService, get_rule_engine_service


class ApplicationService:
    def __init__(
        self,
        db: AsyncSession,
        repository: ApplicationRepository,
        jobs: JobRepository,
        rules: RuleEngineService,
        audit: AuditService,
        audit_logs: AuditLogRepository,
        runner: ApplicationRunnerInterface,
    ) -> None:
        self._db = db
        self._repository = repository
        self._jobs = jobs
        self._rules = rules
        self._audit = audit
        self._audit_logs = audit_logs
        self._runner = runner

    async def get_timeline(self, application_id: uuid.UUID) -> list[AuditLog]:
        return await self._audit_logs.list_for_entity("application", str(application_id))

    async def list_applications(
        self, limit: int = 50, offset: int = 0, status: ApplicationStatus | None = None
    ) -> list[Application]:
        if status is not None:
            return await self._repository.list(
                limit=limit, offset=offset, application_status=status
            )
        return await self._repository.list(limit=limit, offset=offset)

    async def get_application(self, application_id: uuid.UUID) -> Application | None:
        return await self._repository.get(application_id)

    async def count_applications(self) -> int:
        return await self._repository.count()

    async def count_by_status(self, status: ApplicationStatus) -> int:
        return await self._repository.count_by_status(status)

    async def create_application(self, job_id: uuid.UUID, user_id: uuid.UUID) -> Application:
        """Mirrors Phase 2 §10's example shape: duplicate check -> rule
        evaluation -> create -> audit log, one session, one commit."""
        if await self._repository.exists_for_job(job_id):
            raise FlamesAPIError(409, ErrorCode.APPLICATION_FAILED, "Duplicate application")

        job = await self._jobs.get(job_id)
        if job is None:
            raise FlamesAPIError(404, ErrorCode.JOB_NOT_FOUND, "Job not found")

        decision = await self._rules.evaluate(job, user_id)
        status = (
            ApplicationStatus.QUEUED if decision.approved else ApplicationStatus.REVIEW_REQUIRED
        )

        application = await self._repository.create(
            job_id=job_id, user_id=user_id, application_status=status
        )
        await self._audit.log(
            entity="application",
            entity_id=application.id,
            action="created",
            performed_by=str(user_id),
            commit=False,
        )
        await self._db.commit()
        if status == ApplicationStatus.QUEUED:
            _enqueue_playwright_prep(application.id)
        return application

    async def retry_application(self, application_id: uuid.UUID) -> Application:
        application = await self._repository.get(application_id)
        if application is None:
            raise FlamesAPIError(404, ErrorCode.NOT_FOUND, "Application not found")
        if application.application_status != ApplicationStatus.FAILED:
            raise FlamesAPIError(
                409, ErrorCode.APPLICATION_FAILED, "Only failed applications can be retried"
            )
        application.application_status = ApplicationStatus.QUEUED
        application.retry_count += 1
        await self._db.commit()
        _enqueue_playwright_prep(application.id)
        return application

    async def apply_to_job(
        self, job: JobPosting, cover_letter: CoverLetterDraft
    ) -> ApplicationRecord:
        """Real submission — stays `NotImplementedError` (see
        `ApplicationRunnerInterface.apply`). Not to be confused with the
        `app.tasks.application_tasks.apply_to_job` Celery task, which only
        ever runs the dry-run path."""
        return await self._runner.apply(job, cover_letter)


def _enqueue_playwright_prep(application_id: uuid.UUID) -> None:
    """Fires the Phase 3 dry-run task for a newly-(re)queued application.
    A local import, same as `api/v1/jobs.py`'s `/search` route — keeps
    the Celery app import out of this module's top level."""
    from app.tasks.application_tasks import apply_to_job

    apply_to_job.delay(str(application_id))


def get_application_service(db: AsyncSession) -> ApplicationService:
    return ApplicationService(
        db=db,
        repository=ApplicationRepository(db),
        jobs=JobRepository(db),
        rules=get_rule_engine_service(db),
        audit=get_audit_service(db),
        audit_logs=AuditLogRepository(db),
        runner=PlaywrightApplicationRunner(),
    )
