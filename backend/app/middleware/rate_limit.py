"""Redis-backed fixed-window rate limiting (Phase 2 §04/§65).

Deliberately simple — a fixed window per client IP per path, just enough
that a runaway client (or bug) can't hammer the API unbounded. Raises
`FlamesAPIError`, caught by the same global handler as everything else
(`app/main.py`) so the 429 still comes back through the standard envelope.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.rate_limit import enforce_rate_limit

RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        await enforce_rate_limit(
            key=f"ratelimit:{client_ip}:{request.url.path}",
            max_attempts=RATE_LIMIT_REQUESTS,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        return await call_next(request)
