"""CRUD for `Notification`."""

from __future__ import annotations

from app.models.notification import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification
