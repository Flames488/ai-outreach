"""Runtime settings: feature flags (DB-backed, editable) and read-only
boot-time thresholds. `GET /settings` / `POST /settings` per Phase 2 §11.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_settings_service_dep
from app.database.session import get_db
from app.models.user import User
from app.schemas.envelope import SuccessResponse
from app.services.feature_flag_service import FeatureFlagService, get_feature_flag_service
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


class FeatureFlags(BaseModel):
    enable_playwright: bool
    enable_gmail: bool
    enable_telegram: bool
    enable_ai_scoring: bool
    enable_auto_apply: bool
    enable_dashboard: bool
    enable_screenshots: bool
    enable_resume_generator: bool
    enable_interview_preparation: bool


class SettingsRead(BaseModel):
    job_match_threshold: int
    job_search_max_results: int
    feature_flags: FeatureFlags


class FeatureFlagUpdate(BaseModel):
    key: str
    enabled: bool


def get_feature_flag_service_dep(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureFlagService:
    return get_feature_flag_service(db)


@router.get("", response_model=SuccessResponse[SettingsRead])
async def get_settings_route(
    _: Annotated[User, Depends(get_current_user)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service_dep)],
    feature_flags: Annotated[FeatureFlagService, Depends(get_feature_flag_service_dep)],
) -> SuccessResponse[SettingsRead]:
    flags = await feature_flags.get_all()
    data = SettingsRead(
        job_match_threshold=settings_service.get("job_match_threshold"),
        job_search_max_results=settings_service.get("job_search_max_results"),
        feature_flags=FeatureFlags(**flags),
    )
    return SuccessResponse(message="Settings retrieved successfully.", data=data)


@router.post("", response_model=SuccessResponse[dict])
async def update_settings_route(
    body: FeatureFlagUpdate,
    _: Annotated[User, Depends(get_current_user)],
    feature_flags: Annotated[FeatureFlagService, Depends(get_feature_flag_service_dep)],
) -> SuccessResponse[dict]:
    """Updates one feature flag. Scheduling times remain boot-time only
    this phase (Phase 2 §18: "requires a config change and worker
    restart... fully dynamic rescheduling is a nice-to-have, not required
    for this phase")."""
    await feature_flags.set(body.key, body.enabled)
    return SuccessResponse(message="Setting updated successfully.", data={})
