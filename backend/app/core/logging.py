"""Central logging configuration — every service logs structured JSON.

Every entrypoint (api, celery_worker, celery_beat, flower) calls
setup_logging(service_name) once at startup so log format and destination
stay consistent across containers. Per-record context (request_id, user_id,
task_id, duration_ms) is threaded through via contextvars set by the
FastAPI middleware (app/main.py) and the Celery signal handlers
(app/scheduler/logging_signals.py) — LogContextFilter copies whatever is
currently set onto every record emitted while that context is active.

A regex-based scrubbing safety net (Phase 2 §19) redacts known-sensitive
field names in every log line — passwords, tokens, secrets, the
Authorization header — so a developer accidentally logging a credential
doesn't leak it, without relying solely on remembering not to.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config.settings import get_settings

LOG_DIR = Path("/app/logs")

_SENSITIVE_FIELD_PATTERN = re.compile(
    r'(?i)\b(password|token|secret|authorization|api[_-]?key)\b(["\']?\s*[:=]\s*["\']?)'
    r"([^\"'\s,}]+)"
)


def scrub_sensitive_text(text: str) -> str:
    """Redacts the value half of any `password=...`, `"token": "..."`,
    `Authorization: Bearer ...`-shaped substring. Best-effort, not a
    substitute for simply not logging secrets in the first place — see
    the module docstring."""
    return _SENSITIVE_FIELD_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}***REDACTED***", text)


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_task_id: ContextVar[str | None] = ContextVar("task_id", default=None)
_duration_ms: ContextVar[float | None] = ContextVar("duration_ms", default=None)

_CONTEXT_VARS: dict[str, ContextVar[Any]] = {
    "request_id": _request_id,
    "user_id": _user_id,
    "task_id": _task_id,
    "duration_ms": _duration_ms,
}


def set_log_context(**kwargs: Any) -> None:
    for key, value in kwargs.items():
        _CONTEXT_VARS[key].set(value)


def clear_log_context(*keys: str) -> None:
    for key in keys or tuple(_CONTEXT_VARS):
        _CONTEXT_VARS[key].set(None)


class LogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, var in _CONTEXT_VARS.items():
            value = var.get()
            if value is not None:
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "service": self._service_name,
            "logger": record.name,
            "message": scrub_sensitive_text(record.getMessage()),
        }
        for key in _CONTEXT_VARS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = scrub_sensitive_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


def setup_logging(service_name: str) -> None:
    settings = get_settings()
    log_dir = Path(settings.log_dir) if settings.log_dir else LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = JsonFormatter(service_name)
    context_filter = LogContextFilter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)

    file_handler = logging.FileHandler(log_dir / f"{service_name}.log")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)

    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(level=level, handlers=[stream_handler, file_handler], force=True)
