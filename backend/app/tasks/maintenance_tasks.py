"""Cleanup / DB maintenance / application-retry Celery tasks. Run on the
`default` queue.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from flames_shared.enums import ApplicationStatus
from sqlalchemy import func, select

from app.database.session import session_scope
from app.models.job import Job
from app.repositories.application_repository import ApplicationRepository
from app.repositories.provider_log_repository import ProviderLogRepository
from app.repositories.scheduled_task_repository import ScheduledTaskRepository
from app.repositories.system_log_repository import SystemLogRepository
from app.repositories.task_log_repository import TaskLogRepository
from app.scheduler.celery_app import celery_app
from app.scheduler.tracking import track_scheduled_task

logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS = 90
SCHEDULED_TASK_ARCHIVE_DAYS = 30
MAX_APPLICATION_RETRIES = 3


@celery_app.task(name="app.tasks.maintenance_tasks.retry_recoverable_failures")
def retry_recoverable_failures() -> None:
    logger.info("Retry recoverable failures triggered")
    asyncio.run(_retry_recoverable_failures())


@track_scheduled_task("retry_recoverable_failures")
async def _retry_recoverable_failures() -> None:
    async with session_scope() as db:
        applications = ApplicationRepository(db)
        failed = await applications.list(application_status=ApplicationStatus.FAILED, limit=200)
        retried = 0
        for application in failed:
            if application.retry_count >= MAX_APPLICATION_RETRIES:
                continue
            application.application_status = ApplicationStatus.QUEUED
            application.retry_count += 1
            retried += 1
        await db.commit()
        logger.info("Re-queued %d recoverable application(s)", retried)


@celery_app.task(name="app.tasks.maintenance_tasks.cleanup_old_logs")
def cleanup_old_logs() -> None:
    logger.info("Log cleanup triggered")
    asyncio.run(_cleanup_old_logs())


@track_scheduled_task("cleanup_old_logs")
async def _cleanup_old_logs() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=LOG_RETENTION_DAYS)
    async with session_scope() as db:
        # audit_logs is deliberately excluded — insert-only, retained
        # indefinitely (Part 4 §48).
        system_deleted = await SystemLogRepository(db).delete_older_than(cutoff)
        task_deleted = await TaskLogRepository(db).delete_older_than(cutoff)
        provider_deleted = await ProviderLogRepository(db).delete_older_than(cutoff)
        await db.commit()
        logger.info(
            "Pruned logs older than %s: %d system, %d task, %d provider",
            cutoff.date(),
            system_deleted,
            task_deleted,
            provider_deleted,
        )


@celery_app.task(name="app.tasks.maintenance_tasks.archive_completed_tasks")
def archive_completed_tasks() -> None:
    logger.info("Scheduled-task archiving triggered")
    asyncio.run(_archive_completed_tasks())


@track_scheduled_task("archive_completed_tasks")
async def _archive_completed_tasks() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=SCHEDULED_TASK_ARCHIVE_DAYS)
    async with session_scope() as db:
        archived = await ScheduledTaskRepository(db).archive_completed_older_than(cutoff)
        await db.commit()
        logger.info("Archived %d completed scheduled task run(s)", archived)


@celery_app.task(name="app.tasks.maintenance_tasks.db_maintenance")
def db_maintenance() -> None:
    logger.info("DB maintenance check triggered")
    asyncio.run(_db_maintenance())


@track_scheduled_task("db_maintenance")
async def _db_maintenance() -> None:
    """A lightweight health check, not a raw VACUUM/ANALYZE — Postgres
    autovacuum handles routine maintenance in production; running VACUUM
    manually needs an autocommit connection and isn't worth the added
    complexity/risk for what this phase needs. Records a row count
    snapshot to `system_logs` so growth is visible over time."""
    async with session_scope() as db:
        job_count = (await db.execute(select(func.count()).select_from(Job))).scalar_one()
        await SystemLogRepository(db).create(
            event="db_maintenance_check",
            severity="INFO",
            service="celery_beat",
            detail=f"jobs table row count: {job_count}",
        )
        await db.commit()
