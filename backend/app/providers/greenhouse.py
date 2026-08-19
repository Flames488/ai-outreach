"""Greenhouse provider — real, free, no-auth public API, but per-company:
`GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`.
There's no "search all of Greenhouse" endpoint, so this polls a
configured list of company board tokens (`settings.greenhouse_companies`)
rather than doing a keyword search — the token is the slug in
`boards.greenhouse.io/<token>`.

One company's board failing (wrong/renamed token, timeout) never aborts
the others — each is fetched independently and logged.

Response shape per job:
    {"id": 123, "title": "...", "absolute_url": "...", "company_name": "...",
     "location": {"name": "Remote"}, "content": "<html>...", "updated_at": "..."}
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import httpx
from flames_shared.constants import HTTP_REQUEST_TIMEOUT_SECONDS

from app.config.settings import get_settings
from app.providers.base import Provider
from app.providers.models import SearchParams, StandardJob

logger = logging.getLogger(__name__)

GREENHOUSE_API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
_TAG_RE = re.compile(r"<[^>]+>")


class GreenhouseProvider(Provider):
    name = "greenhouse"

    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        companies = get_settings().greenhouse_companies_list
        if not companies:
            return []

        # Per-company share of the limit, not a global cap applied after
        # aggregating — otherwise one large board (e.g. 100+ open roles)
        # crowds out every other configured company entirely.
        per_company_limit = max(10, params.limit // len(companies))

        postings: list[dict[str, object]] = []
        async with httpx.AsyncClient(timeout=HTTP_REQUEST_TIMEOUT_SECONDS) as client:
            for token in companies:
                try:
                    response = await client.get(
                        GREENHOUSE_API_URL.format(token=token), params={"content": "true"}
                    )
                    response.raise_for_status()
                    jobs = response.json().get("jobs", [])
                    for job in jobs[:per_company_limit]:
                        job["_board_token"] = token
                        postings.append(job)
                except Exception:
                    logger.warning("Greenhouse board %r failed; skipping it", token, exc_info=True)

        if params.query:
            query_lower = params.query.lower()
            postings = [p for p in postings if query_lower in str(p.get("title", "")).lower()]

        return postings

    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        location = raw_result.get("location")
        location_name = location.get("name") if isinstance(location, dict) else None
        content = str(raw_result.get("content", ""))

        return StandardJob(
            id=str(raw_result["id"]),
            provider=self.name,
            job_title=str(raw_result.get("title", "")),
            company=str(raw_result.get("company_name") or raw_result.get("_board_token", "")),
            location=location_name,
            salary=None,
            employment_type=None,
            experience_level=None,
            description=_TAG_RE.sub(" ", content).strip(),
            skills=[],
            application_url=str(raw_result.get("absolute_url", "")),
            company_url=None,
            posted_date=_parse_date(raw_result.get("updated_at")),
            source_url=str(raw_result.get("absolute_url", "")),
            is_remote="remote" in (location_name or "").lower(),
            country=None,
            city=None,
        )


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
