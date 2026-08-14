"""API-facing schemas for the current user's profile (ROADMAP.md's
"APIs: User" item)."""

from __future__ import annotations

import uuid

from flames_shared.enums import UserRole
from pydantic import BaseModel, ConfigDict


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str | None
    phone: str | None
    country: str | None
    city: str | None
    years_of_experience: int | None
    current_position: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    work_authorization: str | None
    visa_sponsorship_needed: bool | None
    expected_salary: float | None
    notice_period: str | None
    education: list | None
    certifications: list | None
    languages: list | None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    role: UserRole
    telegram_chat_id: str | None
    gmail_connected: bool
    profile: UserProfileRead | None = None


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    country: str | None = None
    city: str | None = None
    years_of_experience: int | None = None
    current_position: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    work_authorization: str | None = None
    visa_sponsorship_needed: bool | None = None
    expected_salary: float | None = None
    notice_period: str | None = None
    education: list | None = None
    certifications: list | None = None
    languages: list | None = None
