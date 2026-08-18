"""Command handler implementations (Phase 2 §16). Each handler resolves
its data through a Service — never queries the DB directly — and returns
one or more `(text, reply_markup)` pairs for the router to send.

Plain, professional tone: no emoji, short sentences.
"""

from __future__ import annotations

import uuid
from typing import Any

from flames_shared.enums import ApplicationStatus, JobStatus, UserRole
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client
from app.database.session import engine
from app.models.application import Application
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.application_rule_repository import ApplicationRuleRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.repositories.job_repository import JobRepository
from app.repositories.system_log_repository import SystemLogRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.scheduler.pause import PAUSE_FLAG_KEY
from app.services.ai_service import get_ai_service
from app.services.dashboard_service import get_dashboard_service
from app.services.feature_flag_service import FLAG_KEYS, get_feature_flag_service
from app.telegram.keyboards import job_review_keyboard

HandlerResult = list[tuple[str, dict[str, Any] | None]]

ADMIN_ONLY_COMMANDS = {"health", "logs", "restart", "workers", "version"}

COMMAND_DESCRIPTIONS = {
    "start": "Show the welcome message",
    "help": "List available commands",
    "status": "Show bot and connection status",
    "jobs": "List recently discovered jobs",
    "today": "Show today's activity",
    "applications": "List recent applications",
    "review": "Show jobs pending review, with Apply/Skip buttons",
    "emails": "List recently classified emails",
    "stats": "Show dashboard summary statistics",
    "settings": "Show feature flags, or /settings <key> on|off to change one",
    "rules": "List your application rules",
    "profile": "Show the profile the AI scores jobs against",
    "search": "Run a job search + AI scoring cycle right now",
    "pause": "Pause automated search/scoring cycles",
    "resume": "Resume automated search/scoring cycles",
    "health": "Show system health (admin only)",
    "logs": "Show recent system log entries (admin only)",
    "apply": "Not yet available — queue from /review's Apply button instead",
    "retry": "Not yet available — retry a failed application from the dashboard instead",
}

_NOT_YET_AVAILABLE = {"apply", "retry"}


async def dispatch_command(
    db: AsyncSession, user: User, command: str, args: list[str]
) -> HandlerResult:
    if command in ADMIN_ONLY_COMMANDS and user.role != UserRole.ADMIN:
        return [("Access denied. This command is admin-only.", None)]

    if command in _NOT_YET_AVAILABLE:
        return [(f"/{command} is not yet available. {COMMAND_DESCRIPTIONS[command]}.", None)]

    handler = _HANDLERS.get(command)
    if handler is None:
        return [("Unknown command. Send /help for the list of available commands.", None)]
    return await handler(db, user, args)


# Commands the free-text assistant may route to. Deliberately excludes
# pause/resume/search (state-changing, or costly/slow — require the
# explicit command, never an AI guess) and anything in _NOT_YET_AVAILABLE.
ASSISTANT_ELIGIBLE_COMMANDS = {
    "start",
    "help",
    "status",
    "jobs",
    "today",
    "applications",
    "review",
    "emails",
    "stats",
    "settings",
    "rules",
    "profile",
    "health",
    "logs",
}


async def dispatch_freeform_message(db: AsyncSession, user: User, text: str) -> HandlerResult:
    """Handles a Telegram message that isn't a slash command (Phase 5).
    Uses the AI provider to map free text onto an existing read-only
    command, or to answer directly. Never lets an AI failure bubble up to
    the webhook route — always degrades to a plain-text fallback so the
    user gets a reply either way."""
    available = {
        name: COMMAND_DESCRIPTIONS[name]
        for name in ASSISTANT_ELIGIBLE_COMMANDS
        if name in COMMAND_DESCRIPTIONS
        and (name not in ADMIN_ONLY_COMMANDS or user.role == UserRole.ADMIN)
    }

    try:
        intent = await get_ai_service(db).interpret_telegram_message(text, available)
    except Exception:
        return [("Sorry, I couldn't process that. Send /help for the list of commands.", None)]

    if intent.command is None or intent.command not in available:
        return [(intent.reply, None)]

    handler = _HANDLERS[intent.command]
    result = await handler(db, user, [])
    result[0] = (f"{intent.reply}\n\n{result[0][0]}", result[0][1])
    return result


