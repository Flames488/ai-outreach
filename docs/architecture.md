# Flames — Architecture (Phase 2)

## Mission

Flames is an autonomous personal recruitment assistant: it searches for
jobs, scores them against the user's CV using AI, applies where relevant,
tracks every application, monitors Gmail for recruiter responses, and
reports everything through Telegram.

## Philosophy

Quality over quantity. Never spam. Never submit duplicates. Never bypass
CAPTCHAs or anti-bot measures — skip and log those instead. Every action is
auditable. Microservice-inspired: every container has one responsibility,
is independently restartable, and talks to the others only over the
internal Docker network. AI advises; application logic decides — the Rule
Engine, not the AI, has the final say on apply/review/skip.

## Stack

Python 3.12 / FastAPI, PostgreSQL 17, Redis, Celery (5 queues), Groq +
DeepSeek (AI, both OpenAI-chat-completions-compatible, behind a
provider-agnostic interface), Telegram Bot API, Gmail API (OAuth 2.0,
read-only), Docker Compose, Nginx, SQLAlchemy 2.x, Alembic, JWT (access +
refresh tokens), Argon2 password hashing, Fernet encryption (`cryptography`),
uv, Pytest/pytest-asyncio/respx/factory-boy. Playwright (actual application
submission) and the React dashboard are later phases.

## Layered architecture

```
Client -> API Route -> Service -> Repository -> Database
```

- API routes (`app/api/v1/`) validate the request, call exactly one
  service, and return the standard response envelope. No business logic,
  no DB access.
- Services (`app/services/`) hold all business logic. Each is the only
  layer allowed to combine a repository with a provider/client
  (Groq/DeepSeek, Gmail, Telegram, a job source).
- Repositories (`app/repositories/`, generic `BaseRepository[ModelT]`) are
  CRUD only — no business logic, and they never `commit()`. The calling
  service owns the transaction and commits once per unit of work, which is
  what keeps multi-step operations (e.g. ingest a job + create its skills)
  atomic.
- Long-running work (search, AI, Gmail sync, notifications) never runs
  inside an API route — it's dispatched to Celery, tracked in
  `scheduled_tasks`, and the API returns immediately.

## Containers

| Service | Image basis | Role | Ports |
|---|---|---|---|
| `nginx` | `docker/nginx/Dockerfile` | Reverse proxy: `/api/` -> `api`, everything else -> `frontend`, gzip | **80 (only externally-exposed service in dev)** |
| `frontend` | `frontend/Dockerfile` | React dashboard, built to static assets, served by its own nginx with SPA fallback | internal only |
| `api` | `backend/Dockerfile` | FastAPI REST API, JWT auth | internal only |
| `celery_worker` | `backend/Dockerfile` (same image, different `command:`) | All 5 queues (default/search/ai/gmail/notifications) | internal only |
| `celery_beat` | `backend/Dockerfile` | Fires the beat schedule (morning/afternoon/evening cycles, Gmail sync, cleanup) | internal only |
| `flower` | `backend/Dockerfile` | Celery monitoring UI (dev profile only) | internal only |
| `migrate` | `backend/Dockerfile` | One-off: runs `alembic upgrade head`, then exits; gates every other app container | none |
| `postgres` | `postgres:17-alpine` | Primary datastore | internal only |
| `redis` | `redis:7-alpine` | Celery broker/result backend, cache, rate limiting, task locks | internal only |
| `caddy` (prod only, `docker-compose.prod.yml`) | `caddy:2-alpine` | Automatic Let's Encrypt HTTPS, reverse-proxies to `nginx` | **80, 443** |

`api`, `celery_worker`, `celery_beat`, and `flower` all build from the
**same** `backend/Dockerfile` — they're differentiated only by their
`command:` and a `FLAMES_SERVICE_NAME` env var, not by separate images.
There's no dedicated `playwright` container — Playwright automation runs
inside `celery_worker`. In dev, `nginx` is the only service that publishes
a host port; in production, `caddy` takes that role instead (`nginx`
becomes internal-only) so TLS terminates before anything else. See
`docs/deployment.md` for the full production setup.

## Backend module map (`backend/app/`)

