"""Gmail OAuth flow (Phase 2 §15)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from flames_shared.enums import ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_email_service_dep
from app.auth.security import create_access_token, decode_access_token
from app.config.settings import get_settings
from app.core.exceptions import FlamesAPIError
from app.database.session import get_db
from app.gmail.oauth import build_consent_url, exchange_code_for_credentials
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.envelope import SuccessResponse
from app.schemas.gmail import GmailConnectResponse, GmailStatusResponse
from app.services.email_service import EmailService

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/connect", response_model=SuccessResponse[GmailConnectResponse])
async def connect_gmail(
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[GmailConnectResponse]:
    """Builds the Google consent URL — the frontend redirects the user
    there; Google redirects back to `/gmail/callback`. The current user's
    identity travels via `state`, not a header — see build_consent_url's
    docstring for why."""
    url = build_consent_url(state=create_access_token(str(user.id), user.role))
    return SuccessResponse(
        message="Gmail consent URL generated.", data=GmailConnectResponse(consent_url=url)
    )


async def _user_from_state(state: str, db: AsyncSession) -> User:
    payload = decode_access_token(state)
    user_id = payload.get("sub") if payload else None
    if not isinstance(user_id, str):
        raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "Invalid or expired state")
    user = await UserRepository(db).get(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "Invalid or expired state")
    return user


@router.get("/callback", response_model=None)
async def gmail_callback(
    code: str,
    state: str,
    email_service: Annotated[EmailService, Depends(get_email_service_dep)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[dict] | RedirectResponse:
    """OAuth redirect target — exchanges the authorization code for
    tokens and stores the refresh token encrypted (never the access
    token, which is short-lived and not worth persisting). Google makes
    this request as a plain browser redirect, so it can't carry an
    Authorization header — `state` (round-tripped unchanged through
    Google) identifies the user instead, not `get_current_user`.

    On success, sends the browser back to the dashboard (FRONTEND_URL)
    instead of leaving it stranded on this endpoint's raw JSON — that
    URL is optional config, so this degrades to returning JSON directly
    if it's unset rather than guessing a wrong redirect target."""
    user = await _user_from_state(state, db)
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

    frontend_url = get_settings().frontend_url
    if frontend_url:
        return RedirectResponse(f"{frontend_url.rstrip('/')}/settings?gmail=connected")
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
