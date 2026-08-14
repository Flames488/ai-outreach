"""Provider contract: Search() -> Normalize() -> Return Jobs (Phase 2 §13).

Every job source (Indeed, Greenhouse, a company career page, ...) is a
`Provider` subclass. `job_service.py` (the only caller) iterates every
enabled provider and calls `fetch_jobs()` — it never needs to know how any
individual source works, and adding/removing a source never touches
anything outside this package.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from app.providers.models import SearchParams, StandardJob


class Provider(ABC):
    name: ClassVar[str]

    @abstractmethod
    async def search(self, params: SearchParams) -> list[dict[str, object]]:
        """Query the source. Returns raw, source-shaped results."""

    @abstractmethod
    def normalize(self, raw_result: dict[str, object]) -> StandardJob:
        """Convert one raw result into the provider-agnostic StandardJob."""

    async def fetch_jobs(self, params: SearchParams | None = None) -> list[StandardJob]:
        """The Search() -> Normalize() pipeline. Concrete providers only
        need to implement the two steps above; this stays identical for
        every provider so the pipeline logic isn't duplicated per source."""
        raw_results = await self.search(params or SearchParams())
        return [self.normalize(raw) for raw in raw_results]
