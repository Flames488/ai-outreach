"""Shared pytest fixtures.

Sets required infra secrets before anything imports app.config.settings,
so `pytest` is self-contained (no .env file needed) regardless of which
directory it's run from — Settings() fails fast on missing secrets at
import time (app/main.py reads them for TrustedHostMiddleware).
"""

from __future__ import annotations

import base64
import os
import tempfile

for _key, _value in {
    "SECRET_KEY": "test-secret-key",
    "JWT_SECRET": "test-jwt-secret",
    "POSTGRES_PASSWORD": "test-postgres-password",
    # Must be a real Fernet key (32 url-safe base64 bytes) — Settings
    # validates the format at load time, not just presence.
    "MASTER_ENCRYPTION_KEY": base64.urlsafe_b64encode(b"0" * 32).decode(),
    "SEED_ADMIN_PASSWORD": "test-seed-admin-password",
    # Default is "/app/logs" (the Docker container's WORKDIR) — the
    # `client` fixture entering TestClient as a context manager triggers
    # the real FastAPI lifespan, which calls setup_logging() and tries to
    # mkdir this, so it must point somewhere writable outside a container.
    "LOG_DIR": os.path.join(tempfile.gettempdir(), "flames-test-logs"),
}.items():
    os.environ.setdefault(_key, _value)

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Session-scoped and entered as a context manager so every request
    across the whole test run shares one event loop (matching a real
    uvicorn process, which has exactly one for its lifetime). Without
    this, TestClient opens a fresh event loop per un-scoped call, and
    module-level async clients like `app.core.redis_client.redis_client`
    (whose connection binds to whichever loop is active when first used)
    break with "got Future attached to a different loop" the moment two
    tests hit it via different loops."""
    with TestClient(app) as test_client:
        yield test_client
