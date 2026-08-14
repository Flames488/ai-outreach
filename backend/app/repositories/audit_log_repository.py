"""CRUD for `AuditLog`. Insert-only in practice — nothing calls `update`/
`soft_delete` on this repository (audit_logs is never edited)."""

from __future__ import annotations

from app.models.audit_log import AuditLog
from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def list_for_entity(self, entity: str, entity_id: str) -> list[AuditLog]:
        return await self.list(entity=entity, entity_id=entity_id, limit=200)
