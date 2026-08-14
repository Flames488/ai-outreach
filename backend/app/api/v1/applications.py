"""Application creation, retry, and audit-trail endpoints. Goes through
ApplicationService, never the database directly (Part 3 §21).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from flames_shared.enums import ApplicationStatus, ErrorCode

from app.api.deps import get_application_service_dep, get_current_user
from app.core.exceptions import FlamesAPIError
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationDetail, ApplicationRead
from app.schemas.envelope import SuccessResponse
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=SuccessResponse[list[ApplicationRead]])
async def list_applications(
    application_service: Annotated[ApplicationService, Depends(get_application_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
    offset: int = 0,
    status: ApplicationStatus | None = None,
) -> SuccessResponse[list[ApplicationRead]]:
    applications = await application_service.list_applications(
        limit=limit, offset=offset, status=status
    )
    data = [ApplicationRead.model_validate(application) for application in applications]
    return SuccessResponse(
        message="Applications retrieved successfully.",
        data=data,
        meta={"limit": limit, "offset": offset, "count": len(data)},
    )


@router.post("", response_model=SuccessResponse[ApplicationRead], status_code=201)
async def create_application(
    body: ApplicationCreate,
    application_service: Annotated[ApplicationService, Depends(get_application_service_dep)],
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[ApplicationRead]:
    """Queues a job for application, subject to duplicate protection and
    `application_rules` evaluation (Phase 2 §10) — never applies directly;
    Playwright submission is a later phase."""
    application = await application_service.create_application(body.job_id, user.id)
    return SuccessResponse(
        message="Application created successfully.",
        data=ApplicationRead.model_validate(application),
    )


@router.get("/{application_id}", response_model=SuccessResponse[ApplicationDetail])
async def get_application(
    application_id: uuid.UUID,
    application_service: Annotated[ApplicationService, Depends(get_application_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[ApplicationDetail]:
    application = await application_service.get_application(application_id)
    if application is None:
        raise FlamesAPIError(404, ErrorCode.NOT_FOUND, "Application not found")
    timeline = await application_service.get_timeline(application_id)
    detail = ApplicationDetail(
        **ApplicationRead.model_validate(application).model_dump(),
        timeline=[
            {
                "action": entry.action,
                "old_value": entry.old_value,
                "new_value": entry.new_value,
                "created_at": entry.created_at,
            }
            for entry in timeline
        ],
    )
    return SuccessResponse(message="Application retrieved successfully.", data=detail)


@router.post("/{application_id}/retry", response_model=SuccessResponse[ApplicationRead])
async def retry_application(
    application_id: uuid.UUID,
    application_service: Annotated[ApplicationService, Depends(get_application_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[ApplicationRead]:
    application = await application_service.retry_application(application_id)
    return SuccessResponse(
        message="Application re-queued for retry.",
        data=ApplicationRead.model_validate(application),
    )
