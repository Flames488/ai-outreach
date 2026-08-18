"""Shared FastAPI dependencies.

Includes the service-layer providers every route depends on — routes never
construct a repository or session themselves (Part 3 §21).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from flames_shared.enums import ErrorCode, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.core.exceptions import FlamesAPIError
from app.core.logging import set_log_context
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.application_service import ApplicationService, get_application_service
from app.services.dashboard_service import DashboardService, get_dashboard_service
from app.services.email_service import EmailService, get_email_service
from app.services.job_ingestion_service import JobIngestionService, get_job_ingestion_service
from app.services.job_service import JobService, get_job_service
from app.services.rule_engine_service import RuleEngineService, get_rule_engine_service
from app.services.settings_service import SettingsService, get_settings_service
from app.services.user_service import UserService, get_user_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "Invalid or expired token")

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "Invalid or expired token")

    user = await UserRepository(db).get(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise FlamesAPIError(401, ErrorCode.AUTH_INVALID_TOKEN, "Invalid or expired token")

    set_log_context(user_id=str(user.id))
    return user


def require_role(role: UserRole) -> Callable[[User], User]:
    """Route dependency: `Depends(require_role(UserRole.ADMIN))`. Only a
    route-level gate — services that could be reached from more than one
    entry point (API and Telegram) enforce the same rule themselves too
    (Phase 2 §07), since a route dependency doesn't protect a Telegram
    command handler calling the same service."""

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role != role and user.role != UserRole.ADMIN:
            raise FlamesAPIError(403, ErrorCode.AUTH_FORBIDDEN, "Insufficient permissions")
        return user

    return dependency


def get_job_service_dep(db: Annotated[AsyncSession, Depends(get_db)]) -> JobService:
    return get_job_service(db)


def get_job_ingestion_service_dep(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobIngestionService:
    return get_job_ingestion_service(db)


def get_application_service_dep(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationService:
    return get_application_service(db)


def get_rule_engine_service_dep(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RuleEngineService:
    return get_rule_engine_service(db)


def get_email_service_dep(db: Annotated[AsyncSession, Depends(get_db)]) -> EmailService:
    return get_email_service(db)


def get_dashboard_service_dep(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    return get_dashboard_service(db)


def get_user_service_dep(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
    return get_user_service(db)


def get_settings_service_dep() -> SettingsService:
    return get_settings_service()
