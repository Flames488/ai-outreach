"""Login, refresh, logout.

Validates against `users.password_hash` — `scripts/seed.py` creates the
initial ADMIN row. `/auth/login` is rate-limited more aggressively than
the general API limit (Phase 2 §07) to slow down credential stuffing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import enforce_rate_limit
from app.database.session import get_db
from app.schemas.auth import RefreshRequest, TokenPair
from app.schemas.envelope import SuccessResponse
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60


@router.post("/login", response_model=SuccessResponse[TokenPair])
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TokenPair]:
    """Exchange email + password for an access/refresh token pair.
    `form_data.username` holds the email (OAuth2 password flow's field
    name, kept for Swagger UI's built-in "Authorize" button support)."""
    client_ip = request.client.host if request.client else "unknown"
    await enforce_rate_limit(
        key=f"ratelimit:login:{client_ip}",
        max_attempts=LOGIN_RATE_LIMIT_ATTEMPTS,
        window_seconds=LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )

    auth_service: AuthService = get_auth_service(db)
    token_pair = await auth_service.login(email=form_data.username, password=form_data.password)
    return SuccessResponse(message="Logged in successfully.", data=token_pair)


@router.post("/refresh", response_model=SuccessResponse[TokenPair])
async def refresh(
    body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse[TokenPair]:
    """Exchange a valid refresh token for a new access/refresh pair. The
    old refresh token is revoked (single-use) to limit replay risk."""
    auth_service: AuthService = get_auth_service(db)
    token_pair = await auth_service.refresh(body.refresh_token)
    return SuccessResponse(message="Token refreshed successfully.", data=token_pair)


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout(
    body: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> SuccessResponse[dict]:
    """Deletes the refresh token row — invalidates it immediately, no
    waiting for expiry."""
    auth_service: AuthService = get_auth_service(db)
    await auth_service.logout(body.refresh_token)
    return SuccessResponse(message="Logged out successfully.", data={})
