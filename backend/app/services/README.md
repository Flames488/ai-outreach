# Services

Business logic — the only layer allowed to combine a repository with a
provider/client (Part 3 §21/§23: `Client -> API Route -> Service ->
Repository -> Database`). API routes and Celery tasks call these; nothing
downstream (`repositories/`, `providers/`, `ai/`, `gmail/`, `telegram/`,
`playwright/`) is imported directly from anywhere else.

- `job_service.py` — provider orchestration (discover, dedupe) + job reads
- `application_service.py` — Playwright submission + application reads
- `ai_service.py` — wraps the active `AIProvider` (Groq), logs every call to `ai_usage_logs`
- `email_service.py` — Gmail sync orchestration + email reads
- `notification_service.py` — formats and sends Telegram notifications
- `settings_service.py` — the only thing that reads `app.config.settings` on behalf of a route (Part 5 §62)

Each exposes a `get_*_service(...)` composition root — that's the single
place a provider/client implementation is chosen, so swapping one (e.g. a
second `AIProvider`) never touches a caller.
