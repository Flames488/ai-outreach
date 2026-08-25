"""Gmail API client — fetches messages, nothing else. Sync/dedup
orchestration lives in `app/services/email_service.py`; classification in
`app/services/ai_service.py`.

`googleapiclient` is a synchronous library. Calls here block, which is
fine inside a Celery task (a dedicated worker process, not a shared event
loop serving concurrent requests) — callers just shouldn't invoke this
from a FastAPI route body.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config.settings import get_settings
from app.gmail.interface import GmailClientInterface


class GmailClient(GmailClientInterface):
    def __init__(self, refresh_token: str) -> None:
        settings = get_settings()
        credentials = Credentials(  # type: ignore[no-untyped-call]
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def fetch_messages_since(
        self, after: datetime | None, max_results: int = 50
    ) -> list[dict[str, Any]]:
        query = f"after:{int(after.timestamp())}" if after else ""
        response = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        stubs = response.get("messages", [])

        messages: list[dict[str, Any]] = []
        for stub in stubs:
            full = (
                self._service.users()
                .messages()
                .get(userId="me", id=stub["id"], format="full")
                .execute()
            )
            messages.append(full)
        return messages
