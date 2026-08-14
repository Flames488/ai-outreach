"""Explicit mapping from the provider-facing StandardJob (§25) onto the
cross-service JobPosting DTO (flames_shared) that AI scoring, application
records, and notifications already depend on.

Keeping this mapping explicit and in one place is what §25 asks for:
providers don't need to match the DTO/DB field names, but the translation
must be defined, not assumed. Anything StandardJob carries that JobPosting
has no dedicated field for lands in JobPosting.raw_metadata.
"""

from __future__ import annotations

from flames_shared.dto import JobPosting
from flames_shared.enums import JobSourceType

from app.providers.models import StandardJob

_PROVIDER_NAME_TO_SOURCE_TYPE: dict[str, JobSourceType] = {
    "indeed": JobSourceType.INDEED,
    "google_jobs": JobSourceType.GOOGLE_JOBS,
    "remoteok": JobSourceType.REMOTEOK,
    "wellfound": JobSourceType.WELLFOUND,
    "greenhouse": JobSourceType.GREENHOUSE,
    "lever": JobSourceType.LEVER,
    "company_career": JobSourceType.COMPANY_SITE,
}


def standard_job_to_job_posting(standard_job: StandardJob) -> JobPosting:
    source = _PROVIDER_NAME_TO_SOURCE_TYPE.get(standard_job.provider, JobSourceType.OTHER)
    return JobPosting(
        source=source,
        external_id=standard_job.id,
        title=standard_job.job_title,
        company=standard_job.company,
        location=standard_job.location,
        url=standard_job.application_url,
        description=standard_job.description,
        posted_at=standard_job.posted_date,
        raw_metadata={
            "salary": standard_job.salary,
            "employment_type": standard_job.employment_type,
            "experience_level": standard_job.experience_level,
            "skills": standard_job.skills,
            "company_url": standard_job.company_url,
            "source_url": standard_job.source_url,
            "is_remote": standard_job.is_remote,
            "country": standard_job.country,
            "city": standard_job.city,
            "benefits": standard_job.benefits,
            "visa_sponsorship": standard_job.visa_sponsorship,
            "closing_date": (
                standard_job.closing_date.isoformat() if standard_job.closing_date else None
            ),
            "company_logo": standard_job.company_logo,
            "industry": standard_job.industry,
        },
    )
