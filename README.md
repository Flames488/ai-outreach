# Flames

Autonomous job search, application, and tracking assistant. Searches job
sources, scores postings against your CV with AI, applies where relevant,
tracks every application, monitors Gmail for recruiter replies, and
reports through Telegram.

See [docs/architecture.md](docs/architecture.md) for the full system
design and [docs/deployment.md](docs/deployment.md) for the production
runbook. Built phase by phase, all seven now real:

1. **Architecture/infrastructure** — Docker Compose, layered backend.
2. **Backend** — job discovery across 8 providers, AI scoring
   (Groq/DeepSeek), Gmail sync/classification, the Rule Engine, a full
   REST API.
3. **Playwright automation** — a real dry-run engine (5 ATS plugins)
   wired into the pipeline: every queued application is automatically
   driven to `PENDING_VERIFICATION` or `FAILED`, ready for a human to
   review and submit. Real, unattended submission is a deliberate
   non-goal, not a missing feature.
4. **React dashboard** — full CRUD/read UI over every API route.
5. **Telegram AI assistant** — the command bot plus a free-text layer
   that maps natural language onto the same read-only commands.
6. **AI intelligence** — job matching, cover letters, application
   answers, email classification, all wired into real services.
7. **Production deployment** — `docker-compose.prod.yml`, a GitHub
   Actions build/push/deploy pipeline, Caddy for automatic HTTPS.

## Layout

```
flames/
├── backend/
│   ├── app/
│   │   ├── api/            thin routes — validate, call a service, return the envelope
│   │   ├── auth/            JWT + password hashing (Argon2)
│   │   ├── config/           Settings — the only thing that reads .env
│   │   ├── core/              JSON logging, Redis client, FlamesAPIError, rate limiter
│   │   ├── database/           async SQLAlchemy engine/session/base
│   │   ├── middleware/          request ID, rate limiting, security headers
│   │   ├── models/               SQLAlchemy ORM (UUID PKs, soft delete)
│   │   ├── repositories/          CRUD only, generic BaseRepository
│   │   ├── rules/                  application_rules condition schema + evaluator
│   │   ├── schemas/                 API-facing Pydantic models + response envelope
│   │   ├── services/                 all business logic (Client -> API -> Service -> Repository -> DB)
│   │   ├── providers/                 job-source integrations (8: RemoteOK, Indeed, Lever, Greenhouse, Google Jobs, Wellfound, company sites, generic)
│   │   ├── ai/                         AIProvider interface + Groq/DeepSeek
│   │   ├── gmail/                       OAuth + message fetch
│   │   ├── telegram/                     bot webhook, command router, handlers, free-text AI assistant
│   │   ├── playwright/                    browser engine + 5 ATS plugins; dry-run automation, wired into the pipeline
│   │   ├── scheduler/                      Celery app config, beat schedule, task tracking/locking
│   │   ├── tasks/                           Celery task bodies, incl. application_tasks.py (Playwright dry-run)
│   │   └── utils/                            cross-cutting helpers (retry/backoff, encryption)
│   ├── prompts/    AI prompts as files, never hardcoded strings
│   ├── migrations/ Alembic
│   └── tests/      mirrors app/
├── frontend/    React 18 + TypeScript dashboard (Vite, TanStack Query, Tailwind, Recharts)
├── shared/      flames_shared — DTOs/enums/constants every service depends on
├── docker/      nginx/ + caddy/ (production TLS) — api/celery_worker/celery_beat/flower share backend/Dockerfile
├── docs/        Architecture + deployment documentation
├── scripts/     Local setup + seed helpers
├── data/        Bind-mounted into containers — put your cv.pdf / cover letter template here
├── logs/        Local (non-Docker) log output; Docker containers use the `logs` named volume instead
├── docker-compose.yml       local/dev — builds every image from source
├── docker-compose.prod.yml  production — pulls prebuilt images, adds Caddy for HTTPS
└── tests/       Cross-service integration tests
```

See [docs/architecture.md](docs/architecture.md) for what each layer does
and how a request flows through them.

## Local setup

```bash
./scripts/bootstrap.sh        # creates .env from .env.example if missing
# edit .env: fill in real Groq/Telegram/Google credentials when you reach
# the features that need them — the infra boots fine with those left
# blank (deliberately softer than Phase 2's literal "crash if missing"
# spec, since you won't have every account set up on day one).

docker compose build
docker compose up -d
docker compose run --rm api uv run python scripts/seed.py   # initial admin user, default flags/rules
```

`migrate` runs Alembic to `head` automatically before `api`,
`celery_worker`, and `celery_beat` start — no manual migration step
needed. To generate a new migration after changing models:

```bash
docker compose run --rm api uv run alembic revision --autogenerate -m "describe the change"
docker compose up -d --build migrate api celery_worker celery_beat
```

The dashboard is served at `http://localhost/`, the API at
`http://localhost/api/v1/` (docs at `/api/v1/docs` when `DEBUG=true`).
Celery monitoring (Flower) is dev-only and not started by default:

```bash
docker compose --profile dev up -d flower
```

## Backend development (without Docker)

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv sync --directory backend
uv run --directory backend pytest
uv run --directory backend uvicorn app.main:app --reload
```

## Frontend development (without Docker)

Requires Node 20+.

```bash
npm install --prefix frontend
npm run dev --prefix frontend      # http://localhost:5173, proxies /api to :8000
npm run build --prefix frontend
```

## Design rules

- **Client -> API Route -> Service -> Repository -> Database.** Routes
  never touch the database or contain business logic; repositories are
  CRUD only (`BaseRepository[ModelT]` — they never commit, the calling
  service owns the transaction); services are the only layer allowed to
  combine a repository with a provider/client (Groq/DeepSeek, Gmail,
  Telegram, a job source).
- Every domain module (`ai/`, `gmail/`, `telegram/`, `playwright/`,
  `providers/*`) exposes an ABC interface plus a concrete implementation,
  wired through a `get_*()` composition root in the matching
  `services/*_service.py`. Cross-module data uses `flames_shared` DTOs —
  no service imports another service's internals.
- Every API response uses the standard envelope
  (`app/schemas/envelope.py`) — `{success, message, data, meta}` on
  success, `{success, message, errors: [{code, detail}]}` on failure.
  Failures never leak a raw stack trace to the client.
- `jobs`/`applications`/`email_messages` are soft-deleted (`deleted_at`),
  never hard-deleted. Every table uses a UUID primary key, native Postgres
  enums where the column is an enum.
- `application_rules` conditions are JSONB (`field`/`op`/`value`),
  validated against an explicit field/op allowlist at write time — never
  `eval()`, never validated only at evaluation time.
- Only `nginx` publishes a host port — every other service talks over the
  internal `flames-network` bridge only.
- Credentials live in `.env` only (see `.env.example`); never hardcoded
  (grep for `os.getenv`/`os.environ` outside `app/config/settings.py` —
  any hit is a bug). Infra secrets (`SECRET_KEY`, `JWT_SECRET`,
  `POSTGRES_PASSWORD`, `MASTER_ENCRYPTION_KEY`) fail the boot immediately
  if blank — they cost nothing to generate locally. Integration
  credentials (Groq/DeepSeek/Telegram/Google) log a startup warning
  instead of failing.
- AI provider is selected via `AI_PROVIDER` (`groq` default, `deepseek`
  supported) — both are OpenAI-chat-completions-compatible, so adding a
  third is a new class in `app/ai/` plus one line in `app/ai/registry.py`.
