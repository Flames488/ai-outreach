"""Contract for submitting a job application via browser automation.

The concrete implementation lives in playwright/application_runner.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from flames_shared.dto import ApplicationRecord, CoverLetterDraft, JobPosting


class ApplicationRunnerInterface(ABC):
    @abstractmethod
    async def apply(self, job: JobPosting, cover_letter: CoverLetterDraft) -> ApplicationRecord:
        """Attempt to submit an application for a single job. Real
        submission — implemented in a later phase, gated behind
        ENABLE_AUTO_APPLY."""

    @abstractmethod
    async def dry_run(
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
        """Fill the application form and reach the submit control without
        ever clicking it. Captures before/after screenshots as artifacts."""
