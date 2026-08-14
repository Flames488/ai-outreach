"""Shared Redis fixed-window rate limiter — used by the generic API
middleware (`app/middleware/rate_limit.py`), by call sites that need a
stricter, route-specific limit (e.g. `/auth/login`, Phase 2 §07), and by
the AI provider wrapper (Phase 2 §14).
"""

from __future__ import annotations

import logging

from flames_shared.enums import ErrorCode
from redis.exceptions import RedisError

from app.core.exceptions import FlamesAPIError
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


async def enforce_rate_limit(
    key: str,
    max_attempts: int,
    window_seconds: int,
    error_code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED,
    status_code: int = 429,
) -> None:
    """Raises FlamesAPIError once `key` has been hit more than
    `max_attempts` times within `window_seconds`.

    Fails open (allows the request) if Redis itself is unreachable — a
    protective measure shouldn't become a single point of failure that
    takes the whole API down, and this must never be what stands between
    `/health` and a 200 on a Redis blip.
    """
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)
    except RedisError:
        logger.warning("Rate limiter: Redis unreachable, failing open for key %s", key)
        return

    if count > max_attempts:
        raise FlamesAPIError(
            status_code,
            error_code,
            f"Max {max_attempts} requests per {window_seconds}s",
        )
