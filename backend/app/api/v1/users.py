"""Current-user profile endpoints (ROADMAP.md's "APIs: User" item)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_user_service_dep
from app.models.user import User
from app.schemas.envelope import SuccessResponse
from app.schemas.user import UserProfileRead, UserProfileUpdate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=SuccessResponse[UserRead])
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service_dep)],
) -> SuccessResponse[UserRead]:
    profile = await user_service.get_profile(user.id)
    data = UserRead.model_validate(user)
    data.profile = UserProfileRead.model_validate(profile) if profile is not None else None
    return SuccessResponse(message="User retrieved successfully.", data=data)


@router.patch("/me", response_model=SuccessResponse[UserRead])
async def update_me(
    body: UserProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service_dep)],
) -> SuccessResponse[UserRead]:
    profile = await user_service.update_profile(user, **body.model_dump(exclude_unset=True))
    data = UserRead.model_validate(user)
    data.profile = UserProfileRead.model_validate(profile)
    return SuccessResponse(message="User profile updated successfully.", data=data)
