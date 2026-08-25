"""Google Jobs provider — Google has no free public jobs-search API, so
this goes through SerpApi's Google Jobs engine instead (a paid
scraper-as-a-service; SERPAPI_KEY must be set, free tier is small). If
the key isn't configured, `search()` raises rather than silently
returning nothing, so the gap shows up in `provider_logs` instead of
looking like "zero matching jobs".

Response shape (SerpApi's `jobs_results`):
    {"job_id": "...", "title": "...", "company_name": "...",
     "location": "...", "via": "...", "description": "...",
     "detected_extensions": {"posted_at": "...", "schedule_type": "..."},
     "related_links": [{"link": "..."}],
     "apply_options": [{"title": "...", "link": "..."}]}
"""

from __future__ import annotations

import logging

import httpx
from flames_shared.constants import HTTP_REQUEST_TIMEOUT_SECONDS

from app.config.settings import get_settings
from app.providers.base import Provider
from app.providers.models import SearchParams, StandardJob

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"


class GoogleJobsProvider(Provider):
    name = "google_jobs"

    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        settings = get_settings()
        if not settings.serpapi_key:
            raise RuntimeError("SERPAPI_KEY is not configured — Google Jobs is unavailable")

        async with httpx.AsyncClient(timeout=HTTP_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                SERPAPI_URL,
                params={
                    "engine": "google_jobs",
                    "q": params.query
                    or (
                        " OR ".join(params.keywords)
                        if params.keywords
                        else settings.google_jobs_query
                    ),
                    "location": params.location or settings.google_jobs_location,
                    "api_key": settings.serpapi_key,
                },
            )
            response.raise_for_status()
            payload = response.json()

        if "error" in payload:
            raise RuntimeError(f"SerpApi error: {payload['error']}")

        return list(payload.get("jobs_results", []))[: params.limit]

    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        extensions = raw_result.get("detected_extensions")
        extensions = extensions if isinstance(extensions, dict) else {}
        apply_options = raw_result.get("apply_options")
        apply_url = ""
        if isinstance(apply_options, list) and apply_options:
            first = apply_options[0]
            if isinstance(first, dict):
                apply_url = str(first.get("link", ""))

        location = raw_result.get("location")

        return StandardJob(
            id=str(raw_result.get("job_id", "")),
            provider=self.name,
            job_title=str(raw_result.get("title", "")),
            company=str(raw_result.get("company_name", "")),
            location=location if isinstance(location, str) else None,
            salary=None,
            employment_type=extensions.get("schedule_type"),
            experience_level=None,
            description=str(raw_result.get("description", "")),
            skills=[],
            application_url=apply_url,
            company_url=None,
            posted_date=None,
            source_url=apply_url,
            is_remote="remote" in str(location or "").lower(),
            country=None,
            city=None,
        )
