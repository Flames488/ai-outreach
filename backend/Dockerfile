# Shared image for api, celery_worker, celery_beat, and flower (Phase 2
# §03: "same image as api" for all three) — docker-compose.yml gives each
# service a different `command:`/`environment:` (FLAMES_SERVICE_NAME),
# not a different Dockerfile. Includes the Playwright Chromium binary
# (Phase 3 dry-run engine) since celery_worker is where application-flow
# tasks eventually run — no dedicated Playwright image yet, that's still
# out of scope. Built from the repo root so it can pull in shared/ as a
# uv workspace member (see /pyproject.toml).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml ./
COPY shared/ shared/
COPY backend/ backend/

# uv sync/run must run from backend/, not the workspace root — the root
# pyproject.toml has no dependencies of its own (it only declares the
# workspace members). Running from /app installed just that empty root
# project, so `playwright` (declared in backend/pyproject.toml) never
# made it into .venv and `playwright install` had nothing to invoke.
WORKDIR /app/backend

RUN uv sync
RUN uv run playwright install --with-deps chromium

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
