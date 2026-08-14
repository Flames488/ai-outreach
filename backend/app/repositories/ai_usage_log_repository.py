"""CRUD for `AIUsageLog` (Part 6 §73)."""

from __future__ import annotations

from app.models.ai_usage_log import AIUsageLog
from app.repositories.base_repository import BaseRepository


class AIUsageLogRepository(BaseRepository[AIUsageLog]):
    model = AIUsageLog
