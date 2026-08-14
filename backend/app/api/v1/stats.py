"""Dashboard summary statistics.

Goes through JobService/ApplicationService, never the database directly
(Part 3 §21).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from flames_shared.enums import ApplicationStatus, JobStatus

from app.api.deps import (
    get_application_service_dep,
    get_current_user,
    get_job_service_dep,
)
from app.schemas.envelope import SuccessResponse
from app.schemas.stats import ApplicationStatusCounts, DashboardStats, JobStatusCounts
from app.services.application_service import ApplicationService
from app.services.job_service import JobService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=SuccessResponse[DashboardStats])
async def get_summary(
    job_service: Annotated[JobService, Depends(get_job_service_dep)],
    application_service: Annotated[ApplicationService, Depends(get_application_service_dep)],
    _: Annotated[str, Depends(get_current_user)],
) -> SuccessResponse[DashboardStats]:
    jobs_by_status = JobStatusCounts(
        new=await job_service.count_by_status(JobStatus.NEW),
        matched=await job_service.count_by_status(JobStatus.MATCHED),
        review=await job_service.count_by_status(JobStatus.REVIEW),
        applied=await job_service.count_by_status(JobStatus.APPLIED),
        failed=await job_service.count_by_status(JobStatus.FAILED),
        skipped=await job_service.count_by_status(JobStatus.SKIPPED),
        expired=await job_service.count_by_status(JobStatus.EXPIRED),
    )
    applications_by_status = ApplicationStatusCounts(
        pending=await application_service.count_by_status(ApplicationStatus.QUEUED),
        running=await application_service.count_by_status(ApplicationStatus.RUNNING),
        success=await application_service.count_by_status(ApplicationStatus.SUCCESS),
        failed=await application_service.count_by_status(ApplicationStatus.FAILED),
        review_required=await application_service.count_by_status(
            ApplicationStatus.REVIEW_REQUIRED
        ),
        cancelled=await application_service.count_by_status(ApplicationStatus.CANCELLED),
    )
    stats = DashboardStats(
        total_jobs_discovered=await job_service.count_jobs(),
        jobs_by_status=jobs_by_status,
        total_applications=await application_service.count_applications(),
        applications_by_status=applications_by_status,
    )
    return SuccessResponse(message="Dashboard stats retrieved successfully.", data=stats)
