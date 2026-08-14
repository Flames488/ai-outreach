"""Telegram bot webhook (Phase 2 §16) — called by Telegram, not API
clients. The route does none of the command logic; it validates the
secret header and hands off to the Command Router.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from flames_shared.enums import ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import FlamesAPIError
from app.database.session import get_db
from app.schemas.envelope import SuccessResponse
from app.telegram.router import handle_update

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook", response_model=SuccessResponse[dict])
async def telegram_webhook(
    update: dict[str, Any],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> SuccessResponse[dict]:
    settings = get_settings()
    if (
        not settings.telegram_webhook_secret
        or x_telegram_bot_api_secret_token != settings.telegram_webhook_secret
    ):
        raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "Invalid webhook secret")

    await handle_update(db, update)
    return SuccessResponse(message="Update processed.", data={})
