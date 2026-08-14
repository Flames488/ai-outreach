"""Generic company career-page provider (one instance per configured
company site). Search integration lands in a later phase."""

from __future__ import annotations

from app.providers.base import Provider
from app.providers.models import SearchParams, StandardJob


class CompanyCareerProvider(Provider):
    name = "company_career"

    def __init__(self, career_page_url: str) -> None:
        self._career_page_url = career_page_url

    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        raise NotImplementedError(f"{self.name} search is implemented in a later phase")

    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        raise NotImplementedError(f"{self.name} normalize is implemented in a later phase")
