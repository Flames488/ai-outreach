# Scheduler

Celery app config + beat schedule only — task bodies live in `app/tasks/`
(Phase 2 §12: "Celery tasks are separated from API logic"). A single
`celery_worker` container consumes all five queues this phase (no
dedicated Playwright container yet); `celery_beat` fires task signals on
a cron schedule and runs neither queue itself.

- `celery_app.py` — Celery app, Redis broker/backend, queues, beat schedule
- `logging_signals.py` — JSON logging setup + task_id/execution_time context per task
- `tracking.py` — `@track_scheduled_task(name)`: writes the `scheduled_tasks` row automatically
- `locking.py` — `task_lock(name, ttl)`: Redis lock preventing overlapping runs

## Queues

| Queue | Tasks |
|---|---|
| `default` | `run_morning_cycle`, `run_evening_cycle`, `run_cleanup_cycle` (orchestrators), `retry_recoverable_failures`, `cleanup_old_logs`, `archive_completed_tasks`, `db_maintenance` |
| `search` | `search_all_providers` |
| `ai` | `score_pending_jobs` |
| `gmail` | `sync_gmail`, `classify_email_task` |
| `notifications` | `send_morning_report`, `send_evening_report` |

## Schedule

All times are settings-driven (`app/config/settings.py`), never hardcoded here.

| Task | When (default) |
|---|---|
| `run_morning_cycle` (search -> score -> Telegram report) | `JOB_SEARCH_TIME_MORNING` (07:00 UTC) |
| `sync_gmail` | every `GMAIL_SYNC_INTERVAL`s (300s) |
| `run_evening_cycle` (search again -> retry recoverable failures) | `JOB_SEARCH_TIME_EVENING` (19:00 UTC) |
| `run_cleanup_cycle` (logs, archive, DB maintenance) | `CLEANUP_TIME` (00:00 UTC) |

## Status

Fully wired end to end for the RemoteOK provider + Groq/DeepSeek scoring +
Gmail sync/classify + Telegram reports. `retry_recoverable_failures` only
does DB-level bookkeeping (re-queues `FAILED` -> `QUEUED`, bumps
`retry_count`) — it doesn't resubmit anything yet since Playwright
automation isn't built this phase.
