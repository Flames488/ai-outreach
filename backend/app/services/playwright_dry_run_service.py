"""Wires the Playwright dry-run flow to the audit trail (Phase 3).

Success/failure of every dry run is logged both structurally (this
module's logger) and durably (`audit_logs`, insert-only, never edited —
the same table Phase 2's Rule Engine uses for its own block decisions).
"""

from __future__ import annotations

import logging

from flames_shared.dto import ApplicationRecord
from flames_shared.enums import ApplicationStatus
from sqlalchemy.ext.asyncio import AsyncSession

from app.playwright.application_runner import PlaywrightApplicationRunner
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class PlaywrightDryRunService:
    def __init__(self, runner: PlaywrightApplicationRunner, audit: AuditService) -> None:
        self._runner = runner
        self._audit = audit

    async def run(
        self,
        *,
        url: str,
        job_fingerprint: str,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        cv_path: str,
    ) -> ApplicationRecord:
        record = await self._runner.dry_run(
            url=url,
            job_fingerprint=job_fingerprint,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            cv_path=cv_path,
        )

        succeeded = record.status == ApplicationStatus.PENDING_VERIFICATION
        action = "dry_run_success" if succeeded else "dry_run_failed"
        await self._audit.log(
            entity="playwright_dry_run",
            entity_id=job_fingerprint,
            action=action,
            new_value={"status": record.status.value, "reason": record.reason, **record.artifacts},
        )
        logger.info(
            "Playwright dry run %s: %s (%s)",
            action,
            job_fingerprint,
            url,
            extra={"job_fingerprint": job_fingerprint, "success": succeeded},
        )
        return record


def get_playwright_dry_run_service(db: AsyncSession) -> PlaywrightDryRunService:
    return PlaywrightDryRunService(
        runner=PlaywrightApplicationRunner(),
        audit=AuditService(db=db, repo=AuditLogRepository(db)),
    )
