"""Email listing endpoints. Goes through EmailService, never the
database directly (Part 3 §21).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from flames_shared.enums import ErrorCode

from app.api.deps import get_current_user, get_email_service_dep
from app.core.exceptions import FlamesAPIError
from app.models.user import User
from app.schemas.email import EmailRead
from app.schemas.envelope import SuccessResponse
from app.services.email_service import EmailService

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=SuccessResponse[list[EmailRead]])
async def list_emails(
    email_service: Annotated[EmailService, Depends(get_email_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
    offset: int = 0,
) -> SuccessResponse[list[EmailRead]]:
    emails = await email_service.list_emails(limit=limit, offset=offset)
    data = [EmailRead.model_validate(email) for email in emails]
    return SuccessResponse(
        message="Emails retrieved successfully.",
        data=data,
        meta={"limit": limit, "offset": offset, "count": len(data)},
    )


@router.get("/{email_id}", response_model=SuccessResponse[EmailRead])
async def get_email(
    email_id: uuid.UUID,
    email_service: Annotated[EmailService, Depends(get_email_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[EmailRead]:
    email = await email_service.get_email(email_id)
    if email is None:
        raise FlamesAPIError(404, ErrorCode.NOT_FOUND, "Email not found")
    return SuccessResponse(
        message="Email retrieved successfully.", data=EmailRead.model_validate(email)
    )
