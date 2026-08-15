"""Playwright application-preparation task (Phase 3 completion). Runs on
the `default` queue — pre-routed for this in `celery_app.py` since before
this phase existed.

Enqueued per-application (never a periodic sweep) right after an
`Application` is created or re-queued, from `ApplicationService`. Gated
behind the `enable_playwright` feature flag and the same `/pause` flag
`search_tasks`/`ai_tasks` check.

This only ever drives `PlaywrightDryRunService` — the dry-run path that
fills a form, reaches the submit control, and stops (Part 3's "never
click submit" rule). Real submission (`ApplicationRunnerInterface.apply`)
stays `NotImplementedError`; nothing here calls it. A successful run
lands the application in `PENDING_VERIFICATION` — ready for a human to
review the filled form and submit it themselves, not auto-submitted.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from flames_shared.enums import ApplicationStatus, NotificationLevel

from app.database.session import session_scope
from app.playwright.browser_engine import PlaywrightTransientError
from app.repositories.application_repository import ApplicationRepository
from app.repositories.cv_version_repository import CVVersionRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.user_repository import UserRepository
from app.scheduler.celery_app import celery_app
from app.scheduler.pause import is_paused
from app.services.feature_flag_service import get_feature_flag_service
from app.services.notification_service import get_notification_service
from app.services.playwright_dry_run_service import get_playwright_dry_run_service

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.application_tasks.apply_to_job",
    # Transient failures (e.g. the browser host is temporarily
    # unavailable) are worth a Celery-level retry. A selector/logic
    # failure never raises PlaywrightTransientError — PlaywrightDryRunService
    # always returns a FAILED ApplicationRecord for those instead.
    autoretry_for=(PlaywrightTransientError,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 2},
)
def apply_to_job(application_id: str) -> None:
    logger.info("Playwright application prep triggered for %s", application_id)
    asyncio.run(_apply_to_job(application_id))


async def _apply_to_job(application_id: str) -> None:
    async with session_scope() as db:
        if await is_paused(db):
            logger.info("Operations paused via /pause; skipping application %s", application_id)
            return

        flags = await get_feature_flag_service(db).get_all()
        if not flags["enable_playwright"]:
            logger.info("Playwright automation disabled; skipping application %s", application_id)
            return

        applications = ApplicationRepository(db)
        application = await applications.get(uuid.UUID(application_id))
        if application is None:
            logger.warning("Application %s no longer exists; skipping", application_id)
            return
        if application.application_status != ApplicationStatus.QUEUED:
            # Already processed (or moved on) since this was enqueued —
            # avoid re-running a stale/duplicate task.
            logger.info(
                "Application %s is %s, not QUEUED; skipping",
                application_id,
                application.application_status.value,
            )
            return

        job = await JobRepository(db).get(application.job_id)
        if job is None:
            application.application_status = ApplicationStatus.FAILED
            application.error_message = "Job no longer exists."
            await db.commit()
            return

        cv = await CVVersionRepository(db).get_default()
        if cv is None:
            application.application_status = ApplicationStatus.REVIEW_REQUIRED
            application.error_message = "No default CV on file — upload one before auto-applying."
            await db.commit()
            return

        user = await UserRepository(db).get(application.user_id)
        profile = (
            await UserProfileRepository(db).get_by_user_id(application.user_id) if user else None
        )

        first_name = (user.first_name if user else None) or _first_name_of(profile)
        last_name = (user.last_name if user else None) or _last_name_of(profile)
        if not first_name or not last_name or user is None:
            application.application_status = ApplicationStatus.REVIEW_REQUIRED
            application.error_message = (
                "Profile is missing a name — complete it before auto-applying."
            )
            await db.commit()
            return

        record = await get_playwright_dry_run_service(db).run(
            url=job.application_url,
            job_fingerprint=f"{job.provider}:{job.external_job_id}",
            first_name=first_name,
            last_name=last_name,
            email=user.email,
            phone=(profile.phone if profile else None) or "",
            cv_path=cv.storage_path,
        )

        application.application_status = record.status
        application.error_message = record.reason
        application.cv_version_id = cv.id
        await db.commit()

        if record.status == ApplicationStatus.PENDING_VERIFICATION:
            await get_notification_service(db).notify(
                title="Application ready to review",
                body=f"{job.title}\n\nFilled and ready — open it to review and submit.",
                level=NotificationLevel.SUCCESS,
                user_id=application.user_id,
                notification_type="application_ready_for_review",
                action_url=job.application_url,
                action_label="Open application",
            )
        logger.info(
            "Application %s -> %s (%s)",
            application_id,
            record.status.value,
            record.method,
        )


def _full_name_of(profile: object) -> str | None:
    full_name = getattr(profile, "full_name", None)
    return full_name if isinstance(full_name, str) and full_name else None


def _first_name_of(profile: object) -> str | None:
    full_name = _full_name_of(profile)
    return full_name.split()[0] if full_name else None


def _last_name_of(profile: object) -> str | None:
    full_name = _full_name_of(profile)
    if not full_name:
        return None
    parts = full_name.split()
    return " ".join(parts[1:]) if len(parts) > 1 else None
