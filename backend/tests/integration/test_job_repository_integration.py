"""Integration tests: repositories/services against a real Postgres.

Phase 2 Testing spec (`20-Testing.md`): "Repositories and Services against
a real (disposable, Dockerized) test Postgres + Redis... mocking the DB
for these tests would defeat their purpose." In CI, the `test` job runs
`alembic upgrade head` against a Postgres service container before
`pytest` for exactly this reason. Locally, point DATABASE_URL at any
migrated Postgres — these tests skip themselves (not fail) when no
database is reachable, so a plain `pytest` still passes on a machine
without Postgres running.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from app.config.settings import get_settings
from app.providers.models import StandardJob
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_skill_repository import JobSkillRepository
from app.services.job_ingestion_service import JobIngestionService
from flames_shared.enums import JobStatus
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # A dedicated NullPool engine per test, not the app's shared
    # module-level engine — pytest-asyncio gives every test its own event
    # loop, and a pooled asyncpg connection checked out under one loop
    # can't be reused under the next (raises/hangs), which without
    # NullPool showed up as this fixture's reachability probe spuriously
    # failing on the second integration test in a run.
    test_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with test_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await test_engine.dispose()
        pytest.skip("No reachable, migrated Postgres — set DATABASE_URL to run integration tests.")

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


def _standard_job(external_id: str, company: str) -> StandardJob:
    return StandardJob(
        id=external_id,
        provider="integration-test",
        job_title="Integration Test Engineer",
        company=company,
        location="Remote",
        salary=None,
        employment_type="full_time",
        experience_level="mid",
        description="Exercises the real ingestion round trip against Postgres.",
        skills=["python", "sql"],
        application_url="https://example.com/apply",
        company_url=None,
        posted_date=None,
        source_url="https://example.com/job",
        is_remote=True,
        country="US",
        city=None,
    )


async def test_job_ingestion_round_trip_dedupes_against_real_db(
    db_session: AsyncSession,
) -> None:
    """Verifies the provider+external_id uniqueness/idempotency guarantee
    (Phase 1 Part 9 §127) actually holds via real SQL, not a mock."""
    external_id = f"itest-{uuid.uuid4()}"
    company_name = f"Acme Test Co {uuid.uuid4()}"
    service = JobIngestionService(
        db=db_session,
        jobs=JobRepository(db_session),
        companies=CompanyRepository(db_session),
        job_skills=JobSkillRepository(db_session),
    )

    try:
        first = await service.ingest(_standard_job(external_id, company_name))
        second = await service.ingest(_standard_job(external_id, company_name))

        assert first.id == second.id

        count = await JobRepository(db_session).count(
            provider="integration-test", external_job_id=external_id
        )
        assert count == 1
    finally:
        await db_session.execute(
            text(
                "DELETE FROM job_skills WHERE job_id IN "
                "(SELECT id FROM jobs WHERE external_job_id = :ext)"
            ),
            {"ext": external_id},
        )
        await db_session.execute(
            text("DELETE FROM jobs WHERE external_job_id = :ext"), {"ext": external_id}
        )
        await db_session.execute(
            text("DELETE FROM companies WHERE company_name = :name"), {"name": company_name}
        )
        await db_session.commit()


async def test_soft_delete_excludes_row_from_repository_reads(
    db_session: AsyncSession,
) -> None:
    """Verifies BaseRepository's `deleted_at IS NULL` filter against real
    SQL — a mocked session would trivially "pass" this without the filter
    actually being wired into the query."""
    jobs = JobRepository(db_session)
    external_id = f"itest-sd-{uuid.uuid4()}"
    job = await jobs.create(
        provider="integration-test",
        external_job_id=external_id,
        title="Soft Delete Probe",
        description="...",
        application_url="https://example.com/apply",
        remote=True,
        status=JobStatus.NEW,
        discovered_at=datetime.now(UTC),
    )
    await db_session.commit()

    try:
        assert await jobs.get(job.id) is not None

        await jobs.soft_delete(job.id)
        await db_session.commit()

        assert await jobs.get(job.id) is None
    finally:
        await db_session.execute(text("DELETE FROM jobs WHERE id = :id"), {"id": job.id})
        await db_session.commit()
