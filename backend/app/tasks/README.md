# Tasks

Celery task definitions — separated from `app/scheduler/` (which only
holds the Celery app config and beat schedule) per Phase 2 §12/§33. Every
task body is a thin wrapper that opens a DB session and calls into the
matching service; no task contains business logic directly.

- `search_tasks.py` — `search_all_providers` (`search` queue)
- `ai_tasks.py` — `score_pending_jobs` (`ai` queue)
- `gmail_tasks.py` — `sync_gmail`, `classify_email_task` (`gmail` queue)
- `telegram_tasks.py` — `send_morning_report`, `send_evening_report` (`notifications` queue)
- `maintenance_tasks.py` — `retry_recoverable_failures`, `cleanup_old_logs`,
  `archive_completed_tasks`, `db_maintenance` (`default` queue)
- `orchestration.py` — `run_morning_cycle`, `run_evening_cycle`,
  `run_cleanup_cycle`: light orchestrators that chain the above with
  Celery's `chain()`, so each step stays independently retryable/
  observable instead of one monolithic task
- `application_tasks.py` (not yet created) — `apply_to_job`; added once
  Playwright automation ships (out of scope this phase)

Every scheduled entry point's async implementation is wrapped in
`@track_scheduled_task(...)` (`app/scheduler/tracking.py`), which writes
the `scheduled_tasks` row automatically — task bodies never do that
bookkeeping by hand. Tasks that aren't naturally idempotent
(`search_all_providers`, `sync_gmail`) also take a Redis lock
(`app/scheduler/locking.py`) so an overlapping beat-triggered run gets
skipped instead of double-running.

See `app/scheduler/celery_app.py` for the beat schedule and queue routing.
