"""Celery application shared by the `celery_worker` and `celery_beat`
containers (Phase 2 §12/§18).

Five queues, separated so a slow AI call doesn't starve a fast search
task: `default`, `search`, `ai`, `gmail`, `notifications`. Routed via
`task_routes` — one place to see the routing table, never scattered
`.apply_async(queue=...)` calls. A single `celery_worker` container
consumes all five (Playwright application prep runs on `default`); the
queue split still matters for observability and is ready for a dedicated
Playwright consumer later without touching this file again.

Schedule (Phase 2 §18) — all times are settings-driven, never hardcoded:

| Time (default)          | Flow |
|---|---|
| JOB_SEARCH_TIME_MORNING | search -> score -> Telegram morning report |
| every GMAIL_SYNC_INTERVAL s | Gmail sync |
| JOB_SEARCH_TIME_EVENING | search again -> retry recoverable failures |
| CLEANUP_TIME            | cleanup logs, archive tasks, DB maintenance |
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "flames",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.search_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.gmail_tasks",
        "app.tasks.telegram_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.orchestration",
        "app.tasks.application_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "app.tasks.search_tasks.*": {"queue": "search"},
        "app.tasks.ai_tasks.*": {"queue": "ai"},
        "app.tasks.gmail_tasks.*": {"queue": "gmail"},
        "app.tasks.telegram_tasks.*": {"queue": "notifications"},
        "app.tasks.maintenance_tasks.*": {"queue": "default"},
        "app.tasks.orchestration.*": {"queue": "default"},
        # Phase 3: dry-run application prep, gated behind the
        # `enable_playwright` feature flag (see application_tasks.py) —
        # still never a real submission, see ApplicationRunnerInterface.apply.
        "app.tasks.application_tasks.apply_to_job": {"queue": "default"},
    },
)

_morning_hour, _morning_minute = settings.hour_minute(settings.job_search_time_morning)
_evening_hour, _evening_minute = settings.hour_minute(settings.job_search_time_evening)
_cleanup_hour, _cleanup_minute = settings.hour_minute(settings.cleanup_time)

celery_app.conf.beat_schedule = {
    "morning-cycle": {
        "task": "app.tasks.orchestration.run_morning_cycle",
        "schedule": crontab(hour=_morning_hour, minute=_morning_minute),
    },
    "gmail-sync": {
        "task": "app.tasks.gmail_tasks.sync_gmail",
        "schedule": settings.gmail_sync_interval,
    },
    "evening-cycle": {
        "task": "app.tasks.orchestration.run_evening_cycle",
        "schedule": crontab(hour=_evening_hour, minute=_evening_minute),
    },
    "cleanup-cycle": {
        "task": "app.tasks.orchestration.run_cleanup_cycle",
        "schedule": crontab(hour=_cleanup_hour, minute=_cleanup_minute),
    },
}

# Side-effect import: registers the JSON-logging signal handlers below.
from app.scheduler import logging_signals  # noqa: E402,F401
