"""Shared async Redis client — used for health checks today, and for
caching / rate limiting in later phases (see infra philosophy: Redis is
"Celery broker, caching, temporary session storage, rate limiting")."""

from __future__ import annotations

from redis.asyncio import Redis

from app.config.settings import get_settings

settings = get_settings()

redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
