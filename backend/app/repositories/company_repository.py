"""CRUD + lookup for `Company` — used by `JobIngestionService` to resolve
a provider's plain-text company name to a `companies.id` FK."""

from __future__ import annotations

from app.models.company import Company
from app.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model = Company

    async def get_by_name(self, company_name: str) -> Company | None:
        result = await self.db.execute(
            self._base_query().where(Company.company_name == company_name)
        )
        return result.scalar_one_or_none()
