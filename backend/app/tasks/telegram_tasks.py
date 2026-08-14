"""Morning/evening Telegram report Celery tasks. Runs on the
`notifications` queue. Pulls data through `DashboardService` — the same
aggregation the `/dashboard` API endpoint uses (Phase 2 §16), so the two
can't report different numbers.
"""

from __future__ import annotations

import asyncio
import logging

from app.database.session import session_scope
from app.scheduler.celery_app import celery_app
from app.scheduler.tracking import track_scheduled_task
from app.services.dashboard_service import get_dashboard_service
from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.telegram_tasks.send_morning_report")
def send_morning_report() -> None:
    logger.info("Morning report triggered")
    asyncio.run(_send_report("Good morning"))


@celery_app.task(name="app.tasks.telegram_tasks.send_evening_report")
def send_evening_report() -> None:
    logger.info("Evening report triggered")
    asyncio.run(_send_report("Good evening"))


@track_scheduled_task("send_telegram_report")
async def _send_report(greeting: str) -> None:
    async with session_scope() as db:
        summary = await get_dashboard_service(db).get_summary()
        notifications = get_notification_service(db)
        body = (
            f"Jobs found today: {summary.new_jobs_today} (total: {summary.total_jobs})\n"
            f"Matched: {summary.matched_jobs} | Pending review: {summary.pending_review}\n"
            f"Applications today: {summary.applications_today} "
            f"(queued: {summary.queued_applications}, total: {summary.total_applications})\n"
            f"Unprocessed emails: {summary.unprocessed_emails}"
        )
        await notifications.notify(
            title=f"{greeting} — Flames report", body=body, notification_type="daily_report"
        )
