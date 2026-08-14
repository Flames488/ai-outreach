"""Retry transient failures with exponential backoff (Part 3 §30).

One implementation, used by every service that calls an external API
(providers, AI, Gmail, Telegram) — never re-implemented per call site.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retries a transient failure up to `max_attempts` times, waiting
    `base_delay_seconds * 2**attempt` between attempts. Re-raises the last
    exception once attempts are exhausted — callers still need their own
    "continue with the rest of the batch" handling around this."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last_exception: BaseException | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts - 1:
                        break
                    delay = base_delay_seconds * (2**attempt)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__qualname__,
                        attempt + 1,
                        max_attempts,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
            assert last_exception is not None
            raise last_exception

        return wrapper

    return decorator
