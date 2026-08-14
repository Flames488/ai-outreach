from app.providers.mapping import standard_job_to_job_posting
from app.providers.models import StandardJob
from flames_shared.enums import JobSourceType


def _standard_job(**overrides: object) -> StandardJob:
    defaults: dict[str, object] = {
        "id": "123",
        "provider": "greenhouse",
        "job_title": "Backend Engineer",
        "company": "Acme",
        "location": "Remote",
        "salary": "$120k-$150k",
        "employment_type": "full_time",
        "experience_level": "mid",
        "description": "Build things.",
        "skills": ["python", "sql"],
        "application_url": "https://boards.greenhouse.io/acme/jobs/123",
        "company_url": "https://acme.example",
        "posted_date": None,
        "source_url": "https://boards.greenhouse.io/acme/jobs/123",
        "is_remote": True,
        "country": "US",
        "city": None,
    }
    defaults.update(overrides)
    return StandardJob(**defaults)


def test_maps_known_provider_to_source_type() -> None:
    posting = standard_job_to_job_posting(_standard_job())

    assert posting.source == JobSourceType.GREENHOUSE
    assert posting.external_id == "123"
    assert posting.title == "Backend Engineer"
    assert posting.url == "https://boards.greenhouse.io/acme/jobs/123"
    assert posting.raw_metadata["salary"] == "$120k-$150k"
    assert posting.raw_metadata["skills"] == ["python", "sql"]


def test_unknown_provider_falls_back_to_other() -> None:
    posting = standard_job_to_job_posting(_standard_job(provider="some_new_source"))

    assert posting.source == JobSourceType.OTHER
