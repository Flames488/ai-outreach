"""Light orchestrator tasks for the morning/evening/cleanup flows — each
step stays an independently retryable, independently observable Celery
task; this just sequences them via `chain()` (Phase 2 §12/§18) rather than
one monolithic task doing everything inline.
"""

from __future__ import annotations

import logging

from app.scheduler.celery_app import celery_app
from app.tasks.ai_tasks import score_pending_jobs
from app.tasks.maintenance_tasks import (
    archive_completed_tasks,
    cleanup_old_logs,
    db_maintenance,
    retry_recoverable_failures,
)
from app.tasks.search_tasks import search_all_providers
from app.tasks.telegram_tasks import send_morning_report

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.orchestration.run_morning_cycle")
def run_morning_cycle() -> None:
    logger.info("Morning cycle starting: search -> score -> report")
    (search_all_providers.si() | score_pending_jobs.si() | send_morning_report.si()).apply_async()


@celery_app.task(name="app.tasks.orchestration.run_evening_cycle")
def run_evening_cycle() -> None:
    logger.info("Evening cycle starting: search -> retry recoverable failures")
    (search_all_providers.si() | retry_recoverable_failures.si()).apply_async()


@celery_app.task(name="app.tasks.orchestration.run_cleanup_cycle")
def run_cleanup_cycle() -> None:
    logger.info("Cleanup cycle starting: logs -> archive -> DB maintenance")
    (cleanup_old_logs.si() | archive_completed_tasks.si() | db_maintenance.si()).apply_async()