async def _handle_start(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    return [
        (
            f"Flames is connected, {user.email}. Send /help for the list of commands.",
            None,
        )
    ]


async def _handle_help(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    lines = ["Available commands:"]
    for command, description in COMMAND_DESCRIPTIONS.items():
        if command in ADMIN_ONLY_COMMANDS and user.role != UserRole.ADMIN:
            continue
        lines.append(f"/{command} — {description}")
    return [("\n".join(lines), None)]


async def _handle_status(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    flags = FeatureFlagRepository(db)
    paused = await flags.get_by_key(PAUSE_FLAG_KEY)
    is_paused = paused is not None and paused.enabled
    gmail_status = "connected" if user.gmail_connected else "not connected"
    return [
        (
            f"Operations: {'paused' if is_paused else 'running'}\n"
            f"Gmail: {gmail_status}\n"
            f"Role: {user.role.value}",
            None,
        )
    ]


async def _handle_jobs(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    jobs = await JobRepository(db).list(limit=10)
    if not jobs:
        return [("No jobs discovered yet.", None)]
    lines = ["Recent jobs:"]
    for job in jobs:
        score = f"{job.ai_score:.0f}" if job.ai_score is not None else "unscored"
        lines.append(f"- {job.title} ({job.status.value}, score {score})")
    return [("\n".join(lines), None)]


async def _handle_today(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    summary = await get_dashboard_service(db).get_summary()
    return [
        (
            f"Jobs found today: {summary.new_jobs_today}\n"
            f"Applications today: {summary.applications_today}\n"
            f"Pending review: {summary.pending_review}",
            None,
        )
    ]


async def _handle_applications(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    applications: list[Application] = await ApplicationRepository(db).list(limit=10)
    if not applications:
        return [("No applications yet.", None)]
    lines = ["Recent applications:"]
    for application in applications:
        lines.append(f"- Job {application.job_id}: {application.application_status.value}")
    return [("\n".join(lines), None)]


async def _handle_review(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    jobs = await JobRepository(db).list(status=JobStatus.REVIEW, limit=5)
    if not jobs:
        return [("No jobs are pending review.", None)]

    result: HandlerResult = []
    for job in jobs:
        score = f"{job.ai_score:.0f}" if job.ai_score is not None else "unscored"
        text = f"{job.title}\nScore: {score}\n{job.application_url}"
        result.append((text, job_review_keyboard(str(job.id))))
    return result


async def _handle_emails(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    emails = await EmailRepository(db).list(limit=10)
    if not emails:
        return [("No emails synced yet.", None)]
    lines = ["Recent emails:"]
    for email in emails:
        lines.append(f"- {email.subject} ({email.category.value}) from {email.sender}")
    return [("\n".join(lines), None)]


async def _handle_stats(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    summary = await get_dashboard_service(db).get_summary()
    return [
        (
            f"Total jobs: {summary.total_jobs}\n"
            f"Matched: {summary.matched_jobs}\n"
            f"Pending review: {summary.pending_review}\n"
            f"Total applications: {summary.total_applications}\n"
            f"Queued: {summary.queued_applications}\n"
            f"Unprocessed emails: {summary.unprocessed_emails}",
            None,
        )
    ]


async def _handle_settings(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    from app.config.settings import get_settings

    flag_service = get_feature_flag_service(db)

    if len(args) == 2 and args[0] in FLAG_KEYS and args[1].lower() in ("on", "off"):
        enabled = args[1].lower() == "on"
        await flag_service.set(args[0], enabled)
        return [(f"{args[0]} is now {'enabled' if enabled else 'disabled'}.", None)]

    settings = get_settings()
    flags = await flag_service.get_all()
    lines = ["Feature flags — /settings <key> on|off to change one:"]
    lines.extend(f"- {key}: {'on' if enabled else 'off'}" for key, enabled in flags.items())
    lines.append(f"\nJob match threshold: {settings.job_match_threshold}")
    return [("\n".join(lines), None)]


async def _handle_rules(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    rules = await ApplicationRuleRepository(db).list(user_id=user.id, limit=20)
    if not rules:
        return [("No rules defined yet. Add them from the dashboard's Rules page.", None)]
    lines = ["Your rules:"]
    for rule in rules:
        state = "on" if rule.enabled else "off"
        condition = rule.condition
        lines.append(
            f"- [{state}] {rule.name} ({rule.priority_tier.value}): "
            f"{condition['field']} {condition['op']} {condition['value']}"
        )
    return [("\n".join(lines), None)]


async def _handle_profile(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    profile = await UserProfileRepository(db).get_by_user_id(user.id)
    if profile is None or not profile.full_name:
        return [
            (
                "No profile set yet. Fill it in from the dashboard's Profile "
                "page — it's what the AI scores every job against.",
                None,
            )
        ]
    location = ", ".join(filter(None, [profile.city, profile.country])) or "—"
    lines = [
        f"Name: {profile.full_name}",
        f"Position: {profile.current_position or '—'}",
        f"Experience: {profile.years_of_experience or '—'} years",
        f"Location: {location}",
        f"Work authorization: {profile.work_authorization or '—'}",
    ]
    return [("\n".join(lines), None)]


async def _handle_search(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    from app.tasks.ai_tasks import _score_pending_jobs
    from app.tasks.search_tasks import _search_all_providers

    found = await _search_all_providers()
    await _score_pending_jobs()
    return [(f"Search complete: {found} new job(s) found and scored.", None)]


async def _handle_pause(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    await _set_pause_flag(db, True)
    return [("Automated search/scoring cycles are now paused.", None)]


async def _handle_resume(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    await _set_pause_flag(db, False)
    return [("Automated search/scoring cycles are now running.", None)]


async def _set_pause_flag(db: AsyncSession, enabled: bool) -> None:
    flags = FeatureFlagRepository(db)
    existing = await flags.get_by_key(PAUSE_FLAG_KEY)
    if existing is None:
        await flags.create(
            key=PAUSE_FLAG_KEY,
            enabled=enabled,
            description="Set via /pause and /resume Telegram commands.",
        )
    else:
        existing.enabled = enabled
    await db.commit()


async def _handle_health(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    checks = {"database": False, "redis": False}
    try:
        async with engine.connect() as connection:
            await connection.execute(sql_text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        await redis_client.ping()
        checks["redis"] = True
    except Exception:
        pass

    lines = [f"{name}: {'ok' if ok else 'unreachable'}" for name, ok in checks.items()]
    return [("\n".join(lines), None)]


async def _handle_logs(db: AsyncSession, user: User, args: list[str]) -> HandlerResult:
    logs = await SystemLogRepository(db).list(limit=10)
    if not logs:
        return [("No system log entries.", None)]
    lines = ["Recent system log entries:"]
    for entry in logs:
        lines.append(f"- [{entry.severity}] {entry.event}: {entry.detail or ''}")
    return [("\n".join(lines), None)]


async def handle_job_review_callback(db: AsyncSession, user: User, action: str, job_id: str) -> str:
    job_repo = JobRepository(db)
    job = await job_repo.get(uuid.UUID(job_id))
    if job is None:
        return "That job no longer exists."

    if action == "skip":
        job.status = JobStatus.SKIPPED
        await db.commit()
        return f"Skipped: {job.title}."

    if action == "apply":
        applications = ApplicationRepository(db)
        if await applications.exists_for_job(job.id):
            return f"An application already exists for {job.title}."
        await applications.create(
            job_id=job.id,
            user_id=user.id,
            application_status=ApplicationStatus.QUEUED,
        )
        job.status = JobStatus.APPLIED
        await db.commit()
        return f"Queued for application: {job.title}."

    if action == "view":
        return f"{job.title}\n{job.description[:500]}\n{job.application_url}"

    return "Unrecognized action."


_HANDLERS = {
    "start": _handle_start,
    "help": _handle_help,
    "status": _handle_status,
    "jobs": _handle_jobs,
    "today": _handle_today,
    "applications": _handle_applications,
    "review": _handle_review,
    "emails": _handle_emails,
    "stats": _handle_stats,
    "settings": _handle_settings,
    "rules": _handle_rules,
    "profile": _handle_profile,
    "search": _handle_search,
    "pause": _handle_pause,
    "resume": _handle_resume,
    "health": _handle_health,
    "logs": _handle_logs,
}
