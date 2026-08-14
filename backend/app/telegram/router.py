"""Command Router (Phase 2 §16). `POST /api/v1/telegram/webhook`
(`app/api/v1/telegram.py`) does none of the command logic — it validates
the secret header, parses the update, and hands off to
`handle_update()` here.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import enforce_rate_limit
from app.telegram.auth import get_telegram_user
from app.telegram.client import TelegramProvider
from app.telegram.handlers import (
    dispatch_command,
    dispatch_freeform_message,
    handle_job_review_callback,
)

logger = logging.getLogger(__name__)

COMMAND_RATE_LIMIT = 30
COMMAND_RATE_LIMIT_WINDOW_SECONDS = 60


async def handle_update(db: AsyncSession, update: dict[str, Any]) -> None:
    provider = TelegramProvider()

    if "callback_query" in update:
        await _handle_callback_query(db, provider, update["callback_query"])
        return

    message = update.get("message")
    if not message or "text" not in message:
        return

    chat_id = str(message["chat"]["id"])
    text = message["text"].strip()
    if not text:
        return

    try:
        await enforce_rate_limit(
            key=f"ratelimit:telegram:{chat_id}",
            max_attempts=COMMAND_RATE_LIMIT,
            window_seconds=COMMAND_RATE_LIMIT_WINDOW_SECONDS,
        )
    except Exception:
        await provider.send_message(chat_id, "Too many messages. Please slow down.")
        return

    user = await get_telegram_user(db, chat_id)
    if user is None:
        await provider.send_message(chat_id, "Access denied. This chat is not authorized.")
        return

    if text.startswith("/"):
        parts = text[1:].split()
        command = parts[0].lower()
        args = parts[1:]
        results = await dispatch_command(db, user, command, args)
    else:
        # Free-text (Phase 5): routed through the AI assistant rather than
        # the fixed command dispatcher.
        results = await dispatch_freeform_message(db, user, text)

    for response_text, reply_markup in results:
        await provider.send_message(chat_id, response_text, reply_markup=reply_markup)


async def _handle_callback_query(
    db: AsyncSession, provider: TelegramProvider, callback_query: dict[str, Any]
) -> None:
    callback_id = callback_query["id"]
    chat_id = str(callback_query["message"]["chat"]["id"])
    data = callback_query.get("data", "")

    user = await get_telegram_user(db, chat_id)
    if user is None:
        await provider.answer_callback_query(callback_id, "Access denied.")
        return

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "job":
        await provider.answer_callback_query(callback_id)
        return

    _, action, job_id = parts
    response_text = await handle_job_review_callback(db, user, action, job_id)
    await provider.answer_callback_query(callback_id, response_text[:200])
    await provider.send_message(chat_id, response_text)
