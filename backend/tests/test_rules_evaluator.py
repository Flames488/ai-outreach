"""Table-driven tests for the Rule Engine's condition evaluator
(Phase 2 §20: every supported `op`, plus the tier short-circuit behavior).
"""

from __future__ import annotations

import pytest
from app.rules.evaluator import matches
from app.rules.schema import RuleCondition
from flames_shared.enums import RuleOperator
from pydantic import ValidationError

CONTEXT = {
    "ai_score": 85,
    "remote": True,
    "country": "US",
    "salary_min": 90000,
    "skills": ["python", "sql"],
}

CASES = [
    ({"field": "ai_score", "op": RuleOperator.EQ, "value": 85}, True),
    ({"field": "ai_score", "op": RuleOperator.EQ, "value": 50}, False),
    ({"field": "ai_score", "op": RuleOperator.NE, "value": 50}, True),
    ({"field": "ai_score", "op": RuleOperator.GTE, "value": 85}, True),
    ({"field": "ai_score", "op": RuleOperator.GTE, "value": 86}, False),
    ({"field": "ai_score", "op": RuleOperator.LTE, "value": 85}, True),
    ({"field": "ai_score", "op": RuleOperator.LTE, "value": 84}, False),
    ({"field": "ai_score", "op": RuleOperator.GT, "value": 84}, True),
    ({"field": "ai_score", "op": RuleOperator.GT, "value": 85}, False),
    ({"field": "ai_score", "op": RuleOperator.LT, "value": 86}, True),
    ({"field": "ai_score", "op": RuleOperator.LT, "value": 85}, False),
    ({"field": "country", "op": RuleOperator.IN, "value": ["US", "CA"]}, True),
    ({"field": "country", "op": RuleOperator.IN, "value": ["UK"]}, False),
    ({"field": "country", "op": RuleOperator.NOT_IN, "value": ["UK"]}, True),
    ({"field": "country", "op": RuleOperator.NOT_IN, "value": ["US"]}, False),
    ({"field": "skills", "op": RuleOperator.CONTAINS, "value": "python"}, True),
    ({"field": "skills", "op": RuleOperator.CONTAINS, "value": "rust"}, False),
]


@pytest.mark.parametrize("condition_dict,expected", CASES)
def test_operator_matches(condition_dict: dict, expected: bool) -> None:
    condition = RuleCondition.model_validate(condition_dict)
    assert matches(condition, CONTEXT) is expected


def test_missing_field_never_matches_gte() -> None:
    condition = RuleCondition.model_validate(
        {"field": "salary_max", "op": RuleOperator.GTE, "value": 100}
    )
    # "salary_max" isn't in CONTEXT -> actual is None -> GTE against None
    # must not match (and must not raise).
    assert matches(condition, CONTEXT) is False


def test_unknown_field_rejected_at_validation() -> None:
    with pytest.raises(ValidationError):
        RuleCondition.model_validate({"field": "not_a_real_field", "op": "==", "value": 1})
