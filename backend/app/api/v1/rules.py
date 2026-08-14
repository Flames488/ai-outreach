"""CRUD over `application_rules`, scoped to the authenticated user
(Phase 2 §11/§17). Goes through RuleEngineService, never the database
directly.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_rule_engine_service_dep
from app.models.user import User
from app.schemas.envelope import SuccessResponse
from app.schemas.rule import ApplicationRuleCreate, ApplicationRuleRead, ApplicationRuleUpdate
from app.services.rule_engine_service import RuleEngineService

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=SuccessResponse[list[ApplicationRuleRead]])
async def list_rules(
    rules: Annotated[RuleEngineService, Depends(get_rule_engine_service_dep)],
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[list[ApplicationRuleRead]]:
    rule_rows = await rules.list_rules(user.id)
    data = [ApplicationRuleRead.model_validate(rule) for rule in rule_rows]
    return SuccessResponse(message="Rules retrieved successfully.", data=data)


@router.post("", response_model=SuccessResponse[ApplicationRuleRead], status_code=201)
async def create_rule(
    body: ApplicationRuleCreate,
    rules: Annotated[RuleEngineService, Depends(get_rule_engine_service_dep)],
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[ApplicationRuleRead]:
    rule = await rules.create_rule(
        user_id=user.id,
        name=body.name,
        description=body.description,
        priority_tier=body.priority_tier,
        condition=body.condition.model_dump(),
        enabled=body.enabled,
    )
    return SuccessResponse(
        message="Rule created successfully.", data=ApplicationRuleRead.model_validate(rule)
    )


@router.patch("/{rule_id}", response_model=SuccessResponse[ApplicationRuleRead])
async def update_rule(
    rule_id: uuid.UUID,
    body: ApplicationRuleUpdate,
    rules: Annotated[RuleEngineService, Depends(get_rule_engine_service_dep)],
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[ApplicationRuleRead]:
    updates = body.model_dump(exclude_unset=True)
    if "condition" in updates and updates["condition"] is not None:
        updates["condition"] = body.condition.model_dump() if body.condition else None
    rule = await rules.update_rule(rule_id, user.id, **updates)
    return SuccessResponse(
        message="Rule updated successfully.", data=ApplicationRuleRead.model_validate(rule)
    )


@router.delete("/{rule_id}", response_model=SuccessResponse[dict])
async def delete_rule(
    rule_id: uuid.UUID,
    rules: Annotated[RuleEngineService, Depends(get_rule_engine_service_dep)],
    user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    await rules.delete_rule(rule_id, user.id)
    return SuccessResponse(message="Rule deleted successfully.", data={})
