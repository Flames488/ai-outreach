"""Contract for delivering a notification.

Telegram is the only channel today, but nothing outside this module
assumes that.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from flames_shared.dto import NotificationPayload


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Deliver a notification. Returns True on success."""
