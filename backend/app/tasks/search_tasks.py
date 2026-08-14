"""Job search Celery tasks — thin wrapper calling into JobService. Runs
on the `search` queue.
"""

from __future__ import annotations

import asyncio
import logging

from app.database.session import session_scope
from app.scheduler.celery_app import celery_app
from app.scheduler.locking import task_lock
from app.scheduler.pause import is_paused
from app.scheduler.tracking import track_scheduled_task
from app.services.job_service import get_job_service

logger = logging.getLogger(__name__)

_LOCK_TTL_SECONDS = 600


@celery_app.task(name="app.tasks.search_tasks.search_all_providers")
def search_all_providers() -> None:
    logger.info("Job search triggered")
    asyncio.run(_search_all_providers())


@track_scheduled_task("search_all_providers")
async def _search_all_providers() -> None:
    async with task_lock("search_all_providers", ttl_seconds=_LOCK_TTL_SECONDS) as acquired:
        if not acquired:
            logger.info("search_all_providers already running elsewhere; skipping")
            return
        async with session_scope() as db:
            if await is_paused(db):
                logger.info("Operations paused via /pause; skipping search_all_providers")
                return
            job_service = get_job_service(db)
            jobs = await job_service.search_all()
            logger.info("Ingested %d job(s) this search cycle", len(jobs))
