"""Liveness (`/health`) and readiness (`/ready`) endpoints — Part 5 §66.

`/health`: the process is alive and can respond — no dependency checks.
`/ready`: DB, Redis, and Celery are all reachable — this is what
docker-compose healthchecks gate dependent services on (a service can be
alive during migrations but not yet ready to serve traffic).
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from flames_shared.enums import ErrorCode
from pydantic import BaseModel
from sqlalchemy import text

from app.core.exceptions import FlamesAPIError
from app.core.redis_client import redis_client
from app.database.session import engine
from app.scheduler.celery_app import celery_app
from app.schemas.envelope import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str


class ReadyStatus(BaseModel):
    status: str
    checks: dict[str, bool]


@router.get("/health", response_model=SuccessResponse[HealthStatus])
async def health() -> SuccessResponse[HealthStatus]:
    return SuccessResponse(message="Flames API is alive.", data=HealthStatus(status="ok"))


@router.get("/ready", response_model=SuccessResponse[ReadyStatus])
async def ready() -> SuccessResponse[ReadyStatus]:
    checks = {"database": False, "redis": False, "celery": False}

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("Readiness check: database unreachable")

    try:
        await redis_client.ping()
        checks["redis"] = True
    except Exception:
        logger.exception("Readiness check: redis unreachable")

    try:
        pings = await asyncio.to_thread(celery_app.control.inspect(timeout=1.0).ping)
        checks["celery"] = bool(pings)
    except Exception:
        logger.exception("Readiness check: celery unreachable")

    if not all(checks.values()):
        raise FlamesAPIError(503, ErrorCode.NOT_READY, "Not all dependencies are ready")

    return SuccessResponse(
        message="Flames API is ready.", data=ReadyStatus(status="ready", checks=checks)
    )
