from app.services.job_service import JobService
from flames_shared.dto import JobPosting
from flames_shared.enums import JobSourceType


def _job(external_id: str) -> JobPosting:
    return JobPosting(
        source=JobSourceType.LINKEDIN,
        external_id=external_id,
        title="Backend Engineer",
        company="Acme",
        url="https://example.com/job",
        description="...",
    )


async def test_deduplicate_drops_repeated_fingerprints() -> None:
    # deduplicate() is pure data logic and doesn't touch the DB, so no
    # session/repository/ingestion wiring is needed for this test.
    service = JobService(db=None, repository=None, ingestion=None, provider_logs=None)  # type: ignore[arg-type]
    jobs = [_job("1"), _job("2"), _job("1")]

    result = await service.deduplicate(jobs)

    assert [job.external_id for job in result] == ["1", "2"]
