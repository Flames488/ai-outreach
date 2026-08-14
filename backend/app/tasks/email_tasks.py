"""Email sync Celery tasks — thin wrapper calling into EmailService."""

from __future__ import annotations

import asyncio
import logging

from app.database.session import session_scope
from app.gmail.client import GmailClient
from app.repositories.email_repository import EmailRepository
from app.scheduler.celery_app import celery_app
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.email_tasks.sync_gmail")
def sync_gmail() -> None:
    logger.info("Gmail sync triggered")
    asyncio.run(_sync_gmail())


async def _sync_gmail() -> None:
    async with session_scope() as db:
        email_service = EmailService(repository=EmailRepository(db), client=GmailClient())
        await email_service.sync_inbox()
