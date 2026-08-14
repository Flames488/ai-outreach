"""CRUD + rule-specific queries for `ApplicationRule`."""

from __future__ import annotations

import uuid

from flames_shared.enums import RulePriorityTier

from app.models.application_rule import ApplicationRule
from app.repositories.base_repository import BaseRepository


class ApplicationRuleRepository(BaseRepository[ApplicationRule]):
    model = ApplicationRule

    async def get_active_rules(
        self, user_id: uuid.UUID, priority_tier: RulePriorityTier | None = None
    ) -> list[ApplicationRule]:
        query = self._base_query().where(
            ApplicationRule.user_id == user_id, ApplicationRule.enabled.is_(True)
        )
        if priority_tier is not None:
            query = query.where(ApplicationRule.priority_tier == priority_tier)
        result = await self.db.execute(query)
        return list(result.scalars().all())
