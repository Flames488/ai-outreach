"""Telegram Bot API calls are mocked at the HTTP boundary — never a real
call in the automated suite."""

from __future__ import annotations

import json

import httpx
import respx
from app.telegram.client import TELEGRAM_API_BASE, TelegramProvider
from flames_shared.dto import NotificationPayload


def _provider() -> TelegramProvider:
    return TelegramProvider(bot_token="test-token", chat_id="12345")


@respx.mock
async def test_send_without_action_url_omits_reply_markup() -> None:
    route = respx.post(f"{TELEGRAM_API_BASE}/bottest-token/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    sent = await _provider().send(NotificationPayload(title="Hi", body="Hello there"))

    assert sent is True
    assert "reply_markup" not in route.calls.last.request.content.decode()


@respx.mock
async def test_send_with_action_url_adds_url_button() -> None:
    route = respx.post(f"{TELEGRAM_API_BASE}/bottest-token/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    sent = await _provider().send(
        NotificationPayload(
            title="Application ready to review",
            body="Backend Engineer at Acme",
            metadata={
                "action_url": "https://job-boards.greenhouse.io/acme/jobs/1",
                "action_label": "Open application",
            },
        )
    )

    assert sent is True
    payload = json.loads(route.calls.last.request.content)
    assert payload["reply_markup"] == {
        "inline_keyboard": [
            [
                {
                    "text": "Open application",
                    "url": "https://job-boards.greenhouse.io/acme/jobs/1",
                }
            ]
        ]
    }
