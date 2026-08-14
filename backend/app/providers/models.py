"""The Standard Job Model (Part 3 §25).

Every provider returns exactly this shape — it's what makes the AI engine
and (eventually) the DB schema provider-agnostic. "Required" fields are
always present as attributes, even when the source doesn't disclose the
value (e.g. `salary=None` is valid; omitting `salary` entirely is not) —
that distinction is deliberate: a provider must say "unknown" rather than
silently drop the field.

Field-name reconciliation with the `jobs` DB table (`title`/`company_id`
etc.) happens explicitly in Part 4 — this model is the provider-facing
contract, not the DB row; the two don't need identical field names, but
the mapping between them will be defined in the repository layer once
Part 4 lands.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchParams(BaseModel):
    """Search criteria passed to `Provider.search()` (Phase 2 §13)."""

    query: str | None = None
    location: str | None = None
    remote_only: bool = False
    limit: int = Field(default=50, ge=1, le=500)


class StandardJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    # ---- Required (always present; value may be None if undisclosed) ----
    id: str
    provider: str
    job_title: str
    company: str
    location: str | None
    salary: str | None
    employment_type: str | None
    experience_level: str | None
    description: str
    skills: list[str]
    application_url: str
    company_url: str | None
    posted_date: datetime | None
    source_url: str
    is_remote: bool
    country: str | None
    city: str | None

    # ---- Optional ----
    benefits: list[str] | None = None
    visa_sponsorship: bool | None = None
    closing_date: datetime | None = None
    company_logo: str | None = None
    industry: str | None = None
    # Structured salary, when the source provides it — `salary` above stays
    # the free-text display string either way. JobIngestionService prefers
    # these over parsing `salary` when mapping onto jobs.salary_min/_max.
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None


# Phase 2 §13 calls this contract `NormalizedJob` — same shape, same
# object. Kept as an alias rather than a rename so existing wiring
# (mapping.py, tests) doesn't churn for a naming preference.
NormalizedJob = StandardJob
