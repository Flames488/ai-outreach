"""API-facing read models for jobs.

Distinct from flames_shared.dto.JobPosting (the provider-boundary DTO) and
app.providers.models.StandardJob (the raw provider contract) — this is
what the dashboard actually receives, shaped off the `jobs` DB row
(Part 4 §40).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from flames_shared.enums import JobStatus
from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    title: str
    company_id: uuid.UUID | None
    location: str | None
    country: str | None
    city: str | None
    remote: bool
    employment_type: str | None
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    application_url: str
    ai_score: float | None
    status: JobStatus
    posted_date: datetime | None
    discovered_at: datetime
    client_total_spend: float | None
    client_rating: float | None
    client_payment_verified: bool | None


class JobDetail(JobRead):
    description: str


class JobCreate(BaseModel):
    """For manually-added jobs — freelance-platform gigs (Upwork, Fiverr,
    etc.) that no provider discovers automatically. See docs/architecture.md
    on why there's deliberately no scraping-based path onto these."""

    title: str
    company_name: str | None = None
    provider: str = "manual"
    description: str = ""
    application_url: str
    location: str | None = None
    country: str | None = None
    city: str | None = None
    remote: bool = False
    employment_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    client_total_spend: float | None = None
    client_rating: float | None = None
    client_payment_verified: bool | None = None
