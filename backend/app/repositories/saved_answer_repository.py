"""CRUD for `SavedAnswer`."""

from __future__ import annotations

from app.models.saved_answer import SavedAnswer
from app.repositories.base_repository import BaseRepository


class SavedAnswerRepository(BaseRepository[SavedAnswer]):
    model = SavedAnswer
