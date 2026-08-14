"""Job listing/search endpoints. Goes through JobService, never the
database directly (Part 3 §21).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from flames_shared.enums import ErrorCode, JobStatus

from app.api.deps import get_current_user, get_job_service_dep
from app.core.exceptions import FlamesAPIError
from app.models.user import User
from app.schemas.envelope import SuccessResponse
from app.schemas.job import JobDetail, JobRead
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


@router.post("/search", response_model=SuccessResponse[dict])
async def trigger_search(
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """Triggers a Celery search task and returns immediately (Phase 2 §55
    /§72 — the API never blocks on provider calls)."""
    from app.tasks.search_tasks import search_all_providers

    task = search_all_providers.delay()
    return SuccessResponse(message="Job search queued.", data={"task_id": task.id})