| Folder | Role |
|---|---|
| `api/v1/` | Thin routes — auth, jobs, applications, rules, emails, gmail, telegram (webhook), settings, users, dashboard, health |
| `auth/` | JWT (access + refresh) + Argon2 password hashing |
| `config/` | `Settings` — the *only* thing that reads `.env` directly |
| `core/` | JSON logging (with secret-scrubbing), Redis client, `FlamesAPIError`, rate limiter (fails open if Redis is down) |
| `database/` | Async SQLAlchemy engine/session, `Base`/mixins (UUID PK, timestamps, soft delete) |
| `middleware/` | Request ID + timing, rate limiting, security headers |
| `models/` | 22 SQLAlchemy ORM models, UUID PKs, native Postgres enums |
| `repositories/` | Generic `BaseRepository[ModelT]` — CRUD only, never commits |
| `rules/` | `application_rules` condition schema (allowlisted fields/ops) + evaluator |
| `schemas/` | API-facing Pydantic models, incl. the response envelope |
| `services/` | All business logic — the only layer allowed to combine a repository with a provider/client |
| `providers/` | Job-source integrations (`Provider.search() -> normalize() -> StandardJob`); `RemoteOKProvider` is real and working end-to-end |
| `ai/` | `AIProvider` ABC + shared `_ChatCompletionAIProvider` base + `GroqProvider`/`DeepSeekProvider` + `PromptLoader` |
| `gmail/` | OAuth flow (`google_auth_oauthlib`) + message fetch client |
| `telegram/` | Bot API client, webhook auth, command router, 14 command handlers, and a free-text AI assistant fallback |
| `playwright/` | `BrowserEngine` (Chromium lifecycle, retried launch/nav), 5 ATS plugins (Greenhouse/Lever/Workday/Ashby/SmartRecruiters), `PlaywrightApplicationRunner.dry_run()` — real and wired into the pipeline; `.apply()` (real submission) stays `NotImplementedError` by design |
| `scheduler/` | Celery app config, 5-queue routing, beat schedule, task tracking/locking, pause flag |
| `tasks/` | Celery task bodies (search/ai/gmail/telegram/maintenance/application) + orchestration chains |
| `utils/` | Cross-cutting helpers: `async_retry_with_backoff`, Fernet encryption |
| `prompts/` (repo root under `backend/`) | AI prompts as `.md` files with `{{variable}}` placeholders, never hardcoded strings |

`shared/` (`flames_shared`, a uv workspace member) holds the DTOs/enums
every module agrees on — no service imports another service's internals.

## Database

PostgreSQL 17, SQLAlchemy 2.x (typed `Mapped`/`mapped_column`), Alembic.
Every table: UUID primary key (`app/database/base.py:UUIDPrimaryKeyMixin`,
client-side `uuid4()` default plus `gen_random_uuid()` server default),
`snake_case` plural name, native Postgres enums (`native_enum=True`).
`jobs`, `applications`, and `email_messages` are soft-deleted
(`deleted_at`, never a hard `DELETE` — `BaseRepository` filters
`deleted_at IS NULL` by default).

22 tables: `users`, `user_profiles`, `refresh_tokens`, `feature_flags`,
`companies`, `jobs`, `job_skills`, `applications`, `application_rules`,
`cv_versions`, `cover_letters`, `saved_answers`, `email_messages`,
`email_labels`, `notifications`, `telegram_messages`, `scheduled_tasks`,
`task_logs`, `provider_logs`, `system_logs`, `audit_logs`, `ai_usage_logs`.

`jobs.status` (`JobStatus`) and `applications.status`
(`ApplicationStatus`: QUEUED/RUNNING/SUCCESS/FAILED/REVIEW_REQUIRED/
PENDING_VERIFICATION/CANCELLED) are independent — a job can be skipped with
no application ever attempted.

### Rule Engine

`application_rules` stores its `condition` as JSONB
(`{field, op, value}`), validated against an explicit allowlist of fields
and operators at **write time** (`app/rules/schema.py`) — never `eval()`,
and rejected up front rather than only failing at evaluation time. Rules
are grouped into three tiers, evaluated in order by
`RuleEngineService.evaluate()`:

1. **CRITICAL** and **REQUIRED** are pass/fail gates — the first failure
   short-circuits evaluation and writes an `audit_logs` entry explaining
   the block.
