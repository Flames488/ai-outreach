"""Gmail OAuth flow (Phase 2 §15)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from flames_shared.enums import ErrorCode

from app.api.deps import get_current_user, get_email_service_dep
from app.core.exceptions import FlamesAPIError
from app.gmail.oauth import build_consent_url, exchange_code_for_credentials
from app.models.user import User
from app.schemas.envelope import SuccessResponse
from app.schemas.gmail import GmailConnectResponse, GmailStatusResponse
from app.services.email_service import EmailService

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/connect", response_model=SuccessResponse[GmailConnectResponse])
async def connect_gmail(
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[GmailConnectResponse]:
    """Builds the Google consent URL — the frontend redirects the user
    there; Google redirects back to `/gmail/callback`."""
    url = build_consent_url()
    return SuccessResponse(
        message="Gmail consent URL generated.", data=GmailConnectResponse(consent_url=url)
    )


@router.get("/callback", response_model=SuccessResponse[dict])
async def gmail_callback(
    code: str,
    email_service: Annotated[EmailService, Depends(get_email_service_dep)],
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """OAuth redirect target — exchanges the authorization code for
    tokens and stores the refresh token encrypted (never the access
    token, which is short-lived and not worth persisting)."""
    try:
        credentials = exchange_code_for_credentials(code)
    except Exception as exc:
        raise FlamesAPIError(
            400, ErrorCode.GMAIL_AUTH_FAILED, f"OAuth exchange failed: {exc}"
        ) from exc

    if not credentials.refresh_token:
        raise FlamesAPIError(
            400,
            ErrorCode.GMAIL_AUTH_FAILED,
            "Google did not return a refresh token — retry with prompt=consent",
        )

    await email_service.connect_gmail(user, credentials.refresh_token)
    return SuccessResponse(message="Gmail connected successfully.", data={})


@router.get("/status", response_model=SuccessResponse[GmailStatusResponse])
async def gmail_status(
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[GmailStatusResponse]:
    return SuccessResponse(
        message="Gmail status retrieved successfully.",
        data=GmailStatusResponse(
            connected=user.gmail_connected, last_synced_at=user.gmail_last_synced_at
        ),
    )
