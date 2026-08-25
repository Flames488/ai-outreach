"""Generic CRUD repository (Phase 2 §09).

Repositories perform CRUD and simple queries only — no business logic, no
cross-entity orchestration, no calls to other services. They never
commit; the caller (a Service method, occasionally a route for a trivial
case) owns the transaction via the session from `get_db()`/
`session_scope()`, and commits once at the end of whatever unit of work
it's orchestrating — this is what makes multi-step operations atomic.

`get`/`list`/`count` apply the soft-delete filter (`deleted_at IS NULL`)
automatically for models using `SoftDeleteMixin`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base, SoftDeleteMixin

# Plain Generic/TypeVar rather than PEP 695 `class Foo[T]:` syntax — this
# needs to stay importable on Python 3.11 too (this repo's local dev venv,
# when no 3.12 interpreter is available), even though Docker runs 3.12.
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _base_query(self) -> Select[tuple[ModelT]]:
        query = select(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            query = query.where(self.model.deleted_at.is_(None))
        return query

    async def get(self, id: uuid.UUID) -> ModelT | None:
        result = await self.db.execute(self._base_query().where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 50, offset: int = 0, **filters: Any) -> list[ModelT]:
        query = self._base_query()
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        if hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        query = select(func.count()).select_from(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            query = query.where(self.model.deleted_at.is_(None))
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, **data: Any) -> ModelT:
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def update(self, id: uuid.UUID, **data: Any) -> ModelT | None:
        instance = await self.get(id)
        if instance is None:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await self.db.flush()
        return instance

    async def soft_delete(self, id: uuid.UUID) -> None:
        if not issubclass(self.model, SoftDeleteMixin):
            raise TypeError(f"{self.model.__name__} does not support soft delete")
        instance = await self.get(id)
        if instance is not None:
            instance.deleted_at = datetime.now(UTC)
            await self.db.flush()
