from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_jobs: int
    new_jobs_today: int
    matched_jobs: int
    pending_review: int
    total_applications: int
    applications_today: int
    queued_applications: int
    unprocessed_emails: int
