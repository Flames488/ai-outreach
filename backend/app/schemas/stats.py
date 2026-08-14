"""Dashboard summary statistics.

Jobs and applications carry independent status enums (Part 4 §40/§41 — a
job can be SKIPPED with no application ever attempted), so the dashboard
reports both breakdowns rather than one combined applied/skipped/failed
count.
"""

from __future__ import annotations

from pydantic import BaseModel


class JobStatusCounts(BaseModel):
    new: int
    matched: int
    review: int
    applied: int
    failed: int
    skipped: int
    expired: int


class ApplicationStatusCounts(BaseModel):
    pending: int
    running: int
    success: int
    failed: int
    review_required: int
    cancelled: int


class DashboardStats(BaseModel):
    total_jobs_discovered: int
    jobs_by_status: JobStatusCounts
    total_applications: int
    applications_by_status: ApplicationStatusCounts
