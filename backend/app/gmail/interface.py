"""Contract for talking to the Gmail API.

Classification is `AIService`'s job (see `app/services/email_service.py`),
not this module's — this only fetches raw messages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class GmailClientInterface(ABC):
    @abstractmethod
    def fetch_messages_since(
        self, after: datetime | None, max_results: int = 50
    ) -> list[dict[str, Any]]:
        """Pull messages received after `after` (or the most recent
        `max_results`, if None). Returns raw Gmail API message resources."""
