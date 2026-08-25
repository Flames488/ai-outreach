"""API-facing schemas for the current user's profile (ROADMAP.md's
"APIs: User" item)."""

from __future__ import annotations

import uuid
from typing import Any

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
    education: list[Any] | None
    certifications: list[Any] | None
    languages: list[Any] | None
    professional_summary: str | None
    skills: list[Any] | None
    desired_titles: list[Any] | None
    notable_projects: list[Any] | None


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
    education: list[Any] | None = None
    certifications: list[Any] | None = None
    languages: list[Any] | None = None
    professional_summary: str | None = None
    skills: list[Any] | None = None
    desired_titles: list[Any] | None = None
    notable_projects: list[Any] | None = None
