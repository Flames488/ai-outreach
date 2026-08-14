"""Redis lock preventing overlapping runs of the same scheduled task
(Phase 2 §18) — beat can, in edge cases (worker restart, clock skew),
trigger a task while a previous run is still in flight.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def task_lock(task_name: str, ttl_seconds: int) -> AsyncIterator[bool]:
    """Yields True if the lock was acquired (caller should proceed), False
    if another run is already in flight (caller should skip)."""
    key = f"tasklock:{task_name}"
    acquired = await redis_client.set(key, "1", nx=True, ex=ttl_seconds)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            await redis_client.delete(key)
