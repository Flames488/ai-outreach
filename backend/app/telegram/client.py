"""Telegram Bot API client — outbound sends (notifications + bot replies)
and callback-query acknowledgement.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from flames_shared.constants import HTTP_REQUEST_TIMEOUT_SECONDS
from flames_shared.dto import NotificationPayload

from app.config.settings import get_settings
from app.telegram.interface import NotificationProvider

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramProvider(NotificationProvider):
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None) -> None:
        settings = get_settings()
        self._enabled = settings.enable_telegram
        self._bot_token = bot_token or settings.telegram_bot_token
        self._chat_id = chat_id or settings.telegram_chat_id

    async def send(self, payload: NotificationPayload) -> bool:
        """`NotificationProvider` interface — sends to the single
        configured admin chat (Flames is single-tenant today)."""
        if not self._chat_id:
            return False
        text = f"*{payload.title}*\n{payload.body}"
        reply_markup = None
        action_url = payload.metadata.get("action_url")
        if action_url:
            label = payload.metadata.get("action_label") or "Open"
            reply_markup = {"inline_keyboard": [[{"text": label, "url": action_url}]]}
        return await self.send_message(self._chat_id, text, reply_markup=reply_markup)

    async def send_message(
        self, chat_id: str, text: str, reply_markup: dict[str, Any] | None = None
    ) -> bool:
        if not self._enabled:
            logger.info("Telegram disabled (ENABLE_TELEGRAM=false); dropping message")
            return False
        if not self._bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; dropping message")
            return False

        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        response = await self._post("sendMessage", payload)
        return response is not None

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        await self._post(
            "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text}
        )

    async def set_webhook(self, url: str, secret_token: str) -> bool:
        response = await self._post("setWebhook", {"url": url, "secret_token": secret_token})
        return response is not None

    async def _post(self, method: str, payload: dict[str, Any]) -> httpx.Response | None:
        if not self._bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not configured; dropping %s", method)
            return None

        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/{method}"
        async with httpx.AsyncClient(timeout=HTTP_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)

        if response.status_code != httpx.codes.OK:
            logger.error("Telegram %s failed (%s): %s", method, response.status_code, response.text)
            return None
        return response