2. **PREFERENCE** rules never block; they only influence ranking among
   jobs that already passed the gates.

## API

Every endpoint is versioned (`/api/v1/`) and returns the standard envelope
(`app/schemas/envelope.py`):

```json
{ "success": true, "message": "...", "data": {}, "meta": {} }
{ "success": false, "message": "...", "errors": [{ "code": "...", "detail": "..." }] }
```

`app/core/exceptions.py:FlamesAPIError` plus global handlers in
`app/main.py` (catching `FlamesAPIError`, `StarletteHTTPException`,
`RequestValidationError`, and bare `Exception`) guarantee every failure —
including unhandled exceptions — comes back through that envelope with a
`flames_shared.enums.ErrorCode`, never a raw stack trace.

Auth: JWT access token (short-lived) + refresh token (rotated on
`/auth/refresh`, revocable, hashed at rest). Password hashing: Argon2.
`UserRole` (ADMIN/USER) is carried in the JWT.

Middleware stack (innermost -> outermost): request ID + JSON-logged
timing, Redis-backed rate limiting (fails open if Redis is unreachable —
a protective measure shouldn't itself become a single point of failure),
security headers, GZip, CORS, TrustedHost.

`/health` (liveness, always 200) is distinct from `/ready` (readiness —
Postgres/Redis/Celery all reachable; this gates docker-compose
`depends_on`). `/metrics` exposes Prometheus metrics via
`prometheus-fastapi-instrumentator`. `/docs`/`/redoc` are gated behind
`DEBUG=true`.

Route surface: `auth`, `jobs`, `applications`, `rules`, `emails`, `gmail`
(OAuth connect/callback/status), `telegram` (webhook, validates the
`X-Telegram-Bot-Api-Secret-Token` header), `settings` (feature flags),
`users` (`/users/me` GET/PATCH), `dashboard`, `health`.

## AI

`AIProvider` ABC (`app/ai/provider.py`): `analyze_job`, `score_match`,
`generate_cover_letter`, `classify_email`, `answer_question`. Both
`GroqProvider` and `DeepSeekProvider` are thin subclasses of a shared
`_ChatCompletionAIProvider` base (`app/ai/base_provider.py`) since both
speak the OpenAI chat-completions format — selected at runtime via
`AI_PROVIDER` (`app/ai/registry.py`). Every call goes through `AIService`
(`app/services/ai_service.py`), which enforces an AI-specific rate limit
and logs each call to `ai_usage_logs` (provider, model, task type, tokens,
success/failure) so free-tier exhaustion is visible before it happens.

`score_match()` is advisory only (`MatchResult`: score 0-100, a suggested
decision, reasons, missing skills) — the actual apply/review/skip routing
combines this with the Rule Engine, never the AI alone.

Prompts live as files in `backend/prompts/*.md` (`job_analysis.md`,
`job_matching.md`, `cover_letter.md`, `email_classifier.md`,
`application_answers.md`), loaded by `app/ai/prompt_loader.py`, never
hardcoded strings.

## Gmail

OAuth 2.0, read-only scopes (`gmail.readonly`, `gmail.labels`).
`app/gmail/oauth.py` builds the consent URL and exchanges the auth code;
the refresh token is Fernet-encrypted (`MASTER_ENCRYPTION_KEY`) before
being stored on `users.google_refresh_token_encrypted` — the short-lived
access token is never persisted. `EmailService.sync_inbox_for_user`
dedupes on `gmail_message_id`, and flips `gmail_connected=False` with a
SYSTEM notification if the stored token stops working.

## Telegram

`app/telegram/router.py:handle_update` dispatches incoming webhook updates
to one of 14 commands (start/help/status/jobs/today/applications/review/
emails/stats/settings/pause/resume, plus admin-only health/logs), rate
limited per `chat_id`. `/pause` and `/resume` toggle a real
`feature_flags` row (`operations_paused`) that `search_tasks`/`ai_tasks`
check before doing work.

Anything that isn't a slash command is routed to
`dispatch_freeform_message` (`app/telegram/handlers.py`) instead of being
dropped: `AIService.interpret_telegram_message` maps the free text onto
one of the read-only commands above, or answers directly if none apply.
The mapping is advisory only — the caller re-validates the AI's chosen
command against `ASSISTANT_ELIGIBLE_COMMANDS`, which deliberately excludes
`pause`/`resume` and every admin-only command from non-admins, so a
misread message can never trigger a state change, only show data. An AI
failure degrades to a plain "try /help" reply rather than raising into the
webhook route.

## Frontend

`frontend/` — React 18 + TypeScript + Vite, TanStack Query for server
state, `react-router-dom` for routing, Tailwind for styling, Recharts for
the Overview page's charts. `src/lib/api.ts` is a typed client over every
`/api/v1/*` route with automatic access-token refresh on a 401. Pages:
Overview (stats + charts), Jobs (filter/search, detail drawer, queue an
application), Applications (status filter, detail drawer with timeline +
retry), Emails, Rules (CRUD against the same field/op allowlist the
backend enforces), Settings (feature flags, Gmail connect). Built to
static assets and served by its own nginx (`frontend/Dockerfile`,
`frontend/nginx.conf` — SPA fallback to `index.html`), sitting behind the
main reverse proxy like every other internal service.

## Scheduler (Celery)

5 queues: `default`, `search`, `ai`, `gmail`, `notifications`. Beat
schedule (`app/scheduler/celery_app.py`): `morning-cycle`,
`afternoon-cycle`, `evening-cycle` (search + score + queue), `gmail-sync`
(interval-based, `GMAIL_SYNC_INTERVAL` seconds), `cleanup-cycle`.
`@track_scheduled_task` wraps every scheduled task body to write a
`scheduled_tasks` row automatically; `task_lock()` (Redis `SET NX EX`)
prevents overlapping runs of the same task. Orchestration
(`app/tasks/orchestration.py`) chains task signatures (`.si()`, immutable)
rather than passing large payloads between tasks.

## Config

`app/config/settings.py` is the only module that reads environment
variables directly (enforced by convention — grep for `os.getenv`/
`os.environ` elsewhere is a bug). Two tiers:

- **Infra secrets** (`SECRET_KEY`, `JWT_SECRET`, `POSTGRES_PASSWORD`,
  `MASTER_ENCRYPTION_KEY`) fail the boot immediately if blank — they cost
  nothing to generate locally, and `MASTER_ENCRYPTION_KEY` is additionally
  validated as a real Fernet key at startup.
- **Integration credentials** (Groq/DeepSeek/Telegram/Google) log a
  startup warning instead of failing, since not every account is set up
  on day one — deliberately softer than a literal "crash if missing" for
  those.

## Status

All seven phases have real, working code behind them, not scaffolding:

- **Backend** (Phase 2): job discovery across 8 providers (RemoteOK,
  Indeed, Lever, Greenhouse, Google Jobs, Wellfound, company career pages,
  a generic mapper), AI scoring (Groq/DeepSeek), the Rule Engine, Gmail
  OAuth/sync/classification, and a full REST API — all covered by an
  automated test suite.
- **Playwright automation** (Phase 3): a real dry-run engine (5 ATS
  plugins) wired into the pipeline via `app/tasks/application_tasks.py` —
  every `QUEUED` application is automatically driven through to
  `PENDING_VERIFICATION` or `FAILED`. Real submission
  (`ApplicationRunnerInterface.apply`) is a deliberate, documented
  non-goal, not a missing feature — see `app/playwright/README.md`'s
  "non-negotiable rules."
- **React dashboard** (Phase 4): full CRUD/read UI over every API route —
  see "Frontend" above.
- **Telegram AI assistant** (Phase 5): the 14-command bot plus a free-text
  AI layer that maps natural language onto those same read-only commands.
- **AI intelligence** (Phase 6): job matching, cover letters, application
  answers, and email classification, all wired into real services, not
  orphaned prompt files.
- **Production deployment** (Phase 7): `docker-compose.prod.yml` +
  `.github/workflows/deploy.yml` + Caddy for automatic HTTPS — see
  `docs/deployment.md`.

What's still a conscious limitation rather than a gap: real application
submission never happens without a human in the loop (dry-run stops at
`PENDING_VERIFICATION` for a person to review and submit), and Flames
remains single-tenant by design (one CV, one set of rules) — see
`ApplicationRepository.count_today`'s docstring.
