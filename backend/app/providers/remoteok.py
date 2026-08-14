"""RemoteOK provider — the one working end-to-end integration for Phase 2
(Phase 2 §13: "pick the one with the simplest public API"). RemoteOK's
JSON feed needs no auth: GET https://remoteok.com/api.

Response shape: a JSON array whose first element is a legal notice
(no `id` key) followed by job postings shaped like:

    {"id": "...", "slug": "...", "company": "...", "position": "...",
     "tags": [...], "description": "<html>...", "location": "...",
     "salary_min": 0, "salary_max": 0, "url": "...", "apply_url": "...",
     "company_logo": "...", "date": "2026-08-06T05:58:01+00:00"}
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from flames_shared.constants import HTTP_REQUEST_TIMEOUT_SECONDS

from app.providers.base import Provider
from app.providers.models import SearchParams, StandardJob

logger = logging.getLogger(__name__)

REMOTEOK_API_URL = "https://remoteok.com/api"
# RemoteOK blocks the default httpx/requests UA; a descriptive UA per
# their API Terms of Service is expected of API consumers.
REMOTEOK_USER_AGENT = "FlamesJobBot/1.0 (+https://github.com/)"


class RemoteOKProvider(Provider):
    name = "remoteok"

    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        async with httpx.AsyncClient(timeout=HTTP_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                REMOTEOK_API_URL, headers={"User-Agent": REMOTEOK_USER_AGENT}
            )
            response.raise_for_status()
            payload = response.json()

        # First element is RemoteOK's API legal notice, not a job.
        postings = [item for item in payload if isinstance(item, dict) and "id" in item]

        if params.query:
            query_lower = params.query.lower()
            postings = [
                item
                for item in postings
                if query_lower in str(item.get("position", "")).lower()
                or query_lower in " ".join(item.get("tags", [])).lower()
            ]

        return postings[: params.limit]

    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        posted_date = _parse_date(raw_result.get("date"))
        salary_min = raw_result.get("salary_min") or None
        salary_max = raw_result.get("salary_max") or None
        salary = f"${salary_min:,.0f}-${salary_max:,.0f}" if salary_min and salary_max else None

        return StandardJob(
            id=str(raw_result["id"]),
            provider=self.name,
            job_title=str(raw_result.get("position", "")),
            company=str(raw_result.get("company", "")),
            location=raw_result.get("location") or None,
            salary=salary,
            employment_type=None,
            experience_level=None,
            description=str(raw_result.get("description", "")),
            skills=list(raw_result.get("tags", [])),
            application_url=str(raw_result.get("apply_url") or raw_result.get("url", "")),
            company_url=None,
            posted_date=posted_date,
            source_url=str(raw_result.get("url", "")),
            is_remote=True,
            country=None,
            city=None,
            company_logo=raw_result.get("company_logo") or raw_result.get("logo") or None,
            salary_min=float(salary_min) if salary_min else None,
            salary_max=float(salary_max) if salary_max else None,
            currency="USD" if salary_min or salary_max else None,
        )


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning("RemoteOK: unparseable date %r", value)
        return None
