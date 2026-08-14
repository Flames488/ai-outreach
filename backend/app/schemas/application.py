"""API-facing read models for applications, shaped off the `applications`
DB row (Part 4 §41)."""

from __future__ import annotations

import uuid
from datetime import datetime

from flames_shared.enums import ApplicationStatus
from pydantic import BaseModel, ConfigDict


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    application_status: ApplicationStatus
    error_message: str | None
    retry_count: int
    submitted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID


class TimelineEvent(BaseModel):
    action: str
    old_value: dict | None
    new_value: dict | None
    created_at: datetime


class ApplicationDetail(ApplicationRead):
    timeline: list[TimelineEvent] = []
