"""Safe evaluation of a single `RuleCondition` against a context dict —
never `eval()`. Phase 2 §17.
"""

from __future__ import annotations

from typing import Any

from flames_shared.enums import RuleOperator

from app.rules.schema import RuleCondition

_OPERATORS: dict[RuleOperator, Any] = {
    RuleOperator.EQ: lambda actual, expected: actual == expected,
    RuleOperator.NE: lambda actual, expected: actual != expected,
    RuleOperator.GTE: lambda actual, expected: actual is not None and actual >= expected,
    RuleOperator.LTE: lambda actual, expected: actual is not None and actual <= expected,
    RuleOperator.GT: lambda actual, expected: actual is not None and actual > expected,
    RuleOperator.LT: lambda actual, expected: actual is not None and actual < expected,
    RuleOperator.IN: lambda actual, expected: actual in expected,
    RuleOperator.NOT_IN: lambda actual, expected: actual not in expected,
    RuleOperator.CONTAINS: lambda actual, expected: expected in (actual or []),
}


def matches(condition: RuleCondition, context: dict[str, object]) -> bool:
    actual = context.get(condition.field)
    comparator = _OPERATORS[condition.op]
    try:
        return bool(comparator(actual, condition.value))
    except TypeError:
        # Mismatched types (e.g. comparing None against >=) never match —
        # they don't raise and abort the rest of the evaluation.
        return False
