# Repositories

CRUD-only data access — no business logic (Phase 2 §09). Every repository
takes an `AsyncSession` via constructor injection (see `app/api/deps.py`
for the FastAPI-side providers, `app/database/session.session_scope()`
for Celery tasks).

- `base_repository.py` — `BaseRepository[ModelT]`: generic `get`/`list`/
  `count`/`create`/`update`/`soft_delete`, soft-delete filter applied
  automatically for `SoftDeleteMixin` models.
- One file per model needing anything beyond generic CRUD — `job_repository.py`,
  `application_repository.py`, `email_repository.py`, `user_repository.py`,
  `refresh_token_repository.py`, `application_rule_repository.py`,
  `user_profile_repository.py`, `saved_answer_repository.py`,
  `telegram_message_repository.py`, `notification_repository.py`,
  `scheduled_task_repository.py`, `task_log_repository.py`,
  `provider_log_repository.py`, `system_log_repository.py`,
  `audit_log_repository.py`, `feature_flag_repository.py`,
  `company_repository.py`, `job_skill_repository.py`,
  `ai_usage_log_repository.py`.

## Rules

- API routes and Celery tasks never import these directly — only
  `app/services/*` does.
- **Repositories don't commit.** `create`/`update`/`soft_delete` call
  `db.flush()` only — the calling Service method owns the transaction
  boundary and commits once at the end, after every repository call in
  that unit of work has succeeded. This is what makes a multi-step
  operation (e.g. "create application row + write audit log") atomic.
- All queries parameterized via SQLAlchemy's query builder — never raw
  string-interpolated SQL.
