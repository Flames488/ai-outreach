"""Wraps a task body so every scheduled run gets a `scheduled_tasks` row
automatically (Phase 2 §18) — task functions never write this bookkeeping
by hand.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from app.database.session import session_scope
from app.repositories.scheduled_task_repository import ScheduledTaskRepository

logger = logging.getLogger(__name__)

T = TypeVar("T")


def track_scheduled_task(
    task_name: str, worker: str = "celery_worker"
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            start = time.perf_counter()

            async with session_scope() as db:
                repo = ScheduledTaskRepository(db)
                record = await repo.create(
                    task_name=task_name,
                    started_at=datetime.now(UTC),
                    status="running",
                    worker=worker,
                )
                await db.commit()
                record_id = record.id

            status = "success"
            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "failed"
                logger.exception("Scheduled task %s failed", task_name)
                raise
            finally:
                duration = time.perf_counter() - start
                async with session_scope() as db:
                    repo = ScheduledTaskRepository(db)
                    await repo.update(
                        record_id,
                        completed_at=datetime.now(UTC),
                        status=status,
                        duration=duration,
                    )
                    await db.commit()

        return wrapper

    return decorator
