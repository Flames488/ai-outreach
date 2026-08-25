"""Lever provider — real, free, no-auth public API, but per-company like
Greenhouse: `GET https://api.lever.co/v0/postings/{token}?mode=json`. No
generic search endpoint exists, so this polls a configured list of
company tokens (`settings.lever_companies`) — the slug in
`jobs.lever.co/<token>`.

One company's board failing never aborts the others.

Response shape per posting:
    {"id": "...", "text": "title", "hostedUrl": "...", "applyUrl": "...",
     "categories": {"location": "...", "team": "...", "commitment": "..."},
     "descriptionPlain": "...", "createdAt": 1699999999000}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from flames_shared.constants import HTTP_REQUEST_TIMEOUT_SECONDS

from app.config.settings import get_settings
from app.providers.base import Provider
from app.providers.models import SearchParams, StandardJob

logger = logging.getLogger(__name__)

LEVER_API_URL = "https://api.lever.co/v0/postings/{token}"


class LeverProvider(Provider):
    name = "lever"

    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        companies = get_settings().lever_companies_list
        if not companies:
            return []

        per_company_limit = max(10, params.limit // len(companies))

        postings: list[dict[str, object]] = []
        async with httpx.AsyncClient(timeout=HTTP_REQUEST_TIMEOUT_SECONDS) as client:
            for token in companies:
                try:
                    # Lever's `limit` is server-side — without it, a large
                    # board (e.g. thousands of postings, each carrying a
                    # full HTML/plain-text description) returns a multi-MB
                    # response that takes 20s+ just to download, discovered
                    # by an actual hang while testing this against palantir's
                    # real board (5.9MB down to ~325KB with limit=15).
                    response = await client.get(
                        LEVER_API_URL.format(token=token),
                        params={"mode": "json", "limit": per_company_limit},
                    )
                    response.raise_for_status()
                    for job in response.json():
                        job["_board_token"] = token
                        postings.append(job)
                except Exception:
                    logger.warning("Lever board %r failed; skipping it", token, exc_info=True)

        terms = [t.lower() for t in params.keywords] or (
            [params.query.lower()] if params.query else []
        )
        if terms:
            postings = [
                p for p in postings if any(term in str(p.get("text", "")).lower() for term in terms)
            ]

        return postings

    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        categories = raw_result.get("categories")
        categories = categories if isinstance(categories, dict) else {}
        location = categories.get("location")

        return StandardJob(
            id=str(raw_result["id"]),
            provider=self.name,
            job_title=str(raw_result.get("text", "")),
            company=str(raw_result.get("_board_token", "")).replace("-", " ").title(),
            location=location,
            salary=None,
            employment_type=categories.get("commitment"),
            experience_level=None,
            description=str(raw_result.get("descriptionPlain", "")),
            skills=[],
            application_url=str(raw_result.get("applyUrl") or raw_result.get("hostedUrl", "")),
            company_url=None,
            posted_date=_parse_epoch_ms(raw_result.get("createdAt")),
            source_url=str(raw_result.get("hostedUrl", "")),
            is_remote="remote" in (location or "").lower(),
            country=None,
            city=None,
        )


def _parse_epoch_ms(value: object) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (ValueError, OSError, OverflowError):
        return None
