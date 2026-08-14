"""Aggregate dashboard summary (Phase 2 §11) — served from the API even
though the dashboard UI itself is a later phase.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_dashboard_service_dep
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.schemas.envelope import SuccessResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=SuccessResponse[DashboardSummary])
async def get_dashboard(
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service_dep)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[DashboardSummary]:
    summary = await dashboard_service.get_summary()
    return SuccessResponse(message="Dashboard summary retrieved successfully.", data=summary)
