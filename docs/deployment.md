# Flames — Production Deployment (Phase 7)

This is the real path from "runs on my machine via `docker compose up`"
to a deployed, HTTPS-served instance. It assumes a single host (a VPS —
Hetzner, DigitalOcean, Linode, an EC2 instance, anywhere you can SSH into
a box with Docker) rather than Kubernetes; the stack is a handful of
Compose services, and a second orchestrator would be more operational
overhead than the workload justifies.

## Pieces

- **`docker-compose.yml`** — local/dev. Builds every image from source.
- **`docker-compose.prod.yml`** — production. Pulls prebuilt images from
  GHCR instead of building, and adds `caddy` for automatic HTTPS. The two
  files are intentionally standalone (not a merge overlay) so there's
  never ambiguity about whether a given `up` builds or pulls.
- **`.github/workflows/ci.yml`** — lint, type-check, test, build (already
  existed).
- **`.github/workflows/deploy.yml`** — runs after CI succeeds on `main`:
  builds and pushes `ghcr.io/<owner>/<repo>-{backend,frontend,nginx}` for
  every push, then (only if the SSH secrets below are configured) SSHes
  into the target host and redeploys.

Nothing about the build/push half needs any setup — it works the moment
this repo has commits and a GitHub remote (`GITHUB_TOKEN` is automatic).
The SSH deploy half is opt-in: no secrets configured means the workflow
still builds and pushes images, it just skips the redeploy step. You can
always `docker compose -f docker-compose.prod.yml pull && ... up -d` by
hand on the server instead.

## First-time server setup

1. **Provision a host.** Any VPS with a public IPv4 address and at least
   2 vCPU / 4GB RAM (Postgres + Redis + API + 2 Celery processes + a
   headless Chromium instance during Playwright runs adds up). Ubuntu
   22.04/24.04 LTS is the easiest baseline.

2. **Point DNS at it.** An `A` record for the domain you'll use
   (`flames.example.com`) pointing at the host's IP. Caddy's automatic
   HTTPS needs this to resolve *before* it can issue a certificate.

3. **Install Docker.**
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER   # log out/in after this
   ```

4. **Copy the deployment files to the host** (git clone is simplest if
   the repo is on GitHub; otherwise `scp` these three):
   ```bash
   git clone <this-repo-url> flames && cd flames
   # or, without cloning the whole repo:
   #   scp docker-compose.prod.yml docker/caddy/Caddyfile .env.example <host>:~/flames/
   ```

5. **Create `.env` from `.env.example`.** Fill in real values —
   `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET`,
   `MASTER_ENCRYPTION_KEY` (generate with the command `.env.example`
   documents next to it), Groq/Telegram/Google credentials, and:
   ```bash
   DOMAIN=flames.example.com
   ACME_EMAIL=you@example.com
   IMAGE_NAME=ghcr.io/<owner>/<repo>
   IMAGE_TAG=latest
   CORS_ALLOWED_ORIGINS=https://flames.example.com
   ALLOWED_HOSTS=flames.example.com
   DEBUG=false
   ```
   Never commit this file — it's already in `.gitignore`.

6. **Log in to GHCR** if the package is private (skip if you made it
   public in the repo's package settings):
   ```bash
   echo <a GitHub PAT with read:packages> | docker login ghcr.io -u <username> --password-stdin
   ```

7. **First deploy:**
   ```bash
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d
   docker compose -f docker-compose.prod.yml run --rm api uv run python scripts/seed.py
   ```
   Watch `docker compose -f docker-compose.prod.yml logs -f caddy` on
   first boot — it needs a minute to get the initial certificate.

8. **Verify:**
   - `https://flames.example.com/` — the dashboard.
   - `https://flames.example.com/api/v1/health` — `{"status": "ok"}`.
   - `https://flames.example.com/api/v1/docs` should be **404** — `DEBUG`
     is false in production, so the OpenAPI docs are intentionally off.

## Enabling automatic deploys from CI (optional)

Without this, every update is a manual `pull && up -d` on the host (or
re-run steps 7 above with the new `IMAGE_TAG`). With it, merging to
`main` deploys automatically once CI passes.

In the GitHub repo, **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | the server's IP or hostname |
| `DEPLOY_USER` | the SSH user (the one added to the `docker` group above) |
| `DEPLOY_SSH_KEY` | a private key whose public half is in that user's `~/.ssh/authorized_keys` — generate a dedicated deploy key, never reuse a personal one |
| `DEPLOY_PATH` | absolute path to the directory containing `docker-compose.prod.yml` and `.env` on the host, e.g. `/home/deploy/flames` |

The workflow's deploy job is gated on `DEPLOY_HOST` being set — leave it
unset and CI only ever builds/pushes images, never touches the server.

## Rollback

Every image is tagged with the commit SHA it was built from, not just
`latest`. To roll back:
```bash
IMAGE_TAG=<previous-sha> docker compose -f docker-compose.prod.yml up -d
```

## Backups

Postgres is the only stateful thing that matters (job/application/email
history, feature flags, rules). A daily dump on the host:
```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "flames-$(date +%F).sql.gz"
```
Cron that, and ship the resulting file somewhere off the host (object
storage, another machine) — a backup that lives only on the box it's
backing up isn't a backup.

## Day-to-day operations

- **Logs:** `docker compose -f docker-compose.prod.yml logs -f <service>`
  (all services also write to the `logs` named volume as JSON).
- **Celery monitoring:** Flower stays dev-only by design (see
  `docker-compose.yml`'s comment on it) — for production, `docker compose
  -f docker-compose.prod.yml exec celery_worker uv run celery -A
  app.scheduler.celery_app inspect active` covers the same "what's
  running right now" question without publishing another port.
- **Pausing automation:** `/pause` in Telegram, or toggle
  `enable_playwright`/`enable_auto_apply` etc. from the dashboard's
  Settings page — no redeploy needed, these are DB-backed feature flags.
- **Migrations:** the `migrate` service runs `alembic upgrade head`
  before `api`/`celery_worker`/`celery_beat` start on every `up` — new
  migrations in a release ship automatically, nothing manual.
