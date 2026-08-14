"""Per-request logging context: request ID + timing.

Deliberately logs only method/path/status/duration — never headers, query
strings, or the body, so an Authorization header or token can never end up
in a log line (Part 3 §32: never log passwords, OAuth tokens, cookies,
authorization headers).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import clear_log_context, set_log_context

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        set_log_context(request_id=request_id)
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={"duration_ms": duration_ms},
        )
        clear_log_context()
        response.headers["X-Request-ID"] = request_id
        return response
