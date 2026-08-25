"""Job business logic: discovery orchestration + read access for the API.

This is the only thing that talks to `app/providers/`,
`app/repositories/job_repository.py`, and (via `JobIngestionService`) the
rest of the ingestion pipeline — API routes and Celery tasks call this,
never the providers or repositories directly (Part 3 §21/§23).
"""

from __future__ import annotations

import logging
import time
import uuid

from flames_shared.dto import JobPosting
from flames_shared.enums import JobStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.providers.base import Provider
from app.providers.mapping import standard_job_to_job_posting
from app.providers.models import SearchParams, StandardJob
from app.providers.registry import get_enabled_providers
from app.repositories.job_repository import JobRepository
from app.repositories.provider_log_repository import ProviderLogRepository
from app.services.job_ingestion_service import JobIngestionService, get_job_ingestion_service
from app.utils.retry import async_retry_with_backoff

logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        db: AsyncSession,
        repository: JobRepository,
        ingestion: JobIngestionService,
        provider_logs: ProviderLogRepository,
    ) -> None:
        self._db = db
        self._repository = repository
        self._ingestion = ingestion
        self._provider_logs = provider_logs

    async def list_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
        status: JobStatus | None = None,
        provider: str | None = None,
        remote: bool | None = None,
        country: str | None = None,
        employment_type: str | None = None,
        min_score: float | None = None,
    ) -> list[Job]:
        return await self._repository.list_filtered(
            limit=limit,
            offset=offset,
            status=status,
            provider=provider,
            remote=remote,
            country=country,
            employment_type=employment_type,
            min_score=min_score,
        )

    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        return await self._repository.get(job_id)

    async def count_jobs(self) -> int:
        return await self._repository.count()

    async def count_by_status(self, status: JobStatus) -> int:
        return await self._repository.count_by_status(status)

    async def search_all(self, params: SearchParams | None = None) -> list[Job]:
        """Search every enabled provider and ingest results into `jobs`.
        One provider failing (timeout, API change, auth expiry) never
        aborts the whole search cycle — per §30, "Indeed unavailable ->
        continue with other providers"; each attempt is logged to
        `provider_logs` regardless of outcome."""
        params = params or SearchParams()
        ingested: list[Job] = []
        for provider in get_enabled_providers():
            start = time.perf_counter()
            try:
                standard_jobs = await self._fetch_from_provider(provider, params)
            except Exception as exc:
                await self._log_provider_call(provider.name, success=False, detail=str(exc))
                logger.exception("Provider %s failed after retries; skipping it", provider.name)
                continue
            await self._log_provider_call(
                provider.name,
                success=True,
                detail=f"{len(standard_jobs)} results in {time.perf_counter() - start:.2f}s",
            )
            for standard_job in standard_jobs:
                ingested.append(await self._ingestion.ingest(standard_job))
        return ingested

    async def discover_jobs(self, params: SearchParams | None = None) -> list[JobPosting]:
        """Same provider fan-out as `search_all`, but returns in-memory
        DTOs without touching the database — used where only the
        cross-service `JobPosting` shape is needed (e.g. AI scoring)."""
        params = params or SearchParams()
        postings: list[JobPosting] = []
        for provider in get_enabled_providers():
            try:
                standard_jobs = await self._fetch_from_provider(provider, params)
            except Exception:
                logger.exception("Provider %s failed after retries; skipping it", provider.name)
                continue
            postings.extend(standard_job_to_job_posting(job) for job in standard_jobs)
        return postings

    @staticmethod
    @async_retry_with_backoff(max_attempts=3, base_delay_seconds=2.0)
    async def _fetch_from_provider(provider: Provider, params: SearchParams) -> list[StandardJob]:
        return await provider.fetch_jobs(params)

    async def _log_provider_call(self, provider: str, *, success: bool, detail: str) -> None:
        await self._provider_logs.create(
            provider=provider, action="search", success=success, detail=detail
        )
        await self._db.commit()

    async def deduplicate(self, jobs: list[JobPosting]) -> list[JobPosting]:
        seen: set[str] = set()
        unique: list[JobPosting] = []
        for job in jobs:
            if job.fingerprint not in seen:
                seen.add(job.fingerprint)
                unique.append(job)
        return unique


def get_job_service(db: AsyncSession) -> JobService:
    return JobService(
        db=db,
        repository=JobRepository(db),
        ingestion=get_job_ingestion_service(db),
        provider_logs=ProviderLogRepository(db),
    )
