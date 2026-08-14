"""RemoteOK's HTTP call is mocked at the boundary (Phase 2 §20) — never a
real call in the automated suite.
"""

from __future__ import annotations

import httpx
import respx
from app.providers.models import SearchParams
from app.providers.remoteok import REMOTEOK_API_URL, RemoteOKProvider

_LEGAL_NOTICE = {"legal": "API Terms of Service: ..."}
_JOB = {
    "id": "1136265",
    "slug": "remote-backend-engineer-acme",
    "company": "Acme",
    "position": "Backend Engineer",
    "tags": ["python", "backend"],
    "description": "Build things.",
    "location": "Worldwide",
    "salary_min": 90000,
    "salary_max": 130000,
    "url": "https://remoteok.com/remote-jobs/remote-backend-engineer-acme",
    "apply_url": "https://remoteok.com/remote-jobs/remote-backend-engineer-acme",
    "company_logo": "https://remoteok.com/logo.png",
    "date": "2026-08-06T05:58:01+00:00",
}


@respx.mock
async def test_search_filters_legal_notice_and_normalizes() -> None:
    respx.get(REMOTEOK_API_URL).mock(return_value=httpx.Response(200, json=[_LEGAL_NOTICE, _JOB]))

    provider = RemoteOKProvider()
    jobs = await provider.fetch_jobs(SearchParams(limit=10))

    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "1136265"
    assert job.provider == "remoteok"
    assert job.job_title == "Backend Engineer"
    assert job.company == "Acme"
    assert job.is_remote is True
    assert job.salary_min == 90000
    assert job.salary_max == 130000
    assert job.currency == "USD"
    assert "python" in job.skills


@respx.mock
async def test_search_query_filters_by_position_or_tags() -> None:
    other_job = {**_JOB, "id": "999", "position": "Data Scientist", "tags": ["ml"]}
    respx.get(REMOTEOK_API_URL).mock(
        return_value=httpx.Response(200, json=[_LEGAL_NOTICE, _JOB, other_job])
    )

    provider = RemoteOKProvider()
    raw_results = await provider.search(SearchParams(query="backend", limit=10))

    assert len(raw_results) == 1
    assert raw_results[0]["id"] == "1136265"
