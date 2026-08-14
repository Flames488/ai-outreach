"""Condition schema for `application_rules.condition` (JSONB) — Phase 2
§17. A minimal, safely-evaluable structure. Never `eval()` a string
expression. Validated against this schema (and the field allowlist) at
write time in `RuleEngineService`, never at evaluation time.
"""

from __future__ import annotations

from flames_shared.enums import RuleOperator, RulePriorityTier
from pydantic import BaseModel, field_validator

# The only context keys a condition may reference — anything else is
# rejected when the rule is created/updated, per §17's "reject any
# condition referencing a field not on the allowlist at write time".
ALLOWED_CONDITION_FIELDS = frozenset(
    {
        "ai_score",
        "remote",
        "country",
        "city",
        "salary_min",
        "salary_max",
        "employment_type",
        "experience_level",
        "provider",
        "applications_today",
        "skills",
    }
)


class RuleCondition(BaseModel):
    field: str
    op: RuleOperator
    value: object

    @field_validator("field")
    @classmethod
    def _field_must_be_allowlisted(cls, value: str) -> str:
        if value not in ALLOWED_CONDITION_FIELDS:
            raise ValueError(
                f"'{value}' is not an evaluatable field. Allowed: "
                f"{sorted(ALLOWED_CONDITION_FIELDS)}"
            )
        return value


class RuleDecision(BaseModel):
    approved: bool
    blocking_rule_id: str | None = None
    blocking_rule_name: str | None = None
    tier: RulePriorityTier | None = None
    preference_score: int = 0
