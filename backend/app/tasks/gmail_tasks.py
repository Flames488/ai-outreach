"""Gmail sync/classify Celery tasks — thin wrappers calling into
EmailService. Runs on the `gmail` queue (see `app/scheduler/celery_app.py`).
"""

from __future__ import annotations

import asyncio
import logging

from app.database.session import session_scope
from app.repositories.user_repository import UserRepository
from app.scheduler.celery_app import celery_app
from app.scheduler.locking import task_lock
from app.scheduler.tracking import track_scheduled_task
from app.services.email_service import GmailAuthError, get_email_service

logger = logging.getLogger(__name__)

_LOCK_TTL_SECONDS = 300


@celery_app.task(name="app.tasks.gmail_tasks.sync_gmail")
def sync_gmail() -> None:
    logger.info("Gmail sync triggered")
    asyncio.run(_sync_gmail())


@track_scheduled_task("sync_gmail")
async def _sync_gmail() -> None:
    async with task_lock("sync_gmail", ttl_seconds=_LOCK_TTL_SECONDS) as acquired:
        if not acquired:
            logger.info("sync_gmail already running elsewhere; skipping")
            return
        async with session_scope() as db:
            users = await UserRepository(db).list(gmail_connected=True, limit=100)
            for user in users:
                email_service = get_email_service(db)
                try:
                    new_messages = await email_service.sync_inbox_for_user(user)
                except GmailAuthError:
                    logger.warning(
                        "Gmail sync skipped for %s: not connected/authorized", user.email
                    )
                    continue

                for message in new_messages:
                    classify_email_task.delay(str(message.id))


@celery_app.task(name="app.tasks.gmail_tasks.classify_email_task")
def classify_email_task(email_id: str) -> None:
    logger.info("Email classification triggered for %s", email_id)
    asyncio.run(_classify_email(email_id))


async def _classify_email(email_id: str) -> None:
    import uuid

    async with session_scope() as db:
        email_service = get_email_service(db)
        email = await email_service.get_email(uuid.UUID(email_id))
        if email is None:
            logger.warning("Email %s not found; skipping classification", email_id)
            return
        await email_service.classify_email(email)
