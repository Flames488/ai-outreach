"""Evaluates `application_rules` against a job for a user — Critical ->
Required -> Preference (Phase 2 §17). Critical/Required are pass/fail
gates; the first failure short-circuits and is what gets logged to
`audit_logs`. Preference rules never block, they only rank.

Same context shape whether called from job-scoring (search-time) or
pre-submission (a later phase's Application Engine) — one `_build_context`,
two call sites, per §17's two-call-site design.
"""

from __future__ import annotations

import uuid

from flames_shared.enums import ErrorCode, RulePriorityTier
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FlamesAPIError
from app.models.application_rule import ApplicationRule
from app.models.job import Job
from app.repositories.application_repository import ApplicationRepository
from app.repositories.application_rule_repository import ApplicationRuleRepository
from app.repositories.job_skill_repository import JobSkillRepository
from app.rules.evaluator import matches
from app.rules.schema import RuleCondition, RuleDecision
from app.services.audit_service import AuditService, get_audit_service


class RuleEngineService:
    def __init__(
        self,
        db: AsyncSession,
        rules: ApplicationRuleRepository,
        applications: ApplicationRepository,
        job_skills: JobSkillRepository,
        audit: AuditService,
    ) -> None:
        self._db = db
        self._rules = rules
        self._applications = applications
        self._job_skills = job_skills
        self._audit = audit

    async def list_rules(self, user_id: uuid.UUID) -> list[ApplicationRule]:
        return await self._rules.list(user_id=user_id, limit=200)

    async def create_rule(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
        priority_tier: RulePriorityTier,
        condition: dict[str, object],
        enabled: bool,
    ) -> ApplicationRule:
        self._validate_condition(condition)
        rule = await self._rules.create(
            user_id=user_id,
            name=name,
            description=description,
            priority_tier=priority_tier,
            condition=condition,
            enabled=enabled,
        )
        await self._db.commit()
        return rule

    async def update_rule(
        self, rule_id: uuid.UUID, user_id: uuid.UUID, **updates: object
    ) -> ApplicationRule:
        rule = await self._rules.get(rule_id)
        if rule is None or rule.user_id != user_id:
            raise FlamesAPIError(404, ErrorCode.NOT_FOUND, "Rule not found")
        if "condition" in updates and updates["condition"] is not None:
            self._validate_condition(updates["condition"])  # type: ignore[arg-type]
        updated = await self._rules.update(
            rule_id, **{key: value for key, value in updates.items() if value is not None}
        )
        await self._db.commit()
        assert updated is not None
        return updated

    async def delete_rule(self, rule_id: uuid.UUID, user_id: uuid.UUID) -> None:
        rule = await self._rules.get(rule_id)
        if rule is None or rule.user_id != user_id:
            raise FlamesAPIError(404, ErrorCode.NOT_FOUND, "Rule not found")
        await self._db.delete(rule)
        await self._db.commit()

    @staticmethod
    def _validate_condition(condition: dict[str, object]) -> None:
        """Rejects a condition referencing a field/op not on the allowlist
        at write time — never at evaluation time (Phase 2 §17)."""
        try:
            RuleCondition.model_validate(condition)
        except Exception as exc:
            raise FlamesAPIError(
                422, ErrorCode.VALIDATION_ERROR, f"Invalid rule condition: {exc}"
            ) from exc

    async def evaluate(self, job: Job, user_id: uuid.UUID) -> RuleDecision:
        rules = await self._rules.get_active_rules(user_id)
        context = await self._build_context(job, user_id)

        for tier in (RulePriorityTier.CRITICAL, RulePriorityTier.REQUIRED):
            for rule in _rules_in_tier(rules, tier):
                condition = RuleCondition.model_validate(rule.condition)
                if not matches(condition, context):
                    await self._audit.log(
                        entity="job",
                        entity_id=job.id,
                        action="rule_blocked",
                        new_value={
                            "rule_id": str(rule.id),
                            "rule_name": rule.name,
                            "tier": tier.value,
                        },
                        performed_by=str(user_id),
                    )
                    return RuleDecision(
                        approved=False,
                        blocking_rule_id=str(rule.id),
                        blocking_rule_name=rule.name,
                        tier=tier,
                    )

        preference_score = sum(
            1
            for rule in _rules_in_tier(rules, RulePriorityTier.PREFERENCE)
            if matches(RuleCondition.model_validate(rule.condition), context)
        )
        return RuleDecision(approved=True, preference_score=preference_score)

    async def _build_context(self, job: Job, user_id: uuid.UUID) -> dict[str, object]:
        applications_today = await self._applications.count_today_for_user(user_id)
        skills = await self._job_skills.list_for_job(job.id)
        return {
            "ai_score": job.ai_score,
            "remote": job.remote,
            "country": job.country,
            "city": job.city,
            "salary_min": float(job.salary_min) if job.salary_min is not None else None,
            "salary_max": float(job.salary_max) if job.salary_max is not None else None,
            "employment_type": job.employment_type,
            "experience_level": job.experience_level,
            "provider": job.provider,
            "applications_today": applications_today,
            "skills": [skill.skill_name for skill in skills],
            "client_total_spend": (
                float(job.client_total_spend) if job.client_total_spend is not None else None
            ),
            "client_rating": job.client_rating,
            "client_payment_verified": job.client_payment_verified,
        }


def _rules_in_tier(rules: list[ApplicationRule], tier: RulePriorityTier) -> list[ApplicationRule]:
    return [rule for rule in rules if rule.priority_tier == tier]


def get_rule_engine_service(db: AsyncSession) -> RuleEngineService:
    return RuleEngineService(
        db=db,
        rules=ApplicationRuleRepository(db),
        applications=ApplicationRepository(db),
        job_skills=JobSkillRepository(db),
        audit=get_audit_service(db),
    )
