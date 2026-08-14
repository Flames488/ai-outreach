"""Wellfound (AngelList Talent) provider. Search integration lands in a later phase."""

from __future__ import annotations

from app.providers.base import Provider
from app.providers.models import SearchParams, StandardJob


class WellfoundProvider(Provider):
    name = "wellfound"

    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        raise NotImplementedError(f"{self.name} search is implemented in a later phase")

    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        raise NotImplementedError(f"{self.name} normalize is implemented in a later phase")
