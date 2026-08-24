"""Shared pytest fixtures.

Sets required infra secrets before anything imports app.config.settings,
so `pytest` is self-contained (no .env file needed) regardless of which
directory it's run from — Settings() fails fast on missing secrets at
import time (app/main.py reads them for TrustedHostMiddleware).
"""

from __future__ import annotations

import base64
import os

for _key, _value in {
    "SECRET_KEY": "test-secret-key",
    "JWT_SECRET": "test-jwt-secret",
    "POSTGRES_PASSWORD": "test-postgres-password",
    # Must be a real Fernet key (32 url-safe base64 bytes) — Settings
    # validates the format at load time, not just presence.
    "MASTER_ENCRYPTION_KEY": base64.urlsafe_b64encode(b"0" * 32).decode(),
    "SEED_ADMIN_PASSWORD": "test-seed-admin-password",
    # Settings.log_dir defaults to /app/logs (correct inside the Docker
    # image); setup_logging() mkdir's it on app startup, which fails with
    # PermissionError on any host where /app isn't already a writable,
    # pre-existing directory (e.g. a GitHub Actions runner, or a non-root
    # local dev machine).
    "LOG_DIR": "/tmp/flames-test-logs",
}.items():
    os.environ.setdefault(_key, _value)

import pytest  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
