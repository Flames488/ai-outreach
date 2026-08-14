"""Celery signal handlers: JSON logging setup + task_id/execution_time context.

Imported once (as a side effect) from celery_app.py so both the worker and
beat processes get consistent structured logs without each task needing to
touch logging directly.
"""

from __future__ import annotations

import logging
import os
import time

from celery.signals import beat_init, task_failure, task_postrun, task_prerun, worker_process_init

from app.core.logging import clear_log_context, set_log_context, setup_logging

logger = logging.getLogger(__name__)

_task_start_times: dict[str, float] = {}


def _service_name() -> str:
    return os.environ.get("FLAMES_SERVICE_NAME", "celery")


@worker_process_init.connect
def _on_worker_process_init(**kwargs: object) -> None:
    setup_logging(_service_name())


@beat_init.connect
def _on_beat_init(**kwargs: object) -> None:
    setup_logging(_service_name())


@task_prerun.connect
def _on_task_prerun(task_id: str, task: object, **kwargs: object) -> None:
    _task_start_times[task_id] = time.perf_counter()
    set_log_context(task_id=task_id)
    logger.info("Task started: %s", getattr(task, "name", "unknown"))


@task_postrun.connect
def _on_task_postrun(task_id: str, task: object, state: str, **kwargs: object) -> None:
    start = _task_start_times.pop(task_id, None)
    duration_ms = round((time.perf_counter() - start) * 1000, 2) if start is not None else None
    set_log_context(task_id=task_id, duration_ms=duration_ms)
    logger.info("Task finished: %s (%s)", getattr(task, "name", "unknown"), state)
    clear_log_context()


@task_failure.connect
def _on_task_failure(task_id: str, exception: BaseException, **kwargs: object) -> None:
    set_log_context(task_id=task_id)
    logger.error("Task failed: %s", exception, exc_info=exception)
    clear_log_context()
