"""RuleEngineService with fake repositories (Phase 2 §10/§20 — this is
exactly what the repository/service split enables: no DB, no network).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from app.services.rule_engine_service import RuleEngineService
from flames_shared.enums import RuleOperator, RulePriorityTier


def _rule(priority_tier: RulePriorityTier, field: str, op: RuleOperator, value: object, name: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        priority_tier=priority_tier,
        condition={"field": field, "op": op.value, "value": value},
        enabled=True,
    )


class FakeRuleRepository:
    def __init__(self, rules: list) -> None:
        self._rules = rules

    async def get_active_rules(self, user_id: uuid.UUID) -> list:
        return self._rules


class FakeApplicationRepository:
    async def count_today_for_user(self, user_id: uuid.UUID) -> int:
        return 0


class FakeJobSkillRepository:
    async def list_for_job(self, job_id: uuid.UUID) -> list:
        return []


class FakeAuditService:
    def __init__(self) -> None:
        self.logged: list[dict] = []

    async def log(self, **kwargs: object) -> None:
        self.logged.append(kwargs)


def _job(**overrides: object):
    defaults = dict(
        id=uuid.uuid4(),
        ai_score=90,
        remote=True,
        country="US",
        city=None,
        salary_min=None,
        salary_max=None,
        employment_type=None,
        experience_level=None,
        provider="remoteok",
        client_total_spend=None,
        client_rating=None,
        client_payment_verified=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def audit() -> FakeAuditService:
    return FakeAuditService()


async def test_critical_failure_short_circuits_before_required(audit: FakeAuditService) -> None:
    rules = [
        _rule(RulePriorityTier.CRITICAL, "remote", RuleOperator.EQ, False, "must be remote"),
        _rule(RulePriorityTier.REQUIRED, "ai_score", RuleOperator.GTE, 80, "min score"),
    ]
    service = RuleEngineService(
        db=None,  # type: ignore[arg-type]
        rules=FakeRuleRepository(rules),
        applications=FakeApplicationRepository(),
        job_skills=FakeJobSkillRepository(),
        audit=audit,
    )

    decision = await service.evaluate(_job(remote=True), uuid.uuid4())

    assert decision.approved is False
    assert decision.tier == RulePriorityTier.CRITICAL
    assert decision.blocking_rule_name == "must be remote"
    assert len(audit.logged) == 1


async def test_all_gates_pass_scores_preferences(audit: FakeAuditService) -> None:
    rules = [
        _rule(RulePriorityTier.CRITICAL, "remote", RuleOperator.EQ, True, "must be remote"),
        _rule(RulePriorityTier.REQUIRED, "ai_score", RuleOperator.GTE, 80, "min score"),
        _rule(RulePriorityTier.PREFERENCE, "country", RuleOperator.EQ, "US", "prefer US"),
        _rule(RulePriorityTier.PREFERENCE, "country", RuleOperator.EQ, "CA", "prefer CA"),
    ]
    service = RuleEngineService(
        db=None,  # type: ignore[arg-type]
        rules=FakeRuleRepository(rules),
        applications=FakeApplicationRepository(),
        job_skills=FakeJobSkillRepository(),
        audit=audit,
    )

    decision = await service.evaluate(_job(country="US"), uuid.uuid4())

    assert decision.approved is True
    assert decision.preference_score == 1
    assert audit.logged == []
