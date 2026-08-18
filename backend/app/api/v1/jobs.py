"""Job listing/search endpoints. Goes through JobService, never the
database directly (Part 3 §21).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from flames_shared.enums import ErrorCode, JobStatus

from app.api.deps import get_current_user, get_job_ingestion_service_dep, get_job_service_dep
from app.core.exceptions import FlamesAPIError
from app.models.user import User
from app.providers.models import StandardJob
from app.schemas.envelope import SuccessResponse
from app.schemas.job import JobCreate, JobDetail, JobRead
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=SuccessResponse[list[JobRead]])
async def list_jobs(
    job_service: Annotated[JobService, Depends(get_job_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
    offset: int = 0,
    status: JobStatus | None = None,
    provider: str | None = None,
    remote: bool | None = None,
    country: str | None = None,
    employment_type: str | None = None,
    min_score: float | None = None,
) -> SuccessResponse[list[JobRead]]:
    """List discovered jobs. Filterable by status, provider, remote,
    country, employment_type, and min_score — each maps to an indexed
    column (`05-Database-Models.md`'s index list)."""
    jobs = await job_service.list_jobs(
        limit=limit,
        offset=offset,
        status=status,
        provider=provider,
        remote=remote,
        country=country,
        employment_type=employment_type,
        min_score=min_score,
    )
    data = [JobRead.model_validate(job) for job in jobs]
    return SuccessResponse(
        message="Jobs retrieved successfully.",
        data=data,
        meta={"limit": limit, "offset": offset, "count": len(data)},
    )


@router.get("/{job_id}", response_model=SuccessResponse[JobDetail])
async def get_job(
    job_id: uuid.UUID,
    job_service: Annotated[JobService, Depends(get_job_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[JobDetail]:
    """Get a single job, including its full description."""
    job = await job_service.get_job(job_id)
    if job is None:
        raise FlamesAPIError(404, ErrorCode.JOB_NOT_FOUND, "Job not found")
    return SuccessResponse(
        message="Job retrieved successfully.", data=JobDetail.model_validate(job)
    )


@router.post("", response_model=SuccessResponse[JobRead], status_code=201)
async def create_job(
    body: JobCreate,
    ingestion: Annotated[JobIngestionService, Depends(get_job_ingestion_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[JobRead]:
    """Manually add a job — the intake point for freelance-platform gigs
    (Upwork, Fiverr, etc.) that no provider discovers automatically.
    Client signals (client_total_spend/rating/payment_verified) only ever
    get in through here; there's deliberately no scraping-based path onto
    them (see JobCreate's docstring)."""
    standard_job = StandardJob(
        id=f"manual-{uuid.uuid4()}",
        provider=body.provider,
        job_title=body.title,
        company=body.company_name or "",
        location=body.location,
        salary=None,
        employment_type=body.employment_type,
        experience_level=None,
        description=body.description,
        skills=[],
        application_url=body.application_url,
        company_url=None,
        posted_date=datetime.now(UTC),
        source_url=body.application_url,
        is_remote=body.remote,
        country=body.country,
        city=body.city,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        currency=body.currency,
        client_total_spend=body.client_total_spend,
        client_rating=body.client_rating,
        client_payment_verified=body.client_payment_verified,
    )
    job = await ingestion.ingest(standard_job)
    return SuccessResponse(message="Job added successfully.", data=JobRead.model_validate(job))


@router.post("/search", response_model=SuccessResponse[dict])
async def trigger_search(
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """Triggers a Celery search task and returns immediately (Phase 2 §55
    /§72 — the API never blocks on provider calls). Requires an actual
    Celery worker consuming the queue — see /search-sync if none exists
    in this deployment."""
    from app.tasks.search_tasks import search_all_providers

    task = search_all_providers.delay()
    return SuccessResponse(message="Job search queued.", data={"task_id": task.id})


@router.post("/search-sync", response_model=SuccessResponse[dict])
async def trigger_search_sync(
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """Runs search + AI scoring synchronously, in-process, instead of via
    Celery — for deployments with no worker to consume /search's queue
    (Render's free tier has no free Background Worker plan; this route
    exists so search still works there). Blocks the request for the
    duration, which can be tens of seconds to a few minutes depending on
    how many jobs need scoring — that's the deliberate trade-off for not
    needing a paid always-on process. Safe to call again if it times out
    client-side: both steps only ever touch NEW jobs, so a second call
    picks up wherever the first left off rather than redoing work."""
    from app.tasks.ai_tasks import _score_pending_jobs
    from app.tasks.search_tasks import _search_all_providers

    found = await _search_all_providers()
    await _score_pending_jobs()
    return SuccessResponse(
        message=f"Search complete: {found} new job(s) found and scored.",
        data={"jobs_found": found},
    )
