"""Aggregates every v1 route module under a single router."""

from fastapi import APIRouter

from app.api.v1 import (
    applications,
    auth,
    dashboard,
    emails,
    gmail,
    health,
    jobs,
    rules,
    settings,
    stats,
    telegram,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(rules.router)
api_router.include_router(emails.router)
api_router.include_router(gmail.router)
api_router.include_router(dashboard.router)
api_router.include_router(telegram.router)
api_router.include_router(stats.router)
api_router.include_router(settings.router)
