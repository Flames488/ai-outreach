"""AI scoring Celery tasks — thin wrapper calling into AIService /
RuleEngineService. Runs on the `ai` queue.
"""

from __future__ import annotations

import asyncio
import logging

from flames_shared.dto import JobPosting
from flames_shared.enums import JobSourceType, JobStatus

from app.config.settings import get_settings
from app.database.session import session_scope
from app.models.user_profile import UserProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.user_repository import UserRepository
from app.scheduler.celery_app import celery_app
from app.scheduler.pause import is_paused
from app.scheduler.tracking import track_scheduled_task
from app.services.ai_service import get_ai_service
from app.services.rule_engine_service import get_rule_engine_service

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.ai_tasks.score_pending_jobs")
def score_pending_jobs() -> None:
    logger.info("Job scoring triggered")
    asyncio.run(_score_pending_jobs())


@track_scheduled_task("score_pending_jobs")
async def _score_pending_jobs() -> None:
    settings = get_settings()

    async with session_scope() as db:
        if await is_paused(db):
            logger.info("Operations paused via /pause; skipping score_pending_jobs")
            return

        jobs_repo = JobRepository(db)
        companies_repo = CompanyRepository(db)
        users_repo = UserRepository(db)
        profiles_repo = UserProfileRepository(db)
        ai_service = get_ai_service(db)
        rule_engine = get_rule_engine_service(db)

        # score_match calls used to fire back-to-back with no pacing, so
        # anything past the first ~25 of a 100-job batch hit AI_RATE_LIMIT_
        # PER_MINUTE's "Max 25 requests per 60s" and got kicked back to NEW
        # every single cycle, forever. A smaller batch, paced below to stay
        # under that budget, keeps every job in it within budget instead of
        # discarding most of it on arrival.
        pending_jobs = await jobs_repo.list(status=JobStatus.NEW, limit=60)
        if not pending_jobs:
            return

        users = await users_repo.list(limit=10)
        if not users:
            logger.warning("No users to score jobs against; skipping")
            return
        user = users[0]  # Flames is single-tenant this phase

        profile = await profiles_repo.get_by_user_id(user.id)
        cv_profile = _profile_to_dict(profile)

        # Spread calls out so the batch stays under the shared
        # ratelimit:ai:<provider> budget instead of bursting into it.
        pace_seconds = 60 / settings.ai_rate_limit_per_minute

        for index, job in enumerate(pending_jobs):
            if index > 0:
                await asyncio.sleep(pace_seconds)

            company = await companies_repo.get(job.company_id) if job.company_id else None
            posting = JobPosting(
                source=JobSourceType.OTHER,
                external_id=job.external_job_id,
                title=job.title,
                company=company.company_name if company else "Unknown",
                url=job.application_url,
                description=job.description,
            )

            try:
                match = await ai_service.score_match(posting, cv_profile)
            except Exception:
                logger.exception("Scoring failed for job %s; leaving as NEW for retry", job.id)
                continue

            job.ai_score = float(match.score)
            decision = await rule_engine.evaluate(job, user.id)
            if not decision.approved:
                job.status = JobStatus.SKIPPED
            elif match.score >= settings.job_match_threshold:
                job.status = JobStatus.MATCHED
            else:
                job.status = JobStatus.REVIEW
            await db.commit()


def _profile_to_dict(profile: UserProfile | None) -> dict[str, object]:
    if profile is None:
        return {}
    return {
        "full_name": profile.full_name,
        "professional_summary": profile.professional_summary,
        "desired_titles": profile.desired_titles,
        "skills": profile.skills,
        "years_of_experience": profile.years_of_experience,
        "current_position": profile.current_position,
        "notable_projects": profile.notable_projects,
        "education": profile.education,
        "certifications": profile.certifications,
        "languages": profile.languages,
        "work_authorization": profile.work_authorization,
    }
