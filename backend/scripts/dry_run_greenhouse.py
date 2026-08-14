"""Manual smoke test for the Playwright dry-run engine (Phase 3).

Runs a real browser against a real Greenhouse job posting: fills the
standard fields, uploads a CV, locates the submit button, and stops
without clicking it. Prints a JSON success/failure metric and writes an
`audit_logs` row via PlaywrightDryRunService.

Run via: `uv run python scripts/dry_run_greenhouse.py [job_url]`
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from app.database.session import session_scope
from app.services.playwright_dry_run_service import get_playwright_dry_run_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dry_run_greenhouse")

DEFAULT_JOB_URL = "https://job-boards.greenhouse.io/anthropic/jobs/4017331008"
DEFAULT_CV_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_cv.pdf"


async def main() -> None:
    job_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JOB_URL

    async with session_scope() as db:
        service = get_playwright_dry_run_service(db)
        record = await service.run(
            url=job_url,
            job_fingerprint=f"dry-run-smoke-test:{job_url}",
            first_name="Flames",
            last_name="TestApplicant",
            email="flames-dry-run-test@example.com",
            phone="+1 555 010 1234",
            cv_path=str(DEFAULT_CV_PATH),
        )

    summary = {
        "job_url": job_url,
        "status": record.status.value,
        "reason": record.reason,
        **record.artifacts,
    }
    print(json.dumps(summary, indent=2))  # noqa: T201 — this script's actual output contract
    if record.status.value != "pending_verification":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
