"""CRUD + lookup for `JobSkill`."""

from __future__ import annotations

import uuid

from app.models.job_skill import JobSkill
from app.repositories.base_repository import BaseRepository


class JobSkillRepository(BaseRepository[JobSkill]):
    model = JobSkill

    async def list_for_job(self, job_id: uuid.UUID) -> list[JobSkill]:
        return await self.list(job_id=job_id, limit=1000)
