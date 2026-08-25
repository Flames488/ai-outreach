"""API-facing schemas for `application_rules` CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from flames_shared.enums import RuleOperator, RulePriorityTier
from pydantic import BaseModel, ConfigDict


class RuleConditionSchema(BaseModel):
    field: str
    op: RuleOperator
    value: object


class ApplicationRuleCreate(BaseModel):
    name: str
    description: str | None = None
    priority_tier: RulePriorityTier
    condition: RuleConditionSchema
    enabled: bool = True


class ApplicationRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    priority_tier: RulePriorityTier | None = None
    condition: RuleConditionSchema | None = None
    enabled: bool | None = None


class ApplicationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    priority_tier: RulePriorityTier
    condition: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime
